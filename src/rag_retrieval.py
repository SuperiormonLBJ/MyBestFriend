from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from rag_ingestion import DB_NAME, embeddings
from config_loader import ConfigLoader
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages
from dotenv import load_dotenv

load_dotenv(override=True)

config = ConfigLoader()
llm=ChatOpenAI(model=config.get_llm_model())
vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings, collection_name="my_collection")
retriever = vectorstore.as_retriever(search_kwargs={"k": config.get_top_k()})

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions about the user's CV and hobbies.
You are given a question and a context.
You need to answer the question based on the context.
Context:
{context}
"""

def fetch_context(query):
    """
    Fetch the context for the query from the vector store with Top K results
    """
    context = retriever.invoke(query)
    return context

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

def generate_answer(query, history: list):
    """
    Generate the answer for the query

    history from gradio is a list of dictionaries with keys "role" and "content" this is OpenAI format, need to convert it to the format that langchain can use
    """
    
    # combine all user questions into a single question
    combined_question = combine_all_user_questions(query, history)
    context_docs = fetch_context(combined_question)
    context = "\n".join([doc.page_content for doc in context_docs])

    # convert history to langchain format
    messages = [SystemMessage(content=SYSTEM_PROMPT.format(context=context))]

    messages.extend(convert_to_messages(history)) # system message + previous history
    messages.append(HumanMessage(content=query))

    response = llm.invoke(messages)

    return response.content, context_docs