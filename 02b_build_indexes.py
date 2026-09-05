"""
To builds the Chroma vector indexes needed by the agentic app.

Run this AFTER 01_external_db_setup.ipynb and 02_core_db_setup.ipynb,
and BEFORE running 03_agentic_app.py.

Run again any time the Knowledge base articles change, or periodically to
refresh the user-history index with newly resolved tickets.
"""
from agentic.tools.rag_tools import build_knowledge_index, build_user_history_index

if __name__ == "__main__":
    print("Building knowledge base index...")
    print(build_knowledge_index())

    print("Building user history index...")
    print(build_user_history_index())