from __future__ import annotations

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    title: str
    date: str
    filename: str


class ReportDetail(ReportSummary):
    content: str


class ReportListResponse(BaseModel):
    reports: list[ReportSummary] = Field(default_factory=list)
