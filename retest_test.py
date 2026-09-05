import shutil
from sqlalchemy import create_engine

from utils import get_session
from data.models.udahub import Ticket, TicketMetadata, TicketMessage
from agentic.tools.rag_tools import HISTORY_PERSIST_DIR


def reset_test_data():
    """Clears ticket-related tables and the user-history vector index,
    for a clean slate between test runs. Does NOT touch cultpass.db or
    the knowledge-base index, since those are static/external data."""
    udahub_db = "data/core/udahub.db"
    engine = create_engine(f"sqlite:///{udahub_db}", echo=False)
    with get_session(engine) as session:
        session.query(TicketMessage).delete()
        session.query(TicketMetadata).delete()
        session.query(Ticket).delete()

    shutil.rmtree(HISTORY_PERSIST_DIR, ignore_errors=True)


if __name__ == "__main__":
    reset_test_data()
    print("Test data reset complete.")