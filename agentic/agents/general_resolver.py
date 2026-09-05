from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from agentic.agents.config import llm
from agentic.agents.schemas import ResolverOutput
from agentic.tools.rag_tools import search_knowledge_base
from agentic.agents.utils import build_history_context

general_resolver = create_react_agent(
    name="general_resolver",
    prompt=SystemMessage(
        content=(
            """
            You are the General Resolver agent. You handle tickets answerable from
            general CultPass knowledge — the same answer applies to any user.

            You have a tool to search the knowledge base for relevant support articles.
            Always search before answering — never answer from assumption alone.

            If no relevant article is found, do not guess or fabricate policy. Set
            grounded=False and emphasize inyour answer text itself that you couldn't find 
            relevant information, do not provide the information anyway from general knowledge.

            You may also see relevant past interactions with this user below the ticket
            content, for background/personalization context only. Do not treat this
            history as evidence for grounding your answer — grounding still comes only
            from your tools.

            For every ticket, output:
            - answer: your response to the user, based only on the retrieved article(s)
            - sources_used: the title(s) of the article(s) you actually used
            - grounded: true only if a relevant article was found and used
            """
        )
    ),
    response_format=ResolverOutput,
    model=llm,
    tools=[search_knowledge_base],
)

def resolve_general_ticket(state: dict) -> dict:
    
    result = general_resolver.invoke(
        input={
            "messages": [state["ticket_data"]["content"] + build_history_context(state)]
        }
    )

    ticket_status = "resolving"
    structured_output = result["structured_response"]
    response = [{
        "agent": "general_resolver",
        "answer": structured_output.answer,
        "grounded": structured_output.grounded,
    }]
    retrieved_docs = []
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            retrieved_docs.append(msg.content)
    
    decision_log = [
        {"agent": "general_resolver", "action": "resolved ticket", "result": f"grounded={structured_output.grounded}, sources_used={structured_output.sources_used}"}
    ]
    return {
        "current_resolution": response[0],
        "decision_log": decision_log,
        "response": response, 
        "ticket_status": ticket_status,
        "retrieved_docs": retrieved_docs
    }