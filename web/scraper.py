import re
import time
import json
from typing import Optional
from dataclasses import dataclass, field

import httpx
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup

from web.config import OMNIDESK_API_KEY, OMNIDESK_STAFF_EMAIL


@dataclass
class Ticket:
    id: int
    number: str
    title: str
    status: str
    group: str
    customer: str
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    messages: list[dict] = field(default_factory=list)


@dataclass
class OmnideskSession:
    base_url: str = "https://iridi.omnidesk.ru"
    client: httpx.Client = field(default_factory=lambda: httpx.Client(verify=False, timeout=60))
    logged_in: bool = False
    csrf_token: str = ""
    use_api: bool = False


class OmnideskScraper:
    def __init__(self, base_url: str = "https://iridi.omnidesk.ru", api_key: str = ""):
        self.api_key = api_key or OMNIDESK_API_KEY
        self.staff_email = OMNIDESK_STAFF_EMAIL
        self.base_url = base_url
        self.session = OmnideskSession(base_url=base_url)
        self.session.client.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        if self.api_key and self.staff_email:
            self.session.use_api = True
            self.session.logged_in = True
            self.session.client.auth = (self.staff_email, self.api_key)
            self.session.client.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json",
            })

    def _get_csrf(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", attrs={"name": "csrf-token"})
        if meta and meta.get("content"):
            return meta["content"]
        inp = soup.find("input", attrs={"name": "_token"})
        if inp and inp.get("value"):
            return inp["value"]
        inp = soup.find("input", attrs={"name": "authenticity_token"})
        if inp and inp.get("value"):
            return inp["value"]
        return ""

    def login(self, email: str, password: str) -> bool:
        if self.session.use_api:
            self.session.logged_in = True
            return True

        resp = self.session.client.get(f"{self.session.base_url}/staff", follow_redirects=True)
        resp.raise_for_status()

        csrf = self._get_csrf(resp.text)
        self.session.csrf_token = csrf

        login_data = {
            "staff[email]": email,
            "staff[password]": password,
        }
        if csrf:
            login_data["_token"] = csrf
            login_data["authenticity_token"] = csrf

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.session.base_url,
            "Referer": f"{self.session.base_url}/staff",
        }

        resp = self.session.client.post(
            f"{self.session.base_url}/staff/auth",
            data=login_data,
            headers=headers,
            follow_redirects=True,
        )

        if resp.status_code == 200 and ("staff/auth" not in str(resp.url)):
            self.session.logged_in = True
            return True

        if "logout" in resp.text.lower() or "cases" in resp.text.lower():
            self.session.logged_in = True
            return True

        return False

    def get_ticket_list(self, page: int = 1, per_page: int = 50, status_filter: str = "") -> list[dict]:
        if not self.session.logged_in:
            raise RuntimeError("Not logged in. Call login() first.")

        if self.session.use_api:
            params = {"page": page, "limit": per_page, "sort": "updated_at_desc"}
            if status_filter:
                params["status"] = status_filter
            url = f"{self.base_url}/api/cases.json"
        else:
            params = {"page": page, "per": per_page}
            if status_filter:
                params["status"] = status_filter
            url = f"{self.base_url}/staff/cases/list/custom/s_1;s_2"

        resp = self.session.client.get(url, params=params)
        resp.raise_for_status()

        if self.session.use_api:
            return self._parse_api_ticket_list(resp.json())

        tickets = []
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("table.cases-table tbody tr, .cases-list .case-item, tr.case"):
            t = self._parse_ticket_row_html(row)
            if t:
                tickets.append(t)
        return tickets

    def _parse_api_ticket_list(self, data: dict) -> list[dict]:
        tickets = []
        for key in data:
            if key == "total_count":
                continue
            item = data[key]
            if isinstance(item, dict) and "case" in item:
                item = item["case"]
            tickets.append({
                "id": item.get("case_id", 0),
                "title": item.get("subject", ""),
                "status": item.get("status", ""),
                "customer": "",
                "updated_at": item.get("updated_at", ""),
                "url": f"/staff/cases/{item.get('case_id', 0)}",
                "priority": item.get("priority", ""),
                "channel": item.get("channel", ""),
                "case_number": item.get("case_number", ""),
            })
        return tickets

    def _parse_ticket_row_html(self, row) -> Optional[dict]:
        cells = row.find_all("td")
        if len(cells) < 5:
            return None

        id_elem = row.get("data-id") or row.get("id", "")
        if id_elem:
            ticket_id = int(re.sub(r"\D", "", str(id_elem))) if re.sub(r"\D", "", str(id_elem)) else 0
        else:
            ticket_id = 0

        title_link = row.select_one("a.case-title, .subject a, td:nth-child(2) a")
        title = title_link.get_text(strip=True) if title_link else ""
        ticket_href = title_link.get("href", "") if title_link else ""

        if not ticket_id and ticket_href:
            ids = re.findall(r"/(\d+)", ticket_href)
            if ids:
                ticket_id = int(ids[-1])

        status_elem = row.select_one(".case-status, td:nth-child(3), .status")
        status = status_elem.get_text(strip=True) if status_elem else ""

        customer_elem = row.select_one(".case-customer, td:nth-child(4), .customer")
        customer = customer_elem.get_text(strip=True) if customer_elem else ""

        date_elem = row.select_one(".case-date, td:nth-child(5), .date, time")
        updated_at = date_elem.get_text(strip=True) if date_elem else ""
        if date_elem and date_elem.get("datetime"):
            updated_at = date_elem["datetime"]

        return {
            "id": ticket_id,
            "title": title,
            "status": status,
            "customer": customer,
            "updated_at": updated_at,
            "url": ticket_href,
        }

    def get_ticket_detail(self, ticket_id: int) -> Optional[Ticket]:
        if not self.session.logged_in:
            raise RuntimeError("Not logged in")

        if self.session.use_api:
            return self._get_ticket_detail_api(ticket_id)

        url = f"{self.base_url}/staff/cases/{ticket_id}"
        resp = self.session.client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        t = Ticket(id=ticket_id, number="", title="", status="", group="",
                   customer="", created_at="", updated_at="")

        t.title = self._extract_text(soup, "h1, .case-subject, .subject-text")
        t.status = self._extract_text(soup, ".case-status-badge, .status-badge, .status")
        t.customer = self._extract_text(soup, ".case-customer-name, .customer-name, .client-name")
        t.group = self._extract_text(soup, ".case-group, .group-name, .assigned-group")

        desc_elem = soup.select_one(".case-description, .description-text, .ticket-body")
        if desc_elem:
            t.description = desc_elem.get_text(strip=True)

        msgs = []
        for msg in soup.select(".message-item, .timeline-item, .case-message"):
            author = self._extract_text(msg, ".message-author, .author, .sender-name")
            body = self._extract_text(msg, ".message-body, .body-text, .content")
            date = self._extract_text(msg, ".message-date, .date, time")
            if body:
                msgs.append({"author": author, "body": body, "date": date})
        t.messages = msgs

        return t

    def _get_ticket_detail_api(self, ticket_id: int) -> Optional[Ticket]:
        resp = self.session.client.get(f"{self.base_url}/api/cases/{ticket_id}.json")
        resp.raise_for_status()
        data = resp.json().get("case", {})

        t = Ticket(
            id=data.get("case_id", ticket_id),
            number=data.get("case_number", ""),
            title=data.get("subject", ""),
            status=data.get("status", ""),
            group="",
            customer="",
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            description=data.get("description", ""),
        )
        t.tags = [str(l) for l in data.get("labels", [])]

        msgs_resp = self.session.client.get(
            f"{self.base_url}/api/cases/{ticket_id}/messages.json",
            params={"limit": 100, "order": "asc"},
        )
        if msgs_resp.status_code == 200:
            msgs_data = msgs_resp.json()
            for key in msgs_data:
                if key == "total_count":
                    continue
                msg = msgs_data[key]
                if isinstance(msg, dict) and "message" in msg:
                    msg = msg["message"]
                content = msg.get("content") or msg.get("content_html", "")
                author = "Пользователь" if msg.get("user_id") else "Сотрудник"
                t.messages.append({
                    "author": author,
                    "body": content,
                    "date": msg.get("created_at", ""),
                    "note": msg.get("note", False),
                    "staff_id": msg.get("staff_id", 0),
                    "user_id": msg.get("user_id", 0),
                })

        return t

    def _extract_text(self, soup, selector: str) -> str:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def close(self):
        self.session.client.close()
