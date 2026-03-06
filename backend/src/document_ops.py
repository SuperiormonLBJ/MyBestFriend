"""
Document operations for Admin: add/delete documents and their chunks in the vector store.
"""
import os
from pathlib import Path

from langchain_core.documents import Document

from rag_retrieval import vectorstore
from rag_ingestion import (
    DATA_DIR,
    _parse_md_frontmatter,
    create_chunks_markdown,
)


DOC_TYPE_TO_FOLDER = {
    "project": "projects",
}


def _resolve_folder(doc_type: str) -> str:
    """Map doc_type to the actual folder name on disk (e.g. 'project' -> 'projects')."""
    return DOC_TYPE_TO_FOLDER.get(doc_type, doc_type)


def _sanitize_metadata(meta: dict) -> dict:
    """Chroma accepts only str, int, float, bool. Convert others to str."""
    out = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = str(v)  # Chroma can have issues with list in some versions
        else:
            out[k] = str(v)
    return out


def delete_document(source: str, doc_type: str | None = None) -> dict:
    """
    Delete a document and its chunks from the vector store.
    Also removes the .md file from DATA_DIR if found.
    source: filename (e.g. "UOB-Software-Engineer.md")
    doc_type: optional folder name to locate the file (e.g. "career")
    Returns: {deleted_chunks: int, deleted_file: str | None, error: str | None}
    """
    result = {"deleted_chunks": 0, "deleted_file": None, "error": None}
    try:
        # Delete from Chroma by metadata filter
        collection = vectorstore._collection
        before = collection.count()
        # Chroma accepts where as dict for metadata filter
        vectorstore.delete(where={"source": source})
        after = collection.count()
        result["deleted_chunks"] = before - after

        # Find and delete the .md file
        data_path = Path(DATA_DIR)
        if doc_type:
            folder_name = _resolve_folder(doc_type)
            candidate = data_path / folder_name / source
            if candidate.exists():
                candidate.unlink()
                result["deleted_file"] = str(candidate)
        else:
            for f in data_path.rglob("*.md"):
                if f.name == source:
                    f.unlink()
                    result["deleted_file"] = str(f)
                    break
    except Exception as e:
        result["error"] = str(e)
    return result


def add_document(content: str, filename: str, doc_type: str) -> dict:
    """
    Add a new document: save to disk, chunk, embed, and add to vector store.
    filename: e.g. "my-doc.md"
    doc_type: folder/category (e.g. "projects", "career")
    Returns: {chunks_added: int, file_path: str, error: str | None}
    """
    result = {"chunks_added": 0, "file_path": None, "error": None}
    try:
        # Ensure filename ends with .md
        if not filename.lower().endswith(".md"):
            filename = f"{filename}.md"
        filename = os.path.basename(filename)

        # Save to disk
        data_path = Path(DATA_DIR)
        folder = data_path / _resolve_folder(doc_type)
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / filename
        file_path.write_text(content, encoding="utf-8")
        result["file_path"] = str(file_path)

        # Parse frontmatter like rag_ingestion
        frontmatter_meta, body = _parse_md_frontmatter(content)
        metadata = {"source": filename, "doc_type": doc_type, **frontmatter_meta}
        if "type" in frontmatter_meta:
            metadata["doc_type"] = frontmatter_meta["type"]
        metadata = _sanitize_metadata(metadata)
        metadata["title"] = filename.split(".")[0]
        print(f"[document_ops] metadata for new document: {metadata}")

        # Use full content if body is empty (e.g. doc with only frontmatter)
        page_content = body.strip() if body.strip() else content
        if not page_content:
            result["error"] = "Document content is empty after processing. Add some text."
            return result

        doc = Document(page_content=page_content, metadata=metadata)
        print(f"[document_ops] doc for new document: {doc}")
        chunks = create_chunks_markdown([doc])

        if not chunks:
            result["error"] = "No chunks produced. Ensure the document has enough content (chunk_size=1000)."
            return result

        vectorstore.add_documents(chunks)
        result["chunks_added"] = len(chunks)
        print(f"[document_ops] Added {len(chunks)} chunks for {filename} to vector store")
    except Exception as e:
        result["error"] = str(e)
        print(f"[document_ops] add_document error: {e}")
    return result
