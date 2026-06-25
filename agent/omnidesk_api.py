"""
Omnidesk API integration for the support agent.

Documentation: https://docs.omnidesk.io/omnidesk
"""

from typing import Optional
from dataclasses import dataclass

from web.config import OMNIDESK_API_KEY, OMNIDESK_API_BASE


@dataclass
class Ticket:
    id: int
    title: str
    description: str
    status: str
    customer_name: str
    customer_email: str
    tags: list[str]
    created_at: str


def _api_url(path: str) -> str:
    return f"{OMNIDESK_API_BASE}/api/v1{path}"


def get_ticket(ticket_id: int) -> Optional[Ticket]:
    if not OMNIDESK_API_KEY:
        return None

    import requests
    try:
        resp = requests.get(
            _api_url(f"/cases/{ticket_id}"),
            params={"apiKey": OMNIDESK_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return Ticket(
            id=data.get("id", ticket_id),
            title=data.get("subject", ""),
            description=data.get("description", ""),
            status=data.get("status", ""),
            customer_name=data.get("client_name", ""),
            customer_email=data.get("client_email", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
        )
    except Exception as e:
        print(f"Error fetching ticket {ticket_id}: {e}")
        return None


def add_note(ticket_id: int, text: str) -> bool:
    if not OMNIDESK_API_KEY:
        print(f"[SIMULATED] Note for ticket #{ticket_id}:\n{text}\n---")
        return True

    import requests
    try:
        resp = requests.post(
            _api_url(f"/cases/{ticket_id}/notes"),
            params={"apiKey": OMNIDESK_API_KEY},
            json={"note": {"text": text}},
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Error adding note to ticket {ticket_id}: {e}")
        return False


def get_new_tickets(status: str = "new") -> list[Ticket]:
    if not OMNIDESK_API_KEY:
        return []

    import requests
    try:
        resp = requests.get(
            _api_url("/cases"),
            params={"apiKey": OMNIDESK_API_KEY, "status": status},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        tickets = []
        for item in data.get("cases", []):
            tickets.append(Ticket(
                id=item.get("id", 0),
                title=item.get("subject", ""),
                description=item.get("description", ""),
                status=item.get("status", ""),
                customer_name=item.get("client_name", ""),
                customer_email=item.get("client_email", ""),
                tags=item.get("tags", []),
                created_at=item.get("created_at", ""),
            ))
        return tickets
    except Exception as e:
        print(f"Error fetching tickets: {e}")
        return []
