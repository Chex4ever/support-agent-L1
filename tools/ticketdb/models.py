from pydantic import BaseModel
from typing import Optional, List


class TicketCreate(BaseModel):
    ticket_id: str
    status: str = "pending"
    priority: str = "medium"
    product: str = ""
    client_name: str = ""
    summary: str = ""
    client_question: str = ""
    research_summary: str = ""
    reply_draft_path: str = ""
    reply_sent: int = 0
    related_files: List[str] = []
    notes: str = ""


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    product: Optional[str] = None
    client_name: Optional[str] = None
    summary: Optional[str] = None
    client_question: Optional[str] = None
    research_summary: Optional[str] = None
    reply_draft_path: Optional[str] = None
    reply_sent: Optional[int] = None
    related_files: Optional[List[str]] = None
    notes: Optional[str] = None


class TicketResponse(BaseModel):
    id: int
    ticket_id: str
    status: str
    priority: str
    product: str
    client_name: str
    summary: str
    client_question: str
    research_summary: str
    reply_draft_path: str
    reply_sent: int
    related_files: List[str]
    notes: str
    created_at: str
    updated_at: str


class KBEntryCreate(BaseModel):
    category: str
    key: str
    value: str = ""
    source: str = ""
    tags: List[str] = []


class KBEntryUpdate(BaseModel):
    category: Optional[str] = None
    key: Optional[str] = None
    value: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None


class KBEntryResponse(BaseModel):
    id: int
    category: str
    key: str
    value: str
    source: str
    tags: List[str]
    created_at: str
    updated_at: str
