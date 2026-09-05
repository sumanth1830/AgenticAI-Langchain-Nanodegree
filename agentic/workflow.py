import operator
from typing import Annotated, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver

from agentic.agents.account_resolver import resolve_account_ticket
from agentic.agents.general_resolver import resolve_general_ticket
from agentic.agents.support_agents import classify_ticket, score_resolution, escalation_agent
from agentic.tools.rag_tools import fetch_user_history
from agentic.tools.persistence import persist_ticket

CONFIDENCE_THRESHOLD = 0.7


class State(MessagesState):
    user_id: str
    ticket_status: str
    ticket_data: dict
    thread_id: str
    resolution_confidence_score: float
    retrieved_docs: List[str]
    account_evidence: Optional[dict[str, list[str]]]
    escalation_reason: str
    route: str
    routing_reason: str
    decision_log: Annotated[List[Dict], operator.add]
    user_history: List[Document]
    response: Annotated[List[str | Dict], operator.add]
    current_resolution: Optional[dict]
    urgency: str


def intake_node(state: State) -> State:
    """Runs first on every invocation. Resets turn-scoped decision fields
    so phase-detection in supervisor_node/route_from_supervisor reflects
    THIS turn, not leftover results from a prior turn on the same thread_id."""
    return {
        "route": None,
        "resolution_confidence_score": None,
        "escalation_reason": None,
        "retrieved_docs": [],
        "account_evidence": None,
        "current_resolution": None,
    }



def supervisor_node(state: State) -> State:
    required_threshold = 0.85 if state.get("urgency") == "high" else CONFIDENCE_THRESHOLD
    if state.get("escalation_reason"):
        last_message = state["response"][-1]["answer"]
        message = AIMessage(content=last_message)
        persist_ticket(state, last_message, "escalated")
        return {"messages": [message]}

    elif state.get("resolution_confidence_score") is not None:
        if state["resolution_confidence_score"] >= required_threshold:
            final_answer = state["response"][-1]["answer"]
            message = AIMessage(content=final_answer)
            persist_ticket(state, final_answer, "resolved")
            return {"ticket_status": "resolved", "messages": [message]}
        else:
            return {}

    elif state.get("current_resolution") is not None:
        return {}

    elif state.get("route"):
        result = fetch_user_history(state["user_id"], state["ticket_data"]["content"])
        return {"user_history": result}

    else:
        return {}


def route_from_supervisor(state: State) -> str:
    required_threshold = 0.85 if state.get("urgency") == "high" else CONFIDENCE_THRESHOLD
    
    if state.get("escalation_reason"):
        return END

    elif state.get("resolution_confidence_score") is not None:
        return END if state["resolution_confidence_score"] >= required_threshold else "escalation"

    elif state.get("current_resolution") is not None:
        return "scorer"

    elif state.get("route"):
        return "account_resolver" if state["route"] == "account" else "general_resolver"

    else:
        if state.get("ticket_status") in ("resolved", "escalated"):
            return "escalation"
        return "classifier"


workflow = StateGraph(State)
workflow.add_node("intake_node", intake_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("classifier", classify_ticket)
workflow.add_node("account_resolver", resolve_account_ticket)
workflow.add_node("general_resolver", resolve_general_ticket)
workflow.add_node("scorer", score_resolution)
workflow.add_node("escalation", escalation_agent)

workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "classifier": "classifier",
        "account_resolver": "account_resolver",
        "general_resolver": "general_resolver",
        "scorer": "scorer",
        "escalation": "escalation",
        END: END,
    },
)

workflow.add_edge("intake_node", "supervisor")
workflow.add_edge("classifier", "supervisor")
workflow.add_edge("account_resolver", "supervisor")
workflow.add_edge("general_resolver", "supervisor")
workflow.add_edge("scorer", "supervisor")
workflow.add_edge("escalation", "supervisor")
workflow.set_entry_point("intake_node")

orchestrator = workflow.compile(checkpointer=MemorySaver())