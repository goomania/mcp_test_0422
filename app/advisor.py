from __future__ import annotations

import re

from app.llm_provider import AdviceProvider
from app.mcp_client import MCPClient

SUBJECTS = {"CS", "MATH", "BIO", "ENG", "HIST"}
DAYS = {"MWF", "TR"}


class CourseAdvisor:
    def __init__(self) -> None:
        self.client = MCPClient()
        self.provider = AdviceProvider()

    def advise(self, question: str) -> dict:
        filters = self._extract_filters(question)
        courses = self.client.search_courses(**filters)
        answer = self.provider.generate(question, courses)
        return {"filters": filters, "courses": courses, "advice": answer}

    def _extract_filters(self, question: str) -> dict:
        q = question.upper()
        subject = next((s for s in SUBJECTS if re.search(rf"\b{s}\b", q)), None)
        days = next((d for d in DAYS if re.search(rf"\b{d}\b", q)), None)
        only_open = bool(re.search(r"\b(open|available|seat|seats)\b", q.lower()))
        return {"subject": subject, "days": days, "only_open": only_open}
