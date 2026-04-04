from pydantic import BaseModel, Field

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

class RetrievalEval(BaseModel):
    """
    Retrieval evaluation from metric based Eval
    """
    MRR: float = Field(description="The MRR of the retrieval results, on a scale of 0 to 1")
    keyword_coverage: float = Field(description="The Keyword Coverage of the retrieval results, on a scale of 0 to 1")

class RerankOrder(BaseModel):
    order: list[int] = Field(description="The order of the documents based on the relevance to the question")

class AgentRoutingEval(BaseModel):
    """Per-question agent routing evaluation result."""
    question: str
    expected_agents: list[str]
    activated_agents: list[str]
    routing_correct: bool

class MultiAgentEvalResult(BaseModel):
    """Aggregated multi-agent evaluation metrics."""
    agent_routing_accuracy: float = Field(description="ARA: fraction of test questions where correct agents were activated")
    agent_context_redundancy_ratio: float = Field(description="ACRR: ratio of unique docs to total docs across agents (higher = more diverse)")
    per_agent_mrr: dict = Field(description="MRR score per agent name")
    synthesis_faithfulness: float = Field(description="RAGAS faithfulness of synthesis output against merged context")
    parallel_efficiency: float = Field(description="max(agent_latencies) / sum(agent_latencies) — approaches 1/N for N parallel agents")
    total_questions: int
    routing_details: list[AgentRoutingEval] = Field(default_factory=list)