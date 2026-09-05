from typing import Annotated
from sqlalchemy import create_engine
from langgraph.prebuilt import InjectedState

from utils import get_session
from data.models.cultpass import User as CultpassUser

cultpass_db = "data/external/cultpass.db"
engine = create_engine(f"sqlite:///{cultpass_db}", echo=False)

def get_account_profile(user_id: Annotated[str, InjectedState("user_id")]) -> dict:
    """Returns subscription tier, status, monthly quota, and whether the account is blocked."""
    with get_session(engine) as session:
        user = session.get(CultpassUser, user_id)
        if user is None:
            return {"error": "User not found"}
        subscription = user.subscription
        if subscription is None:
            return {"message": "User has no subscription"}
        
        return {
            "tier": subscription.tier,
            "status": subscription.status,
            "monthly_quota": subscription.monthly_quota,
            "started_at": subscription.started_at,
            "ended_at": subscription.ended_at,
            "is_blocked": user.is_blocked,
        }

def get_reservation_history(user_id: Annotated[str, InjectedState("user_id")]) -> list[dict]:
    """Returns the user's reservations with experience details and status."""
    experiences = []
    with get_session(engine) as session:
        user = session.get(CultpassUser, user_id)
        if user is None:
            return [{"error": "User not found"}]
        reservations = user.reservations
        if len(reservations) == 0:
            return []
        else:
            for reservation in reservations:
                experience = reservation.experience
                experiences.append(
                    {
                        "title": experience.title,
                        "location": experience.location,
                        "when": experience.when,
                        "slots_available": experience.slots_available,
                        "is_premium": experience.is_premium,
                        "status": reservation.status,

                    }
                )
    
    return experiences