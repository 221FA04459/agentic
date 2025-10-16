"""
SQLModel database schemas for persistence
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON


class Regulation(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    filename: str
    file_path: str
    regulation_type: str
    jurisdiction: str
    effective_date: Optional[str] = None
    extracted_text: str
    analysis_result: Dict[str, Any] = Field(sa_type=JSON)
    upload_date: str
    status: str


class ComplianceCheckRow(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    regulation_id: str = Field(index=True)
    result: Dict[str, Any] = Field(sa_type=JSON)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReportRow(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    regulation_id: str = Field(index=True)
    format: str
    file_path: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Monitoring tables
class Source(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    name: str
    url: str
    jurisdiction: str = "global"
    regulation_type: str = "general"
    enabled: bool = True
    due_days: int | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SourceVersion(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    source_id: str = Field(index=True)
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    hash: str
    title: str | None = None
    snippet: str | None = None


