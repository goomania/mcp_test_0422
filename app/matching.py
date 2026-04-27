from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.db import get_conn, serialize


Days = Literal["MWF", "TR", "ANY"]


class StudentProfile(BaseModel):
    subjects: list[str] = Field(default_factory=list, description="Preferred subjects, e.g. ['CS','MATH']")
    days: Days = Field(default="ANY", description="Preferred meeting pattern")
    earliest_start: str | None = Field(default=None, description="HH:MM (24h), optional")
    latest_end: str | None = Field(default=None, description="HH:MM (24h), optional")
    only_open: bool = Field(default=False, description="If true, require open seats > 0")
    interests: str = Field(default="", description="Free-text interests; matched against course title")
    avoid_instructors: list[str] = Field(default_factory=list, description="Instructor names to avoid")
    prefer_instructors: list[str] = Field(default_factory=list, description="Instructor names to prefer")


class MatchRequest(BaseModel):
    student: StudentProfile
    top_n: int = Field(default=5, ge=1, le=20)
    max_per_subject: int | None = Field(default=3, ge=1, le=20)


class ScoreBreakdown(BaseModel):
    subject: float = 0
    days: float = 0
    time_window: float = 0
    open_seats: float = 0
    interests: float = 0
    instructor: float = 0


class MatchResult(BaseModel):
    course: dict[str, Any]
    score_total: float
    score_breakdown: ScoreBreakdown
    reasons: list[str]


class MatchResponse(BaseModel):
    student: StudentProfile
    candidates_considered: int
    results: list[MatchResult]


@dataclass(frozen=True)
class Weights:
    subject: float = 3.0
    days: float = 1.5
    time_window: float = 1.5
    open_seats: float = 1.0
    interests: float = 2.0
    prefer_instructor: float = 0.5
    avoid_instructor_penalty: float = 2.0
    full_section_penalty: float = 0.75


def _parse_hhmm(value: str) -> time | None:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return time(hour=hh, minute=mm)


def _parse_course_time_range(value: str) -> tuple[time, time] | None:
    # Expected format in seed data: "HH:MM-HH:MM"
    m = re.fullmatch(r"\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", value)
    if not m:
        return None
    start = _parse_hhmm(m.group(1))
    end = _parse_hhmm(m.group(2))
    if not start or not end:
        return None
    return start, end


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 3}


def _fetch_courses(subjects: list[str] | None = None, days: str | None = None) -> list[dict]:
    conn = get_conn()
    q = "SELECT * FROM courses WHERE 1=1"
    params: list[object] = []
    if subjects:
        placeholders = ",".join(["?"] * len(subjects))
        q += f" AND upper(subject) IN ({placeholders})"
        params.extend([s.upper() for s in subjects])
    if days and days != "ANY":
        q += " AND upper(days)=upper(?)"
        params.append(days)
    rows = [serialize(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return rows


def _passes_constraints(course: dict, student: StudentProfile) -> bool:
    if student.only_open and course.get("open_seats", 0) <= 0:
        return False

    if student.days != "ANY" and str(course.get("days", "")).upper() != student.days:
        return False

    # Time window constraints are optional and only applied if parseable.
    course_range = _parse_course_time_range(str(course.get("time", "")))
    if course_range:
        c_start, c_end = course_range
        if student.earliest_start:
            s_earliest = _parse_hhmm(student.earliest_start)
            if s_earliest and c_start < s_earliest:
                return False
        if student.latest_end:
            s_latest = _parse_hhmm(student.latest_end)
            if s_latest and c_end > s_latest:
                return False

    avoid = {a.strip().lower() for a in student.avoid_instructors if a.strip()}
    if avoid and str(course.get("instructor", "")).strip().lower() in avoid:
        return False

    return True


def _score_course(course: dict, student: StudentProfile, weights: Weights) -> tuple[float, ScoreBreakdown, list[str]]:
    bd = ScoreBreakdown()
    reasons: list[str] = []

    subj = str(course.get("subject", "")).upper()
    subj_pref = {s.strip().upper() for s in student.subjects if s.strip()}
    if subj_pref:
        if subj in subj_pref:
            bd.subject = weights.subject
            reasons.append(f"Subject match: {subj}.")
        else:
            bd.subject = 0.0
    else:
        # No subject preference: neutral (don’t reward/penalize).
        bd.subject = 0.0

    if student.days != "ANY":
        if str(course.get("days", "")).upper() == student.days:
            bd.days = weights.days
            reasons.append(f"Matches your days preference: {student.days}.")
    else:
        bd.days = 0.0

    # Time-window: reward only when student gave a window and course fits it.
    tw_reward = 0.0
    course_range = _parse_course_time_range(str(course.get("time", "")))
    if course_range and (student.earliest_start or student.latest_end):
        c_start, c_end = course_range
        ok = True
        if student.earliest_start:
            s_earliest = _parse_hhmm(student.earliest_start)
            if s_earliest and c_start < s_earliest:
                ok = False
        if student.latest_end:
            s_latest = _parse_hhmm(student.latest_end)
            if s_latest and c_end > s_latest:
                ok = False
        if ok:
            tw_reward = weights.time_window
            reasons.append("Fits your time window.")
    bd.time_window = tw_reward

    open_seats = int(course.get("open_seats", 0) or 0)
    if open_seats > 0:
        bd.open_seats = weights.open_seats
        reasons.append(f"Has open seats ({open_seats}).")
    else:
        bd.open_seats = -weights.full_section_penalty
        reasons.append("Currently full.")

    interest_tokens = _tokenize(student.interests or "")
    title_tokens = _tokenize(str(course.get("title", "")))
    if interest_tokens:
        overlap = len(interest_tokens & title_tokens)
        if overlap > 0:
            # Simple capped linear reward.
            bd.interests = min(1.0, overlap / 3.0) * weights.interests
            reasons.append("Matches your interests via course title keywords.")

    prefer = {p.strip().lower() for p in student.prefer_instructors if p.strip()}
    instructor = str(course.get("instructor", "")).strip().lower()
    if prefer and instructor in prefer:
        bd.instructor += weights.prefer_instructor
        reasons.append("Matches your preferred instructor.")

    total = float(bd.subject + bd.days + bd.time_window + bd.open_seats + bd.interests + bd.instructor)
    return total, bd, reasons


def match_courses(req: MatchRequest, weights: Weights | None = None) -> MatchResponse:
    weights = weights or Weights()
    student = req.student

    # Candidate generation: narrow by subject (if given) and days (if not ANY) at DB level.
    subj_pref = [s.strip().upper() for s in student.subjects if s.strip()]
    db_days = None if student.days == "ANY" else student.days
    candidates = _fetch_courses(subjects=subj_pref or None, days=db_days)

    filtered = [c for c in candidates if _passes_constraints(c, student)]

    scored: list[MatchResult] = []
    for c in filtered:
        total, bd, reasons = _score_course(c, student, weights)
        scored.append(MatchResult(course=c, score_total=total, score_breakdown=bd, reasons=reasons))

    scored.sort(
        key=lambda r: (
            r.score_total,
            int(r.course.get("open_seats", 0) or 0),
            str(r.course.get("time", "")),
            str(r.course.get("id", "")),
        ),
        reverse=True,
    )

    # Diversity: cap per subject if configured.
    results: list[MatchResult] = []
    per_subject: dict[str, int] = {}
    for r in scored:
        s = str(r.course.get("subject", "")).upper()
        if req.max_per_subject is not None:
            if per_subject.get(s, 0) >= req.max_per_subject:
                continue
        results.append(r)
        per_subject[s] = per_subject.get(s, 0) + 1
        if len(results) >= req.top_n:
            break

    return MatchResponse(student=student, candidates_considered=len(filtered), results=results)

