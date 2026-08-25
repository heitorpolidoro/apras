"""Protocol number generator service for Occurrences."""

from datetime import datetime

from sqlmodel import Session, select

from app.models.occurrence import Occurrence


def generate_occurrence_protocol(session: Session) -> str:
    """
    Generates a sequential protocol string in the format 'OCO-YYYY-XXXXXX'.
    Sequence resets each calendar year.

    Args:
        session: Active SQLModel session.

    Returns:
        Formatted protocol string (e.g. 'OCO-2026-000001').
    """
    year = datetime.utcnow().year
    prefix = f"OCO-{year}-"

    statement = (
        select(Occurrence.protocol_number)
        .where(Occurrence.protocol_number.like(f"{prefix}%"))
        .order_by(Occurrence.protocol_number.desc())
        .limit(1)
    )
    last_protocol = session.exec(statement).first()

    if not last_protocol:
        next_seq = 1
    else:
        try:
            raw_seq = last_protocol.split("-")[-1]
            next_seq = int(raw_seq) + 1
        except (ValueError, IndexError):
            next_seq = 1

    return f"{prefix}{next_seq:06d}"
