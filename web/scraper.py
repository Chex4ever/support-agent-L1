import re
import time
import json
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlencode

import httpx
from bs4 import BeautifulSoup


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


class OmnideskScraper:
    def __init__(self, base_url: str = "https://iridi.omnidesk.ru", api_key: str = ""):
        self.api_key = api_key
        self.session = OmnideskSession(base_url=base_url)
        self.session.client.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        if self.api_key:
            self.session.client.headers.update({"apiKey": self.api_key})
            self.session.logged_in = True

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

        params = {"page": page, "per": per_page}
        if status_filter:
            params["status"] = status_filter

        url = f"{self.session.base_url}/staff/cases/list/custom/s_1;s_2"
        resp = self.session.client.get(url, params=params)
        resp.raise_for_status()

        tickets = []
        soup = BeautifulSoup(resp.text, "html.parser")

        for row in soup.select("table.cases-table tbody tr, .cases-list .case-item, tr.case"):
            t = self._parse_ticket_row(row)
            if t:
                tickets.append(t)

        return tickets

    def _parse_ticket_row(self, row) -> Optional[dict]:
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

        url = f"{self.session.base_url}/staff/cases/{ticket_id}"
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

    def _extract_text(self, soup, selector: str) -> str:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def close(self):
        self.session.client.close()
