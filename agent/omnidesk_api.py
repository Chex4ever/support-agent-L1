"""
Omnidesk API integration for the support agent.

ВАЖНО: РЕЖИМ ТОЛЬКО ЧТЕНИЕ! Агент НЕ создаёт, НЕ редактирует и НЕ удаляет
никакие данные в Omnidesk. Только GET-запросы.

Аутентификация: HTTP Basic Auth (staff_email:api_key)
Формат: https://domain.omnidesk.ru/api/[endpoint].json
"""

from typing import Optional
from dataclasses import dataclass
from requests.auth import HTTPBasicAuth

from web.config import OMNIDESK_API_KEY, OMNIDESK_STAFF_EMAIL, OMNIDESK_API_BASE


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
    priority: str = ""
    channel: str = ""
    group_id: int = 0
    staff_id: int = 0
    updated_at: str = ""
    case_number: str = ""


def _auth() -> Optional[HTTPBasicAuth]:
    if OMNIDESK_API_KEY and OMNIDESK_STAFF_EMAIL:
        return HTTPBasicAuth(OMNIDESK_STAFF_EMAIL, OMNIDESK_API_KEY)
    return None


def _api_url(endpoint: str) -> str:
    return f"{OMNIDESK_API_BASE}/api{endpoint}.json"


def get_ticket(ticket_id: int) -> Optional[Ticket]:
    auth = _auth()
    if not auth:
        return None

    import requests
    try:
        resp = requests.get(
            _api_url(f"/cases/{ticket_id}"),
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("case", {})
        return Ticket(
            id=data.get("case_id", ticket_id),
            title=data.get("subject", ""),
            description=data.get("description", ""),
            status=data.get("status", ""),
            customer_name=data.get("client_name", ""),
            customer_email=data.get("recipient", ""),
            tags=[str(l) for l in data.get("labels", [])],
            created_at=data.get("created_at", ""),
            priority=data.get("priority", ""),
            channel=data.get("channel", ""),
            group_id=data.get("group_id", 0),
            staff_id=data.get("staff_id", 0),
            updated_at=data.get("updated_at", ""),
            case_number=data.get("case_number", ""),
        )
    except Exception as e:
        print(f"Error fetching ticket {ticket_id}: {e}")
        return None


def get_new_tickets(status: str = "open", page: int = 1, limit: int = 100) -> list[Ticket]:
    auth = _auth()
    if not auth:
        return []

    import requests
    try:
        resp = requests.get(
            _api_url("/cases"),
            auth=auth,
            headers={"Content-Type": "application/json"},
            params={"status": status, "page": page, "limit": limit,
                     "sort": "updated_at_desc"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        tickets = []
        for key in data:
            if key == "total_count":
                continue
            item = data[key].get("case", data[key])
            tickets.append(Ticket(
                id=item.get("case_id", 0),
                title=item.get("subject", ""),
                description=item.get("description", ""),
                status=item.get("status", ""),
                customer_name=item.get("client_name", ""),
                customer_email=item.get("recipient", ""),
                tags=[str(l) for l in item.get("labels", [])],
                created_at=item.get("created_at", ""),
                priority=item.get("priority", ""),
                channel=item.get("channel", ""),
                group_id=item.get("group_id", 0),
                staff_id=item.get("staff_id", 0),
                updated_at=item.get("updated_at", ""),
                case_number=item.get("case_number", ""),
            ))
        return tickets
    except Exception as e:
        print(f"Error fetching tickets: {e}")
        return []


def get_messages(ticket_id: int, limit: int = 100) -> list[dict]:
    """Получение сообщений тикета (только чтение)."""
    auth = _auth()
    if not auth:
        return []

    import requests
    try:
        resp = requests.get(
            _api_url(f"/cases/{ticket_id}/messages"),
            auth=auth,
            headers={"Content-Type": "application/json"},
            params={"limit": limit, "order": "asc"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        messages = []
        for key in data:
            if key == "total_count":
                continue
            msg = data[key].get("message", data[key])
            messages.append({
                "id": msg.get("message_id"),
                "user_id": msg.get("user_id", 0),
                "staff_id": msg.get("staff_id", 0),
                "content": msg.get("content", "") or msg.get("content_html", ""),
                "note": msg.get("note", False),
                "created_at": msg.get("created_at", ""),
                "attachments": msg.get("attachments", []),
            })
        return messages
    except Exception as e:
        print(f"Error fetching messages for ticket {ticket_id}: {e}")
        return []


def get_customer(ticket_id: int) -> Optional[dict]:
    """Получение информации о клиенте из тикета (только чтение)."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        return None

    auth = _auth()
    if not auth:
        return {"name": ticket.customer_name, "email": ticket.customer_email}

    import requests
    try:
        resp = requests.get(
            _api_url("/users"),
            auth=auth,
            headers={"Content-Type": "application/json"},
            params={"user_email": ticket.customer_email},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for key in data:
            if key == "total_count":
                continue
            user = data[key].get("user", data[key])
            return {
                "id": user.get("user_id"),
                "name": user.get("user_full_name") or ticket.customer_name,
                "email": user.get("user_email") or ticket.customer_email,
                "phone": user.get("user_phone", ""),
                "company": user.get("company_name", ""),
                "created_at": user.get("created_at", ""),
            }
        return {"name": ticket.customer_name, "email": ticket.customer_email}
    except Exception as e:
        print(f"Error fetching customer info: {e}")
        return {"name": ticket.customer_name, "email": ticket.customer_email}
