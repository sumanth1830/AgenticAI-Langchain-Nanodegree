import uuid
from sqlalchemy import create_engine

from utils import get_session
from data.models.udahub import User as UdahubUser, TicketMetadata, Ticket, TicketMessage

udahub_db = "data/core/udahub.db"
engine = create_engine(f"sqlite:///{udahub_db}", echo=False)


def persist_ticket(state: dict, final_answer: str, final_status: str) -> None:
    """Save ticket resolution information for future reference"""
    udahub_db = "data/core/udahub.db"
    engine = create_engine(f"sqlite:///{udahub_db}", echo=False)
    with get_session(engine) as session:
        user = session.query(UdahubUser).filter_by(account_id="cultpass", external_user_id=state["user_id"]).first()
        if not user:
            user = UdahubUser(
                user_id=str(uuid.uuid4()),
                account_id="cultpass",
                external_user_id=state["user_id"],
                user_name=state["ticket_data"]["owner_name"],
            )
        
        ticket = Ticket(
            ticket_id=str(uuid.uuid4()),
            account_id="cultpass",
            user_id=user.user_id,
            channel=state["ticket_data"]["channel"],
        )
        metadata = TicketMetadata(
            ticket_id=ticket.ticket_id,
            status=final_status,
            main_issue_type=state["route"],
            tags=state["ticket_data"]["tags"],
        )
        first_message = TicketMessage(
            message_id=str(uuid.uuid4()),
            ticket_id=ticket.ticket_id,
            role=state["ticket_data"]["role"],
            content=state["ticket_data"]["content"],
        )
        ai_message = TicketMessage(
            message_id=str(uuid.uuid4()),
            ticket_id=ticket.ticket_id,
            role="ai",
            content=final_answer,
        )
        session.add_all([user, ticket, metadata, first_message, ai_message])
