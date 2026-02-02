from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from collections import Counter

from config_loader import ConfigLoader

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

#/Users/beijim4/Desktop/Projects-AI/MyBestFriend/data
config = ConfigLoader()
DB_NAME = config.get_db_name()
# Resolve DATA_DIR to absolute path relative to project root
data_dir_from_config = config.get_data_dir()
# Get project root (parent of src/)
project_root = Path(__file__).parent.parent
# Resolve relative path from project root
DATA_DIR = str((project_root / data_dir_from_config).resolve())
MODEL = config.get_llm_model()
TOP_K = config.get_top_k()
CHUNK_SIZE = config.get_chunk_size()
OVERLAP = config.get_overlap()

embeddings = OpenAIEmbeddings(model=config.get_embedding_model())

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_document() -> str:
    documents = []
    doc_type = os.path.basename(DATA_DIR)
    loader = DirectoryLoader(DATA_DIR, glob="*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    folder_docs = loader.load()
    for doc in folder_docs:
        doc.metadata["doc_type"] = doc_type
        doc.metadata["source"] = doc.metadata.get("source").split("/")[-1]
        documents.append(doc)
    
    return documents

"""
Can not use RecursiveCharacterTextSplitter here since we have sections and bounderies. 
so RecursiveCharacterTextSplitter will only mix up the topics.

Section split - CV
Semantic split - LinkedIn and Website
Recursive split - unstructured text
"""
def create_chunks(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=OVERLAP)
    chunks = text_splitter.split_documents(documents)

    print(f"Divided into {len(chunks)} chunks")
    return chunks

def embed_chunks(chunks):
    if os.path.exists(DB_NAME):
        Chroma(persist_directory=DB_NAME, embedding_function=embeddings, collection_name="my_collection").delete_collection()

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_NAME,
        collection_name="my_collection"
    )

    print(f"Vectorstore created with {vector_store._collection.count()} documents")

    collection = vector_store._collection
    count = collection.count()

    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    dimensions = len(sample_embedding)
    print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")

    all_docs = collection.get(include=["documents", "metadatas"])

    # Count by source
    sources = [meta.get("source", "unknown") for meta in all_docs["metadatas"]]
    print("Documents by source:", Counter(sources))

    # Check for duplicates
    doc_contents = all_docs["documents"]
    print(f"Total documents: {len(doc_contents)}")
    print(f"Unique documents: {len(set(doc_contents))}")

    return vector_store


"""
TODO: Implement section split, semantic split and recursive split
"""

if __name__ == "__main__":
    documents = load_document()
    chunks = create_chunks(documents)
    embed_chunks(chunks)