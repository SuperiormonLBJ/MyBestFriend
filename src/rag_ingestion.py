from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from collections import Counter
import sys

# Add project root to path so we can import from utils
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.config_loader import ConfigLoader
from utils.prompts import LINKEDIN_PROMPT

from langchain_community.document_loaders import PlaywrightURLLoader, PyPDFLoader, UnstructuredHTMLLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from langchain_community.document_loaders import WebBaseLoader
from urllib.parse import urlparse
from pathlib import Path

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
project_root = Path(__file__).parent.parent
config = ConfigLoader()
# Resolve DB_NAME to absolute path so ingestion and retrieval use the same DB regardless of cwd
DB_NAME = str((project_root / config.get_db_name()).resolve())
# Resolve DATA_DIR to absolute path relative to project root
data_dir_from_config = config.get_data_dir()
# Resolve relative path from project root
DATA_DIR = str((project_root / data_dir_from_config).resolve())
MODEL = config.get_llm_model()
TOP_K = config.get_top_k()
CHUNK_SIZE = config.get_chunk_size()
OVERLAP = config.get_overlap()

embeddings = OpenAIEmbeddings(model=config.get_embedding_model())

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_document_md() -> str:
    documents = []
    doc_type = os.path.basename(DATA_DIR)
    loader = DirectoryLoader(DATA_DIR, glob="*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    folder_docs = loader.load()
    for doc in folder_docs:
        doc.metadata["doc_type"] = doc_type
        doc.metadata["source"] = doc.metadata.get("source").split("/")[-1]
        documents.append(doc)
    
    return documents

def load_document_pdf() -> str:
    documents = []
    doc_type = os.path.basename(DATA_DIR)
    loader = DirectoryLoader(DATA_DIR, glob="*.pdf", loader_cls=PyPDFLoader)
    folder_docs = loader.load()
    for doc in folder_docs:
        doc.metadata["doc_type"] = doc_type
        doc.metadata["source"] = doc.metadata.get("source").split("/")[-1]
        documents.append(doc)
    
    return documents

def load_document_url():
    """
    Load documents from a file containing URLs and save them as text files
    """
    documents = []

    urls_file = Path(DATA_DIR) / "urls.txt"
    if not urls_file.exists():
        return documents

    with open(urls_file) as f:
        urls = [u.strip() for u in f.readlines() if u.strip()]

    if not urls:
        return documents

    loader = WebBaseLoader(urls)
    loaded_docs = loader.load()

    for doc in loaded_docs:
        doc.page_content = doc.page_content.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        parsed = urlparse(doc.metadata.get("source", ""))
        doc.metadata["doc_type"] = "url"
        doc.metadata["source"] = parsed.netloc
        if doc.metadata.get("source") == "www.linkedin.com":
            llm = ChatOpenAI(model=MODEL, temperature=0)
            messages = [SystemMessage(content=LINKEDIN_PROMPT.format(raw_linkedin_text=doc.page_content))]
            messages.append(HumanMessage(content=doc.page_content))
            doc.page_content = llm.invoke(messages).content
        doc.metadata["full_url"] = doc.metadata.get("source")
        documents.append(doc)
        with open(Path(DATA_DIR) / (doc.metadata.get("source") + ".txt"), "w") as f:
            f.write(doc.page_content)

    print(f"Loaded {len(documents)} URL documents")
    return documents

def load_document():
    documents = load_document_md() + load_document_pdf() + load_document_url()
    return documents

def create_chunks(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=OVERLAP)
    chunks = text_splitter.split_documents(documents)

    print(f"Divided into {len(chunks)} chunks")
    return chunks

def embed_chunks(chunks):
    if os.path.exists(DB_NAME):
        print(f"Deleting existing vectorstore at {DB_NAME}")
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


if __name__ == "__main__":
    documents = load_document()
    chunks = create_chunks(documents)
    embed_chunks(chunks)