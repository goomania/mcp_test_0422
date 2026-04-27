from __future__ import annotations

import os
from textwrap import dedent

import httpx


class AdviceProvider:
    def __init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.claude_key = os.getenv("ANTHROPIC_API_KEY")

    def generate(self, question: str, courses: list[dict]) -> str:
        if self.claude_key:
            try:
                return self._ask_claude(question, courses)
            except Exception:
                return self._fallback(question, courses)
        if self.gemini_key:
            try:
                return self._ask_gemini(question, courses)
            except Exception:
                return self._fallback(question, courses)
        return self._fallback(question, courses)

    def _prompt(self, question: str, courses: list[dict]) -> str:
        return dedent(
            f"""
            You are a concise academic course advisor.
            Student question: {question}
            Candidate courses: {courses}
            Give practical advice and explain why each suggested course fits.
            Mention seat availability and schedule considerations.
            """
        ).strip()

    def _ask_claude(self, question: str, courses: list[dict]) -> str:
        payload = {
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": self._prompt(question, courses)}],
        }
        headers = {
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=20) as client:
            r = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            r.raise_for_status()
        data = r.json()
        return data["content"][0]["text"]

    def _ask_gemini(self, question: str, courses: list[dict]) -> str:
        payload = {"contents": [{"parts": [{"text": self._prompt(question, courses)}]}]}
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-pro:generateContent?key={self.gemini_key}"
        )
        with httpx.Client(timeout=20) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _fallback(self, question: str, courses: list[dict]) -> str:
        if not courses:
            return "I couldn't find matching courses. Try mentioning subject (e.g., CS), days (MWF/TR), or open seats."
        top = sorted(courses, key=lambda c: c["open_seats"], reverse=True)[:3]
        lines = [f"Question: {question}", "Suggested courses:"]
        for c in top:
            lines.append(
                f"- {c['id']} {c['title']} ({c['days']} {c['time']}), open seats: {c['open_seats']}, instructor: {c['instructor']}"
            )
        lines.append("Tip: prioritize classes with open seats and no time conflicts in your plan.")
        return "\n".join(lines)
