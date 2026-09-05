from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from agentic.agents.config import llm
from agentic.agents.schemas import ResolverOutput, AccountResolverState
from agentic.tools.cultpass_tools import get_account_profile, get_reservation_history
from agentic.agents.utils import build_history_context

account_resolver = create_react_agent(
    name="account_resolver",
    prompt=SystemMessage(
        content=(
            """
            You are the Account Resolver agent. You handle tickets that require looking
            up specific user's CultPass account data.

            You have tools to check the user's subscription/account status and their
            reservation history. Always use the appropriate tool before answering — never
            guess or assume account details.

            If a tool returns no data or an error for this user, do not fabricate an
            answer. Set grounded=False and explain in your answer that the information
            could not be retrieved.

            You may also see relevant past interactions with this user below the ticket
            content, for background/personalization context only. Do not treat this
            history as evidence for grounding your answer — grounding still comes only
            from your tools.

            For every ticket, output:
            - answer: your response to the user, based only on what the tools returned
            - sources_used: which tool(s)/data you actually used (e.g. "subscription
            status", "reservation history")
            - grounded: true only if your answer is backed by actual tool results
            """
        )
    ),
    response_format=ResolverOutput,
    model=llm,
    tools=[get_account_profile, get_reservation_history],
    state_schema=AccountResolverState,
)

def resolve_account_ticket(state: dict) -> dict:

    result = account_resolver.invoke(
        input={
            "messages": [state["ticket_data"]["content"] + build_history_context(state)],
            "user_id": state["user_id"]
        }
    )

    ticket_status = "resolving"
    structured_output = result["structured_response"]
    account_evidence = {}
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            account_evidence.setdefault(msg.name, []).append(msg.content)

    response = [{
        "agent": "account_resolver",
        "answer": structured_output.answer,
        "grounded": structured_output.grounded,
    }]

    decision_log = [
        {"agent": "account_resolver", "action": "resolved ticket", "result": f"grounded={structured_output.grounded}"}
    ]
    return {
        "current_resolution": response[0],
        "decision_log": decision_log,
        "response": response, 
        "ticket_status": ticket_status,
        "account_evidence": account_evidence
    }