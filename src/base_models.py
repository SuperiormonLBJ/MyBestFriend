from pydantic import BaseModel, Field
import json

class BaseModel(BaseModel):
    pass

class TestQuestion(BaseModel):
    """
    Question for evaluation
    """
    question: str = Field(description="The question to be evaluated")   # user question
    ground_truth: str = Field(description="The ground truth answer for the question")
    category: str = Field(description="The category of the question")

