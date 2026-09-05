from typing import List, Literal
from pydantic import BaseModel
from langgraph.prebuilt.chat_agent_executor import AgentStateWithStructuredResponse


class RouteDecision(BaseModel):
    """Used by Classifier once the ticket is classified"""
    route: Literal["account", "general"]
    routing_reason: str
    confidence: float
    urgency: Literal["normal", "high"]
    urgency_reason: str

class ResolverOutput(BaseModel):
    """Used by Resolver agents"""
    answer: str
    sources_used: List[str]  
    grounded: bool

class AccountResolverState(AgentStateWithStructuredResponse):
    user_id: str


class ScoreOutput(BaseModel):
    confidence: float
    scoring_reason: str


class EscalationOutput(BaseModel):
    user_message: str       
    escalation_reason: str 