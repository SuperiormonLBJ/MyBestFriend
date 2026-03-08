from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages

import os
import sys
import threading
from pathlib import Path

# Add project root to path so we can import from utils
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

# Module-level vectorstore (used by the main thread and reload_vectorstore).
vectorstore = SupabaseVectorStore(
    client=supabase_client,
    embedding=embeddings,
    table_name="document_chunks",
    query_name="match_documents",
)
retriever_similarity = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
retriever_mmr = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": TOP_K,
        "lambda_mult": 0.6
    }
)

# Thread-local vectorstore so background threads (e.g. eval) get their own
# httpx connection and don't corrupt the main thread's Supabase client.
_tl = threading.local()
_vs_version = 0  # incremented on reload so threads rebuild their local copy


def _get_tl_vectorstore() -> SupabaseVectorStore:
    """Return a per-thread SupabaseVectorStore, rebuilding it when the main vectorstore has been reloaded."""
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
    """Replace the global vectorstore and retrievers after re-ingestion."""
    global vectorstore, retriever_similarity, retriever_mmr, _vs_version
    vectorstore = new_vectorstore
    retriever_similarity = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
    retriever_mmr = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": TOP_K, "lambda_mult": 0.6},
    )
    _vs_version += 1  # signal all threads to rebuild their local copy


def fetch_context(query: str) -> list:
    """
    Fetch context via two paths and combine:
    - Similarity search: top-K most similar chunks
    - MMR (Maximal Marginal Relevance): top-K diverse chunks from a larger candidate pool
    Uses a thread-local vectorstore to avoid httpx thread-safety issues.
    """
    vs = _get_tl_vectorstore()
    query_embedding = embeddings.embed_query(query)

    # Path 1: standard similarity
    context_similarity = vs.similarity_search_by_vector(query_embedding, k=TOP_K)

    # Path 2: MMR — fetch a larger candidate pool, then re-rank client-side for diversity
    fetch_k = TOP_K * 3
    candidates = vs.similarity_search_by_vector(query_embedding, k=fetch_k)
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

    return context_similarity + context_mmr

def deduplicate_context(context: list) -> list:
    """
    Deduplicate the context by creating a unique key from page_content and source metadata
    """
    seen = {}
    deduplicated=[]
    for doc in context:
        key = (doc.page_content, doc.metadata.get("source", ""))
        if key not in seen:
            seen[key] = True
            deduplicated.append(doc)
    return deduplicated

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
    print(f"Rewritten query: {rewritten_query.content}")
    return rewritten_query.content

def rerank_documents(query: str, docs: list, top_k: int = TOP_K):
    """
    Rerank retrieved documents by relevance to the query using the LLM.
    Asks the LLM to return indices of the top_k most relevant passages (1-based).
    """
    user_prompt = f"The user has asked the following question:\n\n{query}\n\nOrder all the chunks of text by relevance to the question, from most relevant to least relevant. Include all the chunk ids you are provided with, reranked.\n\n"
    user_prompt += "Here are the chunks:\n\n"
    for index, chunk in enumerate(docs):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += "Reply only with the list of ranked chunk ids, nothing else."
    messages = [
        {"role": "system", "content": get_prompt("SYSTEM_PROMPT_RERANKER")},
        {"role": "user", "content": user_prompt},
    ]
    llm_with_structured_output = llm_reranker.with_structured_output(RerankOrder)
    rerank_order = llm_with_structured_output.invoke(messages)
    reranked_docs = [docs[i-1] for i in rerank_order.order]

    print(f"Reranked order: {rerank_order.order}")

    return reranked_docs[:top_k]

def combine_all_user_questions(question: str, history: list) -> str:
    """
    Combine all user questions into a single question 
    to solve the issue that user ask "what did she do before"
    """
    prior = "\n".join(msg["content"] for msg in history if msg.get("role") == "user")
    
    # Handle empty prior case
    if prior:
        return prior + "\n" + question
    else:
        return question


def generate_answer(query, history: list[dict] = [], requester_name: str = "", requester_email: str = ""):
    """
    Generate the answer for the query.
    Returns (answer: str, context_docs: list, no_info: bool).
    no_info=True when the LLM signals the context is insufficient via [[NO_INFO]].
    """
    rewritten_query = rewrite_query(query, history)
    combined_query_rewritten = combine_all_user_questions(rewritten_query, history)
    combined_question_original = combine_all_user_questions(query, history)
    context_docs_rewritten = fetch_context(combined_query_rewritten)
    context_docs_original = fetch_context(combined_question_original)
    context_docs = context_docs_rewritten + context_docs_original

    context_docs = deduplicate_context(context_docs)
    reranked_context_docs = rerank_documents(query, context_docs, top_k=TOP_K)
    context = "\n".join([doc.page_content for doc in reranked_context_docs])

    messages = [SystemMessage(content=get_prompt("SYSTEM_PROMPT_GENERATOR").format(context=context))]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=query))

    response = llm.invoke(messages)

    raw = response.content or ""
    no_info = "[[NO_INFO]]" in raw
    answer = raw.replace("[[NO_INFO]]", "").strip()

    print(f"Generated answer with model: {config.get_generator_model()} | no_info={no_info}")

    return answer, context_docs, no_info


def generate_answer_stream(query: str, history: list[dict] = []):
    """
    Stream the answer token by token.
    Yields dicts: {'token': str} for each chunk, then {'done': True, 'no_info': bool, 'final': str}.
    """
    rewritten_query = rewrite_query(query, history)
    combined_query_rewritten = combine_all_user_questions(rewritten_query, history)
    combined_question_original = combine_all_user_questions(query, history)
    context_docs_rewritten = fetch_context(combined_query_rewritten)
    context_docs_original = fetch_context(combined_question_original)
    context_docs = context_docs_rewritten + context_docs_original

    context_docs = deduplicate_context(context_docs)
    reranked_context_docs = rerank_documents(query, context_docs, top_k=TOP_K)
    context = "\n".join([doc.page_content for doc in reranked_context_docs])

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
    print(f"Streamed answer with model: {config.get_generator_model()} | no_info={no_info}")
    yield {"done": True, "no_info": no_info, "final": final}


def get_knowledge_tree():
    """
    Return tree structure of ingested documents for admin UI.
    Tree: doc_type (folder) -> source (document) -> chunks with previews.
    """
    result = supabase_client.table("document_chunks").select("content, metadata").execute()
    rows = result.data or []

    structure = {}
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