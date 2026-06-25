import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from web.scraper import OmnideskScraper
from web.config import OMNIDESK_API_KEY, OMNIDESK_EMAIL, OMNIDESK_PASSWORD, HOST, PORT
from agent.recommender import generate as agent_generate

from jinja2 import Environment, FileSystemLoader

app = FastAPI(title="iRidi Support Agent L1", version="1.0.0")

_tpl_dir = Path(__file__).resolve().parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_tpl_dir)), autoescape=True)


def render(name: str, **context) -> str:
    tpl = _jinja_env.get_template(name)
    return tpl.render(**context)

_scraper: Optional[OmnideskScraper] = None
_tickets_cache: list[dict] = []
_analysed_tickets: dict[int, dict] = {}


def get_scraper() -> OmnideskScraper:
    global _scraper
    if _scraper is None:
        _scraper = OmnideskScraper(api_key=OMNIDESK_API_KEY)
        # Автологин из .env если указаны email/пароль
        if OMNIDESK_EMAIL and OMNIDESK_PASSWORD and not _scraper.session.logged_in:
            try:
                _scraper.login(OMNIDESK_EMAIL, OMNIDESK_PASSWORD)
            except Exception:
                pass
    return _scraper


@app.get("/", response_class=HTMLResponse)
async def index():
    s = get_scraper()
    if not s.session.logged_in:
        return HTMLResponse(render("login.html", error=""))
    return RedirectResponse(url="/tickets")


@app.get("/login", response_class=HTMLResponse)
async def login_page(error: str = ""):
    return HTMLResponse(render("login.html", error=error))


@app.post("/login", response_class=HTMLResponse)
async def login_submit(email: str = Form(...), password: str = Form(...)):
    s = get_scraper()
    try:
        ok = await asyncio.to_thread(s.login, email, password)
        if ok:
            return RedirectResponse(url="/tickets", status_code=303)
        return HTMLResponse(render("login.html", error="Неверный email или пароль. Проверьте данные и попробуйте снова."))
    except Exception as e:
        return HTMLResponse(render("login.html", error=f"Ошибка подключения к Omnidesk: {e}"))


@app.get("/logout")
async def logout():
    global _scraper, _tickets_cache, _analysed_tickets
    if _scraper:
        _scraper.close()
    _scraper = None
    _tickets_cache = []
    _analysed_tickets = {}
    return RedirectResponse(url="/login")


@app.get("/tickets", response_class=HTMLResponse)
async def tickets_page(page: int = 1, refresh: bool = False):
    s = get_scraper()
    if not s.session.logged_in:
        return RedirectResponse(url="/login")

    try:
        if refresh or not _tickets_cache:
            tickets = await asyncio.to_thread(s.get_ticket_list, page=page)
            _tickets_cache.clear()
            _tickets_cache.extend(tickets)

        return HTMLResponse(render("tickets.html",
            tickets=_tickets_cache,
            page=page,
            total=len(_tickets_cache),
        ))
    except Exception as e:
        return HTMLResponse(f"<h2>Ошибка загрузки тикетов</h2><pre>{e}</pre>")


@app.get("/api/tickets")
async def api_tickets(page: int = 1, refresh: bool = False):
    s = get_scraper()
    if not s.session.logged_in:
        raise HTTPException(401, "Not logged in")

    if refresh or not _tickets_cache:
        tickets = await asyncio.to_thread(s.get_ticket_list, page=page)
        _tickets_cache.clear()
        _tickets_cache.extend(tickets)

    return {"tickets": _tickets_cache, "total": len(_tickets_cache)}


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(ticket_id: int):
    s = get_scraper()
    if not s.session.logged_in:
        return RedirectResponse(url="/login")

    ticket = await asyncio.to_thread(s.get_ticket_detail, ticket_id)

    rec = None
    if ticket:
        text = f"{ticket.title}\n\n{ticket.description}"
        for m in ticket.messages:
            text += f"\n\n{m.get('body', '')}"
        rec = agent_generate(text)

        _analysed_tickets[ticket_id] = {
            "ticket": {
                "id": ticket.id,
                "title": ticket.title,
                "status": ticket.status,
                "customer": ticket.customer,
                "description": ticket.description,
                "messages": ticket.messages,
            },
            "recommendation": {
                "product": rec.product,
                "category": rec.problem_category,
                "confidence": rec.confidence,
                "urgency": rec.urgency_level,
                "suggested_answer": rec.suggested_answer,
                "doc_links": rec.doc_links,
                "clarifying_questions": rec.clarifying_questions,
                "notes": rec.notes_for_engineer,
            }
        }

    return HTMLResponse(render("ticket_detail.html", ticket=ticket, rec=rec))


@app.get("/api/tickets/{ticket_id}")
async def api_ticket_detail(ticket_id: int):
    s = get_scraper()
    if not s.session.logged_in:
        raise HTTPException(401, "Not logged in")

    ticket = await asyncio.to_thread(s.get_ticket_detail, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    text = f"{ticket.title}\n\n{ticket.description}"
    for m in ticket.messages:
        text += f"\n\n{m.get('body', '')}"
    rec = agent_generate(text)

    return {
        "ticket": {
            "id": ticket.id,
            "title": ticket.title,
            "status": ticket.status,
            "customer": ticket.customer,
            "group": ticket.group,
            "description": ticket.description,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "messages": ticket.messages,
        },
        "recommendation": {
            "product": rec.product,
            "category": rec.problem_category,
            "confidence": rec.confidence,
            "urgency": rec.urgency_level,
            "suggested_answer": rec.suggested_answer,
            "doc_links": rec.doc_links,
            "clarifying_questions": rec.clarifying_questions,
            "notes": rec.notes_for_engineer,
        }
    }


@app.on_event("shutdown")
async def shutdown():
    s = get_scraper()
    s.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
