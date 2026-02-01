from pydantic import BaseModel, Field
import json

class TestQuestion(BaseModel):
    """
    Question for evaluation
    """
    question: str = Field(description="The question to be evaluated")   # user question
    ground_truth: str = Field(description="The ground truth answer for the question")
    category: str = Field(description="The category of the question")
    keywords: list[str] = Field(description="The keywords of the question")

class RetrievalLLMEval(BaseModel):
    """
    Retrieval evaluation from LLM based Eval
    """
    accuracy: float = Field(description="The accuracy of the retrieval results, on a scale of 0 to 5")
    relevance: float = Field(description="The relevance of the retrieval results, on a scale of 0 to 5")
    completeness: float = Field(description="The completeness of the retrieval results, on a scale of 0 to 5")
    confidence: float = Field(description="The confidence of the retrieval results, on a scale of 0 to 5")
    feedback: str = Field(description="The feedback for the question")
    score: float = Field(description="The score for the question, average of accuracy, relevance, completeness, on a scale of 0 to 5")
