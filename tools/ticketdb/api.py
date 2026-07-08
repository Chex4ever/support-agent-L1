from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from . import database as db
from .models import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    KBEntryCreate,
    KBEntryUpdate,
    KBEntryResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Omnigent TicketDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Tickets ─────────────────────────────────────────────


@app.get("/api/tickets", response_model=list[TicketResponse])
def list_tickets_api(status: str = None, product: str = None, search: str = None):
    return db.list_tickets(status=status, product=product, search=search)


@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket_api(ticket_id: str):
    t = db.get_ticket(ticket_id)
    if not t:
        raise HTTPException(404, f"Ticket '{ticket_id}' not found")
    return t


@app.post("/api/tickets", response_model=TicketResponse, status_code=201)
def create_ticket_api(body: TicketCreate):
    t = db.create_ticket(**body.model_dump())
    if not t:
        raise HTTPException(409, f"Ticket '{body.ticket_id}' already exists")
    return t


@app.put("/api/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket_api(ticket_id: str, body: TicketUpdate):
    existing = db.get_ticket(ticket_id)
    if not existing:
        raise HTTPException(404, f"Ticket '{ticket_id}' not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return db.update_ticket(ticket_id, **updates)


@app.delete("/api/tickets/{ticket_id}", status_code=204)
def delete_ticket_api(ticket_id: str):
    if not db.delete_ticket(ticket_id):
        raise HTTPException(404, f"Ticket '{ticket_id}' not found")


# ── KB ──────────────────────────────────────────────────


@app.get("/api/kb/categories", response_model=list[str])
def list_kb_categories_api():
    return db.list_kb_categories()


@app.get("/api/kb", response_model=list[KBEntryResponse])
def list_kb_api(category: str = None, search: str = None):
    return db.list_kb(category=category, search=search)


@app.get("/api/kb/{kb_id}", response_model=KBEntryResponse)
def get_kb_api(kb_id: int):
    entry = db.get_kb(kb_id)
    if not entry:
        raise HTTPException(404, f"KB entry #{kb_id} not found")
    return entry


@app.post("/api/kb", response_model=KBEntryResponse, status_code=201)
def create_kb_api(body: KBEntryCreate):
    entry = db.create_kb(**body.model_dump())
    if not entry:
        raise HTTPException(
            409,
            f"KB entry '{body.category}/{body.key}' already exists",
        )
    return entry


@app.put("/api/kb/{kb_id}", response_model=KBEntryResponse)
def update_kb_api(kb_id: int, body: KBEntryUpdate):
    existing = db.get_kb(kb_id)
    if not existing:
        raise HTTPException(404, f"KB entry #{kb_id} not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return db.update_kb(kb_id, **updates)


@app.delete("/api/kb/{kb_id}", status_code=204)
def delete_kb_api(kb_id: int):
    if not db.delete_kb(kb_id):
        raise HTTPException(404, f"KB entry #{kb_id} not found")
