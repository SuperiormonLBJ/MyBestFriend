from doctest import DocTestSuite
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os

from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.text_splitter import SemanticChunker
from langchain.embeddings import HuggingFaceEmbeddings

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
DATA_DIR = str(Path(__file__).parent.parent / 'data')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_document() -> str:
    docs=[]
    files = Path(DATA_DIR).glob('*')
    print(f"Found {len(files)} files in the knowledge base")
    print(f"Files: {[file.name for file in files]}")
    for file in files:
        if file.is_file():
            print("Loading file: ", file)
            with open(file, "r", encoding="utf-8") as f:
                docs.append({"text": f.read(), "source": file.name, "type": file.suffix})
    return docs

"""
Can not use RecursiveCharacterTextSplitter here since we have sections and bounderies. 
so RecursiveCharacterTextSplitter will only mix up the topics.

Section split - CV
Semantic split - LinkedIn and Website
Recursive split - unstructured text
"""
def create_chunks(docs):
    chunks=[]
    for doc in docs:
        split_type = doc["type"]
        if split_type == ".md":
            "section split"
            headers = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
            chunks = [
                {
                    "content": d.page_content,
                    "metadata": {
                        "source": doc["source"],
                        "type": doc["type"],
                        "section": d.metadata["section"]
                    }
                }
                for d in splitter.split_text(doc["text"])
            ]
        elif split_type == ".txt":
            "semantic split"
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            splitter = SemanticChunker(embeddings)
            chunks = [
                {
                    "content": d.page_content,
                    "metadata": {
                        "source": doc["source"],
                        "type": doc["type"],
                        "section": "semantic"
                    }
                }
                for d in splitter.create_documents([doc["text"]], chunk_size=500, chunk_overlap=50)
            ]
    return chunks

def embed_chunks(chunks):
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=chunks
    )
    return [d.embedding for d in response.data]

def add_to_vector_database(chunks, embeddings):
    vector_store = Chroma.from_documents(  
        documents=chunks,
        embedding=embeddings,
        persist_directory="chroma_db",
        collection_name="my_collection"
    )
    return vector_store

"""
TODO: Implement section split, semantic split and recursive split
"""