def build_history_context(state: dict) -> str:
    history = state.get("user_history") or []
    if not history:
        return ""
    entries = "\n".join(f"- {doc.page_content}" for doc in history)
    return f"\n\nRelevant past interactions with this user:\n{entries}"