from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.advisor import CourseAdvisor
from app.db import init_db
from app.matching import MatchRequest, match_courses

app = FastAPI(title="Course Advisor")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
advisor = CourseAdvisor()


class AskBody(BaseModel):
    question: str


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/ask")
def ask(body: AskBody):
    result = advisor.advise(body.question)
    return JSONResponse(result)


@app.post("/api/match")
def match(body: MatchRequest):
    result = match_courses(body)
    return JSONResponse(result.model_dump())


@app.on_event("shutdown")
def shutdown() -> None:
    advisor.client.close()
