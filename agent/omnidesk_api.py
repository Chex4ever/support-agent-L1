"""
Omnidesk API integration for the support agent.

Documentation: https://docs.omnidesk.io/omnidesk

Current state: stub for Phase 2.
Actual integration requires API token and endpoint configuration.
"""

import os
from typing import Optional
from dataclasses import dataclass

OMNIDESK_API_BASE = os.getenv("OMNIDESK_API_BASE", "https://iridi.omnidesk.ru/api/v1")
OMNIDESK_API_TOKEN = os.getenv("OMNIDESK_API_TOKEN", "")


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


def get_ticket(ticket_id: int) -> Optional[Ticket]:
    if not OMNIDESK_API_TOKEN:
        return None

    import requests
    try:
        resp = requests.get(
            f"{OMNIDESK_API_BASE}/cases/{ticket_id}",
            auth=(OMNIDESK_API_TOKEN, "X"),
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
    if not OMNIDESK_API_TOKEN:
        print(f"[SIMULATED] Note for ticket #{ticket_id}:\n{text}\n---")
        return True

    import requests
    try:
        resp = requests.post(
            f"{OMNIDESK_API_BASE}/cases/{ticket_id}/notes",
            auth=(OMNIDESK_API_TOKEN, "X"),
            json={"note": {"text": text}},
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Error adding note to ticket {ticket_id}: {e}")
        return False


def get_new_tickets(status: str = "new") -> list[Ticket]:
    if not OMNIDESK_API_TOKEN:
        return []

    import requests
    try:
        resp = requests.get(
            f"{OMNIDESK_API_BASE}/cases",
            auth=(OMNIDESK_API_TOKEN, "X"),
            params={"status": status},
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
