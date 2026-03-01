import json
import os
from pathlib import Path
import sys
# Add project root to path so we can import from utils
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from utils.base_models import TestQuestion
import tqdm
from rag_retrieval import fetch_context, generate_answer, rewrite_query
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from utils.base_models import RetrievalLLMEval
from rag_retrieval import generate_answer
from utils.prompts import SYSTEM_PROMPT_EVALUATOR_GENERATOR
from utils.config_loader import ConfigLoader
from utils.base_models import RetrievalEval

from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from rag_ingestion import embeddings


config = ConfigLoader()
llm = ChatOpenAI(model=config.get_evaluator_model())
TOP_K = config.get_top_k()
project_root = Path(__file__).parent.parent
TEST_QUESTIONS_FILE_PATH = str((project_root / "evaluation/eval_data.jsonl").resolve())

def load_test_questions() -> list[TestQuestion]:
    """
    Load test questions from a JSONL file
    """
    with open(TEST_QUESTIONS_FILE_PATH, "r", encoding="utf-8") as f:
        tests = []
        for line in f:
            data = json.loads(line.strip()) 
            tests.append(TestQuestion(**data))
        print("Loaded {} test questions".format(len(tests)))
    return tests

def evaluate_response(test_question: TestQuestion) -> RetrievalLLMEval:
    """
    Evaluate the LLM-Response based on the retrieval results, not on the retrieval results based on the question
    """
    # get the context
    generated_answer, retrieval_results = generate_answer(test_question.question)

    # parse the messages
    system_messages = [SystemMessage(
        content=("You are an expert evaluator assessing the quality of answers. Evaluate the generated answer by comparing it to the reference answer. Only give 5/5 scores for perfect answers."
                 ))]
    user_messages = [HumanMessage(content=SYSTEM_PROMPT_EVALUATOR_GENERATOR.format(question=test_question.question, generated_answer=generated_answer, ground_truth=test_question.ground_truth))]
    messages = system_messages + user_messages

    structured_llm = llm.with_structured_output(RetrievalLLMEval)
    response_LLM_eval = structured_llm.invoke(messages)

    return response_LLM_eval

def evaluate_LLM(tests: list[TestQuestion]) -> RetrievalLLMEval:
    """
    Evaluate all the tests
    """
    results = []  
    for test in tqdm.tqdm(tests, desc="Evaluating tests", unit="test"):
        results.append(evaluate_response(test))
    evaluation_result = RetrievalLLMEval(
        accuracy=sum([result.accuracy for result in results]) / len(results),
        relevance=sum([result.relevance for result in results]) / len(results),
        completeness=sum([result.completeness for result in results]) / len(results),
        score=sum([result.score for result in results]) / len(results),
        confidence=sum([result.confidence for result in results]) / len(results),
        feedback="This is the average of all the tests",
    )
    
    return evaluation_result

def evaluate_mrr(keyword:str, retrieval_results:list) -> float:
    """
    Evaluate the MRR of the retrieval results,
    mrr = 1 -> first result contains the keyword
    mrr = 0.5 -> second result contains the keyword
    mrr = 0 -> no result contains the keyword
    """
    keyword = keyword.lower();
    for rank, result in enumerate(retrieval_results, start=1):
        if keyword in result.page_content.lower():
            return 1/rank
    return 0

def evaluate_retrieval(test: TestQuestion) -> RetrievalEval:
    """
    Evaluate the retrieval results
    """

    retrieved_docs = fetch_context(test.question)
    mrr_scores = [evaluate_mrr(keyword, retrieved_docs) for keyword in test.keywords]# each keyword need to be calculated separately, so a list of scores
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0

    # Calculate keyword coverage
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords > 0 else 0.0

    return RetrievalEval(
        MRR=avg_mrr,
        keyword_coverage=keyword_coverage,
    )

def evaluate_all(tests: list[TestQuestion]) -> RetrievalEval:
    """
    Evaluate all the tests
    """
    results = []
    for test in tests:
        results.append(evaluate_retrieval(test))
    
    mrr_final = sum(result.MRR for result in results) / len(results)
    keyword_coverage_final = sum(result.keyword_coverage for result in results) / len(results)

    return RetrievalEval(
        MRR=format(mrr_final, ".2f"),
        keyword_coverage=format(keyword_coverage_final, ".2f"),
    )



if __name__ == "__main__":
    tests = load_test_questions()
    # eval_result_LLM = evaluate_LLM(tests)
    # print("\nAverage of all the tests from LLM evaluation on LLM answer:")
    # print(f"accuracy: {eval_result_LLM.accuracy}")
    # print(f"relevance: {eval_result_LLM.relevance}")
    # print(f"completeness: {eval_result_LLM.completeness}")
    # print(f"score: {eval_result_LLM.score}")
    # print(f"confidence: {eval_result_LLM.confidence}")

    # eval_result_retrieval = evaluate_all(tests)
    # print("\nAverage of all the tests from retrieval evaluation:")
    # print(f"MRR: {eval_result_retrieval.MRR}")
    # print(f"Keyword Coverage: {eval_result_retrieval.keyword_coverage}% ")

    questions = [test.question for test in tests]
    ground_truths = [test.ground_truth for test in tests]
    contexts = []
    answers = []
    for test in tests:
        test_answer, test_context = generate_answer(test.question)
        answers.append(test_answer)
        # each query have multiple context documents
        contexts.append([doc.page_content for doc in test_context])

    dataset = Dataset.from_dict({
        "question": questions,
        "reference": ground_truths,
        "contexts": contexts,
        "answer": answers,
    })

    result = evaluate(
        dataset = dataset, 
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
        embeddings=embeddings,
        llm=llm,
    )

    df = result.to_pandas()
    print("contect precision: ", format(df["context_precision"].mean(), ".2f"))
    print("contect recall: ", format(df["context_recall"].mean(), ".2f"))
    print("faithfulness: ", format(df["faithfulness"].mean(), ".2f"))
    print("answer relevancy: ", format(df["answer_relevancy"].mean(), ".2f"))   