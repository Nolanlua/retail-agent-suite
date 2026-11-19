"""Wiki API contracts."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PageCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=2, max_length=256)
    category: str = "general"
    source: str = ""
    content_md: str = Field(min_length=20)


class PageUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=256)
    content_md: str = Field(min_length=20)
    source: str = ""
    review_note: str = ""


class ReviewRequest(BaseModel):
    review_note: str = ""


class RevisionOut(BaseModel):
    version: int
    title: str
    content_md: str
    status: str
    reviewer: str
    review_note: str
    created_by: str
    created_at: datetime


class PageOut(BaseModel):
    slug: str
    title: str
    category: str
    source: str
    status: str
    current_version: int
    index_status: str
    content_md: str = ""
    updated_at: datetime


class WikiSearchHit(BaseModel):
    slug: str
    title: str
    source: str
    snippet: str
