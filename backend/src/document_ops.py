"""
Document operations for Admin: add/delete documents and their chunks in the vector store.
Also syncs to Supabase `documents` table as cloud storage.
"""
import os
import sys
from pathlib import Path

from langchain_core.documents import Document

from src.rag_retrieval import vectorstore
from src.rag_ingestion import (
    DATA_DIR,
    _parse_md_frontmatter,
    create_chunks_markdown,
)
from utils.config_loader import ConfigLoader as _ConfigLoader
_doc_ops_config = _ConfigLoader()

# Add project root so utils/ is importable when running from src/
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from utils.supabase_client import supabase_client


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


def _sync_delete_supabase(filename: str, doc_type: str | None) -> None:
    """Remove document row(s) from Supabase. Errors are logged but not raised."""
    try:
        query = supabase_client.table("documents").delete().eq("filename", filename)
        if doc_type:
            query = query.eq("doc_type", doc_type)
        query.execute()
    except Exception as e:
        print(f"[document_ops] Supabase delete warning (non-fatal): {e}")


def _sync_upsert_supabase(filename: str, doc_type: str, content: str) -> None:
    """Upsert document row into Supabase. Errors are logged but not raised."""
    try:
        supabase_client.table("documents").upsert(
            {"filename": filename, "doc_type": doc_type, "content": content},
            on_conflict="filename,doc_type",
        ).execute()
    except Exception as e:
        print(f"[document_ops] Supabase upsert warning (non-fatal): {e}")


def delete_document(source: str, doc_type: str | None = None) -> dict:
    """
    Delete a document and its chunks from the vector store.
    Also removes the .md file from DATA_DIR and the row from Supabase.
    source: filename (e.g. "UOB-Software-Engineer.md")
    doc_type: optional folder name to locate the file (e.g. "career")
    Returns: {deleted_chunks: int, deleted_file: str | None, error: str | None}
    """
    result = {"deleted_chunks": 0, "deleted_file": None, "error": None}
    try:
        # Find chunk IDs by source metadata filter, then delete from Supabase vector store
        chunk_query = supabase_client.table("document_chunks") \
            .select("id") \
            .filter("metadata->>source", "eq", source) \
            .execute()
        chunk_ids = [str(row["id"]) for row in (chunk_query.data or [])]
        if chunk_ids:
            vectorstore.delete(chunk_ids)
        result["deleted_chunks"] = len(chunk_ids)

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

        # Sync deletion to Supabase
        _sync_delete_supabase(source, doc_type)
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
        metadata["owner_id"] = _doc_ops_config.get_owner_id()

        # Use full content if body is empty (e.g. doc with only frontmatter)
        page_content = body.strip() if body.strip() else content
        if not page_content:
            result["error"] = "Document content is empty after processing. Add some text."
            return result

        doc = Document(page_content=page_content, metadata=metadata)
        chunks = create_chunks_markdown([doc])

        if not chunks:
            result["error"] = "No chunks produced. Ensure the document has enough content (chunk_size=1000)."
            return result

        vectorstore.add_documents(chunks)
        result["chunks_added"] = len(chunks)

        # Sync to Supabase
        _sync_upsert_supabase(filename, doc_type, content)
    except Exception as e:
        result["error"] = str(e)
    return result
