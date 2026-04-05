from dotenv import load_dotenv
import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
import utils.path_setup  # noqa: F401
from pathlib import Path

from utils.config_loader import ConfigLoader
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

load_dotenv(override=True)

"""
RAG Ingestion Module
- Load CV (PDF)
- Load LinkedIn (TXT)
- Load Website (HTML)
- Clean text but preserve headers
- Attach metadata:
    - source
    - doc_type
    - section
    - timestamp
- Chunking
- Embedding
- Add into vector database
"""

config = ConfigLoader()
project_root = Path(__file__).parent.parent
data_dir_from_config = config.get_data_dir()
DATA_DIR = str((project_root / data_dir_from_config).resolve())
MODEL = config.get_llm_model()
CHUNK_SIZE = config.get_chunk_size()
OVERLAP = config.get_overlap()

embeddings = OpenAIEmbeddings(model=config.get_embedding_model())

def _parse_md_frontmatter(content: str):
    """
    Parse simple YAML-like frontmatter:

    ---
    key: value
    tags: [a, b, c]
    ---
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    meta_lines = []
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        meta_lines.append(lines[i])
        i += 1

    if i >= len(lines):
        # no closing ---
        return {}, content

    body = "\n".join(lines[i + 1:])

    metadata = {}
    for line in meta_lines:
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, val = stripped.split(":", 1)
        key = key.strip()
        val = val.strip()
        
        metadata[key] = val.strip().strip("'\"")

    return metadata, body.lstrip("\n")


def load_document_md() -> str:
    documents = []

    # Load all markdown recursively under DATA_DIR
    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    folder_docs = loader.load()

    for doc in folder_docs:
        raw_source = doc.metadata.get("source", "")
        source_path = raw_source

        # Parse and strip frontmatter
        frontmatter_meta, body = _parse_md_frontmatter(doc.page_content)
        if frontmatter_meta:
            doc.page_content = body
            for k, v in frontmatter_meta.items():
                doc.metadata[k] = v

        # doc_type: prefer frontmatter "type", else parent folder name; always lowercase
        if "type" in doc.metadata:
            doc.metadata["doc_type"] = doc.metadata["type"].lower()
        else:
            parent = os.path.basename(os.path.dirname(source_path))
            doc.metadata["doc_type"] = (parent or os.path.basename(DATA_DIR)).lower()

        # source: just the filename
        if raw_source:
            doc.metadata["source"] = os.path.basename(raw_source)

        # owner_id for multi-tenant namespacing
        doc.metadata["owner_id"] = config.get_owner_id()

        documents.append(doc)  # Has to be Document object !!!

    return documents

def load_document():
    return load_document_md()

MAX_WORDS_PER_CHUNK = 400  # ~800 tokens; split sections larger than this by paragraphs


def _split_by_paragraphs(text: str, metadata: dict, max_words: int = MAX_WORDS_PER_CHUNK) -> list:
    """
    Split a long text block into paragraph-level sub-chunks, each under max_words.
    Preserves all metadata fields. Returns at least one Document.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [Document(page_content=text, metadata=metadata)]

    chunks: list = []
    current_parts: list = []
    current_words = 0

    for para in paragraphs:
        words = len(para.split())
        if current_words + words > max_words and current_parts:
            chunks.append(Document(
                page_content="\n\n".join(current_parts),
                metadata=dict(metadata),
            ))
            current_parts = [para]
            current_words = words
        else:
            current_parts.append(para)
            current_words += words

    if current_parts:
        chunks.append(Document(
            page_content="\n\n".join(current_parts),
            metadata=dict(metadata),
        ))

    return chunks if chunks else [Document(page_content=text, metadata=metadata)]


def create_chunks_markdown(documents):
    # Two-level split: ## and ### headers
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("##", "section"),
            ("###", "subsection"),
        ]
    )

    chunked_docs = []
    for doc in documents:
        section_chunks = markdown_splitter.split_text(doc.page_content)
        for c in section_chunks:
            new_meta = dict(doc.metadata)
            section_title = c.metadata.get("section")
            project_title = doc.metadata.get("title")
            if section_title:
                c.page_content = f"project title: {project_title}\n\nsection: {section_title}\n\n{c.page_content}"
            new_meta.update(c.metadata)

            # Sub-split large sections by paragraphs to keep chunks manageable
            word_count = len(c.page_content.split())
            if word_count > MAX_WORDS_PER_CHUNK:
                sub_chunks = _split_by_paragraphs(c.page_content, new_meta, MAX_WORDS_PER_CHUNK)
                chunked_docs.extend(sub_chunks)
            else:
                chunked_docs.append(Document(page_content=c.page_content, metadata=new_meta))

    return chunked_docs

def embed_chunks(chunks):
    from utils.supabase_client import supabase_client

    # Clear all existing chunks before re-ingestion (neq null-uuid matches all rows)
    supabase_client.table("document_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    vector_store = SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=supabase_client,
        table_name="document_chunks",
        query_name="match_documents",
    )

    return vector_store


if __name__ == "__main__":
    documents = load_document()
    chunks = create_chunks_markdown(documents)
    embed_chunks(chunks)