import re
import json
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages
from langchain_core.documents import Document

import os
import sys
import threading
import utils.path_setup  # noqa: F401

from utils.base_models import RerankOrder
from utils.config_loader import ConfigLoader
from utils.prompt_manager import get_prompt
from utils.supabase_client import supabase_client
import numpy as np
from langchain_community.vectorstores.utils import maximal_marginal_relevance
from dotenv import load_dotenv

load_dotenv(override=True)

config = ConfigLoader()
embeddings = OpenAIEmbeddings(model=config.get_embedding_model())
llm = ChatOpenAI(model=config.get_generator_model())
llm_rewrite = ChatOpenAI(model=config.get_rewrite_model())
llm_reranker = ChatOpenAI(model=config.get_reranker_model())
TOP_K = config.get_top_k()

vectorstore = SupabaseVectorStore(
    client=supabase_client,
    embedding=embeddings,
    table_name="document_chunks",
    query_name="match_documents",
)
_tl = threading.local()
_vs_version = 0


def _get_tl_vectorstore() -> SupabaseVectorStore:
    if getattr(_tl, "vs_version", -1) != _vs_version:
        from supabase import create_client
        _c = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
        _tl.vectorstore = SupabaseVectorStore(
            client=_c,
            embedding=embeddings,
            table_name="document_chunks",
            query_name="match_documents",
        )
        _tl.vs_version = _vs_version
    return _tl.vectorstore


def reload_vectorstore(new_vectorstore):
    global vectorstore, _vs_version
    vectorstore = new_vectorstore
    _vs_version += 1


def _supabase_similarity_search(client, query_embedding: list, k: int) -> list:
    """
    Call match_documents RPC directly using .limit(k) instead of .params.
    Bypasses LangChain SupabaseVectorStore which breaks with supabase-py 2.23+.
    """
    params = {"query_embedding": query_embedding}
    res = client.rpc("match_documents", params).limit(k).execute()
    return [
        Document(metadata=row.get("metadata", {}), page_content=row.get("content", ""))
        for row in (res.data or [])
        if row.get("content")
    ]


# ---------------------------------------------------------------------------
# Lexical search helpers
# ---------------------------------------------------------------------------

def lexical_search(query: str, max_results: int = 8) -> list:
    """
    Keyword-based ILIKE search against document_chunks.content.
    Filters stop-words and short tokens, searches top keywords independently,
    returns deduplicated Document objects.
    """
    stop_words = {"what", "when", "where", "which", "who", "how", "the", "and",
                  "for", "that", "this", "with", "from", "about", "have", "does"}
    raw_tokens = re.sub(r'[^\w\s]', '', query.lower()).split()
    keywords = [t for t in raw_tokens if len(t) > 3 and t not in stop_words]
    if not keywords:
        return []

    seen: set = set()
    results: list = []
    for kw in keywords[:5]:
        try:
            resp = (
                supabase_client.table("document_chunks")
                .select("content, metadata")
                .ilike("content", f"%{kw}%")
                .limit(max_results)
                .execute()
            )
            for row in (resp.data or []):
                content = row.get("content", "")
                meta = row.get("metadata") or {}
                key = content[:80]
                if key not in seen:
                    seen.add(key)
                    results.append(Document(page_content=content, metadata=meta))
        except Exception as e:
            print(f"[lexical_search] warning for keyword '{kw}': {e}")

    return results


def merge_hybrid(vector_docs: list, lexical_docs: list, lexical_weight: float = 0.3) -> list:
    """
    Combine vector and lexical results via reciprocal rank fusion-style scoring.
    Documents appearing in both lists get a score boost.
    """
    scores: dict = {}
    doc_map: dict = {}

    for rank, doc in enumerate(vector_docs):
        key = doc.page_content[:80]
        score = (1.0 - lexical_weight) * (1.0 / (rank + 1))
        scores[key] = scores.get(key, 0.0) + score
        doc_map[key] = doc

    for rank, doc in enumerate(lexical_docs):
        key = doc.page_content[:80]
        score = lexical_weight * (1.0 / (rank + 1))
        scores[key] = scores.get(key, 0.0) + score
        doc_map.setdefault(key, doc)

    sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    return [doc_map[k] for k in sorted_keys]


# ---------------------------------------------------------------------------
# Query intent extraction
# ---------------------------------------------------------------------------

def extract_query_intent(query: str) -> dict:
    """
    Extract year and doc_type hints via lightweight regex + keyword patterns.
    Used for soft metadata boosting — never hard-filters results.
    """
    intent: dict = {"year": None, "doc_type": None}

    year_match = re.search(r'\b(20\d{2})\b', query)
    if year_match:
        intent["year"] = year_match.group(1)

    q = query.lower()
    if any(w in q for w in ["work", "job", "career", "company", "role", "position",
                              "intern", "employed", "employer", "hire", "hired"]):
        intent["doc_type"] = "career"
    elif any(w in q for w in ["project", "built", "developed", "created", "app",
                               "system", "tool", "software", "codebase"]):
        intent["doc_type"] = "project"
    elif any(w in q for w in ["hobby", "hobbies", "sport", "personal", "interest",
                               "outside work", "free time", "passion", "travel"]):
        intent["doc_type"] = "personal"
    elif any(w in q for w in ["resume", "cv", "skill", "education", "degree",
                               "university", "school", "study", "studied"]):
        intent["doc_type"] = "cv"

    return intent


def _apply_metadata_boost(docs: list, intent: dict) -> list:
    """
    Re-order docs by soft-boosting those whose metadata matches the extracted intent.
    Documents without a match keep their original relative order.
    """
    if not intent["doc_type"] and not intent["year"]:
        return docs

    boosted = []
    for doc in docs:
        meta = doc.metadata
        boost = 0
        if intent["doc_type"] and (meta.get("doc_type") or "").lower() == intent["doc_type"]:
            boost += 2
        if intent["year"] and str(meta.get("year", "")) == intent["year"]:
            boost += 1
        boosted.append((doc, boost))

    boosted.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in boosted]


def _extract_job_requirements_heuristic(job_description: str) -> dict:
    lines = [line.strip() for line in job_description.splitlines() if line.strip()]
    requirements: list[str] = []
    seen_req: set[str] = set()

    req_starters = (
        "must",
        "required",
        "need",
        "should",
        "prefer",
        "preferred",
        "experience with",
        "ability to",
        "knowledge of",
        "familiarity with",
    )
    section_headings = {
        "about the job",
        "responsibilities",
        "profile",
        "qualifications",
        "culture",
    }
    current_section = ""
    for line in lines:
        lower = line.lower()
        if lower in section_headings:
            current_section = lower
            continue
        in_req_section = current_section in {"responsibilities", "profile", "qualifications"}
        if in_req_section or any(lower.startswith(s) or f" {s} " in f" {lower} " for s in req_starters):
            clean = line.strip().lstrip("-*•· ").strip()
            if len(clean) > 10 and clean not in seen_req:
                seen_req.add(clean)
                requirements.append(clean[:200])

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "have",
        "will",
        "your",
        "you",
        "we",
        "our",
        "are",
        "can",
        "able",
        "about",
        "job",
        "working",
        "team",
        "small",
        "highly",
        "productive",
        "efficient",
        "see",
        "name",
        "truth",
        "write",
        "role",
        "company",
    }
    keyword_source = "\n".join(requirements) if requirements else job_description
    raw_tokens = re.sub(r"[^\w\s]", " ", keyword_source.lower()).split()
    keywords = []
    seen_kw: set[str] = set()
    for t in raw_tokens:
        if len(t) > 2 and t not in stop_words and t.isalpha() and t not in seen_kw:
            seen_kw.add(t)
            keywords.append(t)
    job_lower = job_description.lower()
    skill_terms = [
        "python",
        "linux",
        "unix",
        "distributed",
        "orchestration",
        "scheduling",
        "etl",
        "trading",
        "cluster",
    ]
    for term in skill_terms:
        if term in job_lower and term not in seen_kw:
            seen_kw.add(term)
            keywords.insert(0, term)
    keywords = keywords[:30]
    return {"keywords": keywords, "requirements": requirements}


# ---------------------------------------------------------------------------
# Job preparation: requirement extraction and context
# ---------------------------------------------------------------------------

def extract_job_requirements(job_description: str) -> dict:
    """
    Extract technical requirements, culture signals, and keywords from a job
    description using a small LLM, with a heuristic fallback.
    Returns a dict with keys: technical_requirements, culture, keywords, requirements.
    """
    heuristic = _extract_job_requirements_heuristic(job_description)
    try:
        llm_small = ChatOpenAI(model=config.get_rewrite_model(), temperature=0)
        system = SystemMessage(
            content=(
                "You extract structured information from job descriptions. "
                "Given a full job description, return a strict JSON object with:\n"
                '- "technical_requirements": list of concise bullet strings capturing skills, tools, and experience requirements.\n'
                '- "culture": list of concise bullet strings describing culture, values, and soft factors.\n'
                '- "keywords": list of short skill/role keywords (single words or short phrases).\n'
                "Do not include headings like 'Responsibilities' or 'Qualifications' as items. "
                "Respond with JSON only, no extra text."
            )
        )
        human = HumanMessage(
            content=f"JOB DESCRIPTION:\n\n{job_description}\n\nReturn JSON now."
        )
        response = llm_small.invoke([system, human])
        data = json.loads(response.content or "{}")
        tech = data.get("technical_requirements") or []
        culture = data.get("culture") or []
        keywords = data.get("keywords") or []

        def _norm_list(x):
            if isinstance(x, str):
                return [x.strip()] if x.strip() else []
            if isinstance(x, list):
                out = []
                for item in x:
                    if isinstance(item, str):
                        s = item.strip()
                        if s:
                            out.append(s)
                return out
            return []

        tech_list = _norm_list(tech)
        culture_list = _norm_list(culture)
        keyword_list = _norm_list(keywords)
        if not keyword_list:
            keyword_list = heuristic["keywords"]
        if not tech_list and heuristic["requirements"]:
            tech_list = heuristic["requirements"]
        return {
            "technical_requirements": tech_list,
            "culture": culture_list,
            "keywords": keyword_list,
            "requirements": tech_list or heuristic["requirements"],
        }
    except Exception:
        return {
            "technical_requirements": heuristic["requirements"],
            "culture": [],
            "keywords": heuristic["keywords"],
            "requirements": heuristic["requirements"],
        }


def get_job_context(job_description: str, reqs: dict | None = None) -> tuple[list, str]:
    """
    Build a focused search query from the job description and optional extracted reqs,
    fetch and deduplicate context, rerank, and return (doc list, context string).
    """
    if reqs is None:
        reqs = extract_job_requirements(job_description)
    query_parts = [job_description[:1000]]
    if reqs.get("keywords"):
        query_parts.append(" ".join(reqs["keywords"][:15]))
    if reqs.get("requirements"):
        query_parts.append(" ".join(r[:80] for r in reqs["requirements"][:5]))
    query = " ".join(query_parts).strip()
    if not query:
        query = job_description[:1000]
    docs = fetch_context(query)
    docs = deduplicate_context(docs)
    docs = rerank_documents(query, docs, top_k=TOP_K)
    context = "\n\n".join(doc.page_content for doc in docs)
    return docs, context


# ---------------------------------------------------------------------------
# Core retrieval
# ---------------------------------------------------------------------------

def fetch_context(query: str) -> list:
    """
    Fetch context via:
    1. Standard similarity search (top-K)
    2. MMR for diversity
    3. Lexical ILIKE search (if HYBRID_SEARCH_ENABLED)
    Then applies metadata soft-boost (if METADATA_FILTER_ENABLED).
    """
    vs = _get_tl_vectorstore()
    client = vs._client
    query_embedding = embeddings.embed_query(query)

    context_similarity = _supabase_similarity_search(client, query_embedding, TOP_K)

    fetch_k = TOP_K * 3
    candidates = _supabase_similarity_search(client, query_embedding, fetch_k)
    if candidates:
        candidate_embeddings = embeddings.embed_documents([d.page_content for d in candidates])
        mmr_indices = maximal_marginal_relevance(
            np.array(query_embedding, dtype=np.float32),
            candidate_embeddings,
            lambda_mult=0.6,
            k=TOP_K,
        )
        context_mmr = [candidates[i] for i in mmr_indices]
    else:
        context_mmr = []

    vector_docs = context_similarity + context_mmr

    if config.get_hybrid_search_enabled():
        lexical_docs = lexical_search(query)
        combined = merge_hybrid(vector_docs, lexical_docs, config.get_lexical_weight())
    else:
        combined = vector_docs

    if config.get_metadata_filter_enabled():
        intent = extract_query_intent(query)
        combined = _apply_metadata_boost(combined, intent)

    return combined


def deduplicate_context(context: list) -> list:
    seen: dict = {}
    deduped: list = []
    for doc in context:
        key = (doc.page_content[:80], doc.metadata.get("source", ""))
        if key not in seen:
            seen[key] = True
            deduped.append(doc)
    return deduped


def rewrite_query(query: str, history: list = []) -> str:
    user_prompt = f"""
        This is the history of your conversation so far with the user:
        {history}

        The user has asked the following question:
        {query}
    """
    messages = [
        {"role": "system", "content": get_prompt("REWRITE_PROMPT")},
        {"role": "user", "content": user_prompt},
    ]
    rewritten_query = llm_rewrite.invoke(messages)
    return rewritten_query.content


def rerank_documents(query: str, docs: list, top_k: int = TOP_K):
    user_prompt = (
        f"The user has asked the following question:\n\n{query}\n\n"
        "Order all the chunks of text by relevance to the question, from most relevant to least relevant. "
        "Include all the chunk ids you are provided with, reranked.\n\n"
        "Here are the chunks:\n\n"
    )
    for index, chunk in enumerate(docs):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += "Reply only with the list of ranked chunk ids, nothing else."
    messages = [
        {"role": "system", "content": get_prompt("SYSTEM_PROMPT_RERANKER")},
        {"role": "user", "content": user_prompt},
    ]
    llm_with_structured_output = llm_reranker.with_structured_output(RerankOrder)
    rerank_order = llm_with_structured_output.invoke(messages)
    reranked_docs = [docs[i - 1] for i in rerank_order.order]
    return reranked_docs[:top_k]


def combine_all_user_questions(question: str, history: list) -> str:
    prior = "\n".join(msg["content"] for msg in history if msg.get("role") == "user")
    return (prior + "\n" + question) if prior else question


# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------

def _extract_sources(docs: list) -> list:
    """Return a deduplicated list of source metadata dicts for citation display."""
    seen: set = set()
    sources: list = []
    for doc in docs:
        meta = doc.metadata
        source = meta.get("source", "")
        section = meta.get("section") or meta.get("subsection") or ""
        key = (source, section)
        if key not in seen:
            seen.add(key)
            sources.append({
                "source": source,
                "section": section,
                "doc_type": meta.get("doc_type", ""),
                "year": str(meta.get("year", "")),
                "snippet": (doc.page_content or "")[:160].strip(),
            })
    return sources[:5]


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check_answer(answer: str, context: str) -> dict:
    """
    Run a lightweight factual grounding check.
    Returns {supported: bool, severity: 'low'|'high', raw: str}.
    """
    llm_checker = ChatOpenAI(model=config.get_rewrite_model(), temperature=0)
    prompt = get_prompt("SELF_CHECK_PROMPT").format(context=context[:3000], answer=answer)
    try:
        response = llm_checker.invoke([SystemMessage(content=prompt)])
        raw = (response.content or "").strip()
        supported = raw.upper().startswith("YES")
        severity = "high" if "UNSUPPORTED" in raw.upper() and len(raw) > 60 else "low"
        return {"supported": supported, "severity": severity, "raw": raw}
    except Exception as e:
        print(f"[self_check] warning: {e}")
        return {"supported": True, "severity": "low", "raw": ""}


# ---------------------------------------------------------------------------
# Multi-step / complex-query helpers
# ---------------------------------------------------------------------------

_COMPLEX_KEYWORDS = [
    "compare", "timeline", "pros and cons", "list all", "summarize all",
    "history of", "how did", "what changed", "difference between",
    "progression", "over the years", "evolution",
]


def _is_complex_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _COMPLEX_KEYWORDS)


def _generate_followup_queries(query: str, initial_context: str) -> list:
    """Ask the LLM to suggest up to 2 follow-up retrieval queries."""
    llm_cheap = ChatOpenAI(model=config.get_rewrite_model(), temperature=0)
    prompt = get_prompt("MULTI_STEP_PROMPT").format(
        query=query,
        initial_context=initial_context[:2000],
    )
    try:
        response = llm_cheap.invoke([SystemMessage(content=prompt)])
        raw = (response.content or "").strip()
        if raw.upper() == "SUFFICIENT":
            return []
        queries = [q.strip() for q in raw.split("\n") if q.strip() and q.strip().upper() != "SUFFICIENT"]
        return queries[:2]
    except Exception as e:
        print(f"[multi_step] warning: {e}")
        return []


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------

def _maybe_expand_context(query: str, reranked: list) -> tuple[list, str]:
    """
    Run multi-step expansion if MULTI_STEP_ENABLED and the query is complex.
    Returns (reranked_docs, context_str). Falls back to inputs unchanged if disabled.
    Extracted to avoid copy-paste between generate_answer() and generate_answer_stream().
    """
    if not (config.get_multi_step_enabled() and _is_complex_query(query)):
        return reranked, "\n".join(doc.page_content for doc in reranked)
    followups = _generate_followup_queries(query, "\n".join(doc.page_content for doc in reranked))
    if not followups:
        return reranked, "\n".join(doc.page_content for doc in reranked)
    extra_docs = []
    for fq in followups:
        extra_docs.extend(fetch_context(fq))
    all_docs = deduplicate_context(reranked + extra_docs)
    reranked = rerank_documents(query, all_docs, top_k=TOP_K)
    return reranked, "\n".join(doc.page_content for doc in reranked)


def generate_answer(query: str, history: list = []):
    """
    Generate the answer for the query.
    Returns (answer: str, context_docs: list, no_info: bool, sources: list[dict]).
    """
    rewritten_query = rewrite_query(query, history)
    combined_rewritten = combine_all_user_questions(rewritten_query, history)
    combined_original = combine_all_user_questions(query, history)
    context_docs = deduplicate_context(fetch_context(combined_rewritten) + fetch_context(combined_original))
    reranked = rerank_documents(query, context_docs, top_k=TOP_K)
    reranked, context = _maybe_expand_context(query, reranked)

    messages = [SystemMessage(content=get_prompt("SYSTEM_PROMPT_GENERATOR").format(context=context))]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=query))

    response = llm.invoke(messages)
    raw = response.content or ""
    no_info = "[[NO_INFO]]" in raw
    answer = raw.replace("[[NO_INFO]]", "").strip()

    if config.get_self_check_enabled() and not no_info and answer:
        check = _self_check_answer(answer, context)
        if not check["supported"] and check["severity"] == "high":
            no_info = True

    sources = _extract_sources(reranked)
    return answer, context_docs, no_info, sources


def generate_answer_stream(query: str, history: list = []):
    """
    Stream the answer token by token.
    Yields dicts: {'token': str} for each chunk, then {'done': True, 'no_info': bool, 'final': str, 'sources': list}.
    """
    rewritten_query = rewrite_query(query, history)
    combined_rewritten = combine_all_user_questions(rewritten_query, history)
    combined_original = combine_all_user_questions(query, history)
    context_docs = deduplicate_context(fetch_context(combined_rewritten) + fetch_context(combined_original))
    reranked = rerank_documents(query, context_docs, top_k=TOP_K)
    reranked, context = _maybe_expand_context(query, reranked)

    messages = [SystemMessage(content=get_prompt("SYSTEM_PROMPT_GENERATOR").format(context=context))]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=query))

    full_text = ""
    for chunk in llm.stream(messages):
        token = chunk.content or ""
        full_text += token
        if token:
            yield {"token": token}

    no_info = "[[NO_INFO]]" in full_text
    final = full_text.replace("[[NO_INFO]]", "").strip()

    # Self-check on accumulated answer
    if config.get_self_check_enabled() and not no_info and final:
        check = _self_check_answer(final, context)
        if not check["supported"] and check["severity"] == "high":
            no_info = True

    sources = _extract_sources(reranked)
    yield {"done": True, "no_info": no_info, "final": final, "sources": sources}


def get_knowledge_tree():
    result = supabase_client.table("document_chunks").select("content, metadata").execute()
    rows = result.data or []

    structure: dict = {}
    for row in rows:
        meta = row.get("metadata") or {}
        content = row.get("content", "")
        doc_type = meta.get("doc_type") or meta.get("source", "").split("/")[0] or "unknown"
        source = meta.get("source", "unknown")
        section = meta.get("section") or meta.get("subsection") or ""
        preview = (content or "")[:150].replace("\n", " ") + ("..." if len(content or "") > 150 else "")

        if doc_type not in structure:
            structure[doc_type] = {}
        if source not in structure[doc_type]:
            structure[doc_type][source] = []
        structure[doc_type][source].append({"preview": preview, "section": section})

    tree = []
    for doc_type in sorted(structure.keys()):
        sources = structure[doc_type]
        total_chunks = sum(len(chunks) for chunks in sources.values())
        children = []
        for source in sorted(sources.keys()):
            chunks = sources[source]
            children.append({
                "name": source,
                "type": "document",
                "chunkCount": len(chunks),
                "chunks": chunks,
            })
        tree.append({
            "name": doc_type,
            "type": "folder",
            "chunkCount": total_chunks,
            "children": children,
        })

    return {"tree": tree, "totalChunks": sum(n["chunkCount"] for n in tree)}
