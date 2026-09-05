from langchain_core.prompts import ChatPromptTemplate

from agentic.agents.config import llm
from agentic.agents.schemas import RouteDecision, ScoreOutput, EscalationOutput


def classify_ticket(state: dict) -> dict:
    """Classify the topic/category of a ticket inquiry."""
    ticket_query = state["ticket_data"]["content"]
    date = state["ticket_data"]["date"]
    tags = state["ticket_data"]["tags"]
    channel = state["ticket_data"]["channel"]
    route = ""
    routing_reason = ""
    confidence = 0.0

    classifier_prompt = ChatPromptTemplate.from_template(
        """
        You are the Classifier agent for a customer support system.
        Ticket: {ticket_query}

        Also assess this ticket's urgency based on its content AND metadata:
        - date: {date}
        - tags: {tags}
        - channel: {channel}

        Decide whether this ticket should route to "account" or "general":
        - "account" — answering requires looking up THIS user's specific data
        (their subscription status, blocked status, reservation history, etc.)
        - "general" — the answer is the same for any user (policy, how-to steps,
        pricing, navigation)

        Mark urgency as "high" if the ticket involves being locked out/blocked from
        the account, payment/billing failures, or channel signals suggesting
        time-sensitivity. Otherwise, "normal".

        Output urgency and a brief urgency_reason explaining what in the content or
        metadata drove that judgment.

        Tricky cases to get right:
        - "How do I reset my password?" → general (generic steps)
        - "I reset my password but I'm still blocked" → account (needs to check
        THIS user's blocked status)

        If the ticket is ambiguous, report low confidence rather than guessing —
        ambiguous tickets default to general routing downstream.

        Output: route, routing_reason (based on the test above, not a topic label),
        and confidence (0.0–1.0).
        """
    )
    ticket_classifier = llm.with_structured_output(RouteDecision)
    prompt = classifier_prompt.invoke({
        "ticket_query": ticket_query,
        "date": date,
        "tags": tags,
        "channel": channel,
    })
    response = ticket_classifier.invoke(prompt)
    
    urgency = response.urgency
    # override to general when confidence is low
    if response.confidence < 0.6:
        route = "general"
        routing_reason = "Routing to general as confidence of classification is low"
        confidence = response.confidence
    else:
        route = response.route
        routing_reason = response.routing_reason
        confidence = response.confidence
    
    decision_log = [
        {
            "agent": "classifier", "action": f"routed to {route}", "result": f"Reason: {routing_reason}, Confidence: {confidence}, Urgency: {urgency}, Urgency Reason: {response.urgency_reason}"
        }
    ]

    return {
        "route": route,
        "routing_reason": routing_reason,
        "decision_log": decision_log,
        "ticket_status": "in_progress",
        "urgency": urgency
    }


def score_resolution(state: dict) -> dict:
    """Score the response Provided by the Resolver Agents """
    response_answer_text = state["response"][-1]["answer"]
    ticket_query = state["ticket_data"]["content"]
    retrieved_docs = []
    if len(state.get("retrieved_docs", [])) > 0:
        retrieved_docs = state["retrieved_docs"]

    scorer_prompt = ChatPromptTemplate.from_template(
        """
        You are the Scorer agent. Evaluate a proposed answer against the evidence
        retrieved for it, and assign a confidence score.

        Evidence for this ticket will be in exactly one of two forms: 
        Either Retrieved Docs (knowledge-base articles) or Account Records (data queried directly from the database). 
        Whichever one is populated for this ticket is the evidence to check the answer against
        Do not penalize the answer if one of them is empty.

        Ticket Query: {ticket_query}
        Proposed Answer: {response}
        Retrieved Docs: {retrieved_docs}
        Account Records: {account_records}

        You'll see: the original ticket, the proposed answer, the evidence used, and
        whether the Resolver claimed the answer was "grounded" in that evidence.

        Check independently — don't just trust the Resolver's own claim:
        - Does the answer actually follow from the evidence, or go beyond it?
        - Does it directly address the ticket's question?
        - If grounded=True but the evidence is thin or unrelated, lower the score.
        - If grounded=False, confidence should generally be low.

        Output:
        - confidence: float between 0.0 and 1.0
        - scoring_reason: brief explanation of what supported or undermined the score
        """
    )

    # resolution_confidence_score, ticket_status, decision_log
    scorer = llm.with_structured_output(ScoreOutput)
    account_records = state.get("account_evidence", {})
    retrieved_docs_for_prompt = retrieved_docs if len(retrieved_docs) > 0 else "None"
    prompt = scorer_prompt.invoke({
        "response": response_answer_text, 
        "retrieved_docs": retrieved_docs_for_prompt,
        "ticket_query": ticket_query,
        "account_records": account_records
    })
    result = scorer.invoke(prompt)
    confidence_score = result.confidence
    scoring_reason = result.scoring_reason
    
    decision_log = [
        {"agent": "scorer", "action": f"Scored the response", "result": f"Reason: {scoring_reason}, Confidence: {confidence_score}"}
    ]

    return {
        "decision_log": decision_log,
        "resolution_confidence_score": confidence_score
    }


def escalation_agent(state: dict) -> dict:
    """Deals with the complex queries that need human intervention"""
    ticket_query = state["ticket_data"]["content"]
    response_answer_text = state["response"][-1]["answer"]
    escalation_prompt = ChatPromptTemplate.from_template(
        """
        You are the Escalation agent. A ticket could not be confidently resolved and
        needs to be handed off to a human support agent.

        You'll see: the original ticket, the answer that was attempted.
        Ticket Query: {ticket_query}
        Response: {response}

        Write two things:
        1. user_message — a short, reassuring message to the customer letting them
        know their ticket is being reviewed by the support team. Do not promise
        a specific resolution or timeline you don't know. Do not repeat internal
        scoring details (confidence numbers, "grounded" status) to the user.
        2. escalation_reason — an internal note for the human agent taking over.
        Summarize what was already attempted and why it fell short, so they don't
        have to start from scratch.
        """
    )

    escalator = llm.with_structured_output(EscalationOutput)
    prompt = escalation_prompt.invoke({
        "ticket_query": ticket_query,
        "response": response_answer_text
    })
    result = escalator.invoke(prompt)
    escalation_reason = result.escalation_reason
    ticket_status = "escalated"

    decision_log = [
        {"agent": "escalation", "action": f"Escalated", "result": f"Reason: {escalation_reason}"}
    ]
    response = [{
        "agent": "escalation",
        "answer": result.user_message,
    }]

    return {
        "decision_log": decision_log,
        "response": response,
        "ticket_status": ticket_status,
        "escalation_reason": escalation_reason,
    }
