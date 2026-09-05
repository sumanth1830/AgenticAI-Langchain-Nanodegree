from datetime import datetime
import json
# Domain-accurate CultPass test tickets.
# cultpass_users indices assumed loaded from cultpass_users.jsonl, e.g.:
#   cultpass_users[0] -> Alice Kingsley (is_blocked=True)
#   cultpass_users[1] -> Bob Stone
#   cultpass_users[2] -> Cathy Bloom
#   cultpass_users[3] -> David Noir (is_blocked=True)
#   cultpass_users[4] -> Eva Green
#   cultpass_users[5] -> Frank Ocean


with open("data/external/cultpass_users.jsonl", "r", encoding="utf-8") as f:
    cultpass_users = [json.loads(line) for line in f]


tickets = [
    # 1. GENERAL — should route to General Resolver, hit a real KB article
    # ("How to Reserve a Spot for an Event"), resolve with high confidence.
    {
        "status": "open",
        "date": datetime.now().isoformat(),
        "content": "How do I reserve a spot for an experience on CultPass?",
        "user_id": cultpass_users[1]["id"],
        "owner_name": cultpass_users[1]["name"],
        "role": "user",
        "channel": "chat",
        "tags": "reservation, events, booking",
    },

    # 2. ACCOUNT — should route to Account Resolver, needs a real DB lookup
    # against this specific user's blocked status (Alice is is_blocked=True).
    {
        "status": "open",
        "date": datetime.now().isoformat(),
        "content": "I keep getting blocked from logging in, can you check my account status?",
        "user_id": cultpass_users[0]["id"],
        "owner_name": cultpass_users[0]["name"],
        "role": "user",
        "channel": "chat",
        "tags": "login, access, account",
    },

    # 3. ACCOUNT — subscription-tier lookup specific to this user.
    {
        "status": "open",
        "date": datetime.now().isoformat(),
        "content": "What subscription tier am I currently on, and how many experiences do I have left this month?",
        "user_id": cultpass_users[2]["id"],
        "owner_name": cultpass_users[2]["name"],
        "role": "user",
        "channel": "chat",
        "tags": "subscription, quota, account",
    },

    # 4. AMBIGUOUS — vague enough to plausibly trigger low classification
    # confidence, exercising the "fallback to general" path.
    {
        "status": "open",
        "date": datetime.now().isoformat(),
        "content": "Something's wrong with my pass, can you help?",
        "user_id": cultpass_users[4]["id"],
        "owner_name": cultpass_users[4]["name"],
        "role": "user",
        "channel": "chat",
        "tags": "issue, pass",
    },

    # 5. ESCALATE — general in nature (no specific user data needed) but not
    # covered by any of the 19 KB articles, so General Resolver should come
    # back grounded=False, Scorer should score low, Escalation should trigger.
    {
        "status": "open",
        "date": datetime.now().isoformat(),
        "content": "Can I gift my unused monthly experiences to a friend who isn't a CultPass member?",
        "user_id": cultpass_users[5]["id"],
        "owner_name": cultpass_users[5]["name"],
        "role": "user",
        "channel": "chat",
        "tags": "gifting, experiences, sharing",
    },
]

# 6. REOPENED-TICKET scenario — submit_ticket(tickets[0], thread_id=X) once,
# then submit_ticket(followup_message, thread_id=X) again with the SAME
# thread_id, to confirm Supervisor's reopened-ticket branch routes straight
# to Escalation instead of re-running Classifier/Resolver/Scorer.
followup_message = {
    "status": "open",
    "date": datetime.now().isoformat(),
    "content": "That didn't actually fix it, I'm still having the same problem.",
    "user_id": cultpass_users[1]["id"],
    "owner_name": cultpass_users[1]["name"],
    "role": "user",
    "channel": "chat",
    "tags": "follow-up",
}

# 7. MEMORY TEST — same user as ticket #1 (Bob Stone), a DIFFERENT but
# semantically related question, submitted as a NEW ticket (new thread_id).
# After ticket #1 is persisted and build_user_history_index() is re-run,
# this should retrieve that prior "how to reserve" interaction via
# similarity search and populate state["user_history"].
memory_test_ticket = {
    "status": "open",
    "date": datetime.now().isoformat(),
    "content": "I tried reserving a spot for an event but got an error, can you check what happened?",
    "user_id": cultpass_users[1]["id"],
    "owner_name": cultpass_users[1]["name"],
    "role": "user",
    "channel": "chat",
    "tags": "reservation, error, booking",
}