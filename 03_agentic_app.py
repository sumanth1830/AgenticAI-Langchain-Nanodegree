"""
UDA-Hub Agentic App — Entry point for running and demonstrating the
multi-agent ticket resolution system end-to-end.

Run this file directly:
    python 03_agentic_app.py
"""
import uuid
from datetime import datetime

from agentic.workflow import orchestrator
from langchain_core.messages import HumanMessage
from agentic.tools.rag_tools import build_user_history_index


def submit_ticket(ticket: dict, thread_id: str = None) -> dict:
    is_new_ticket = thread_id is None
    thread_id = str(uuid.uuid4()) if is_new_ticket else thread_id

    state_dict = {
        "messages": [HumanMessage(content=ticket["content"])],
        "ticket_data": ticket,
        "user_id": ticket["user_id"],
        "thread_id": thread_id,
    }
    if is_new_ticket:
        state_dict["ticket_status"] = "open"

    result = orchestrator.invoke(
        input=state_dict,
        config={"configurable": {"thread_id": thread_id}},
    )
    return result

def print_result(label: str, result: dict):
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")
    print(f"User query: {result['ticket_data']['content']}")
    print(f"Status: {result.get('ticket_status')}")
    print(f"Route: {result.get('route')}")
    print(f"Urgency: {result.get('urgency')}")
    print(f"Confidence: {result.get('resolution_confidence_score')}")
    print(f"Final answer: {result['messages'][-1].content}")
    print(f"\nDecision log:")
    for entry in result.get("decision_log", []):
        print(f"  - [{entry['agent']}] {entry['action']}: {entry['result']}")


if __name__ == "__main__":
    from sample_tickets import tickets, memory_test_ticket, followup_message

    # --- Scenario 1-5: core routing/resolution/escalation paths ---
    labels = ["General (resolve)", "Account - blocked", "Account - subscription",
              "Ambiguous", "Escalate (no KB match)"]
    for label, ticket in zip(labels, tickets):
        result = submit_ticket(ticket)
        print_result(label, result)

    build_user_history_index()
    # --- Scenario 6: reopened ticket (same thread_id, new message) ---
    first_thread = str(uuid.uuid4())
    r1 = submit_ticket(tickets[0], thread_id=first_thread)
    print_result("Reopened ticket - initial", r1)
    r2 = submit_ticket(followup_message, thread_id=first_thread)
    print_result("Reopened ticket - follow-up (should escalate directly)", r2)

    # --- Scenario 7: returning customer / long-term memory ---
    r3 = submit_ticket(memory_test_ticket)
    print_result("Returning customer (user_history check)", r3)
    print(r3.get('user_history'))
    print(f"\nuser_history entries retrieved: {len(r3.get('user_history') or [])}")