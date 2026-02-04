from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from base_models import RerankOrder
from config_loader import ConfigLoader
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages
from dotenv import load_dotenv

load_dotenv(override=True)

config = ConfigLoader()
DB_NAME = config.get_db_name()
embeddings = OpenAIEmbeddings(model=config.get_embedding_model())
llm=ChatOpenAI(model=config.get_generator_model())
TOP_K = config.get_top_k()
vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings, collection_name="my_collection")
retriever_similarity = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
retriever_mmr = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": TOP_K,
        "lambda_mult": 0.6  # tweak for diversity
    }
)

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions about an user's profile and daily life.
This response is used for a user to know more about the user's profile and daily life from a HR perspective.

You are given a question and a context.
You need to answer the question based on the context.
Context:
{context}
"""

def fetch_context(query: str) -> list:
    """
    Fetch the context for the query from the vector store with Top K results
    """
    context_similarity = retriever_similarity.invoke(query)
    context_mmr = retriever_mmr.invoke(query)
    context = context_similarity + context_mmr
    context_reranked = rerank_documents(query, context, top_k=TOP_K)
    return context_reranked

SYSTEM_PROMPT_RERANK = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.
"""

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
        {"role": "system", "content": SYSTEM_PROMPT_RERANK},
        {"role": "user", "content": user_prompt},
    ]
    llm_with_structured_output = llm.with_structured_output(RerankOrder)
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

def generate_answer(query, history: list[dict] = []):
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

    print(f"Generated answer with model: {config.get_generator_model()}")

    return response.content, context_docs