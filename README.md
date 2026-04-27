# Minimal Course Advisor + MCP Demo

This repo is intentionally simple so you can iterate later.



# To do list:

- reference [https://claude.ai/chat/013bb60e-1849-4fc3-8a0e-606b17b18fa4](https://claude.ai/chat/013bb60e-1849-4fc3-8a0e-606b17b18fa4) for all Q&A on this project so that i don't need to use up premium sessions inside cursor

## What it includes

1. **Web app (FastAPI + plain JS)** for natural-language course questions.
2. **Mock course database** (SQLite + seed JSON).
3. **Simple MCP-style server** exposing basic tools:
  - `search_courses`
  - `get_course`
4. **MCP client** used by the web app to query tools.
5. **Advice layer** that can use **Claude** or **Gemini** if API keys are provided, with local fallback logic otherwise.

## Project structure

- `app/main.py` - web server and endpoints
- `app/advisor.py` - flow: question -> filter extraction -> MCP tool calls -> advice text
- `app/mcp_client.py` - tiny JSON-RPC client over stdio
- `mcp_server/server.py` - tiny MCP-style tool server
- `app/llm_provider.py` - Claude/Gemini integration + fallback
- `app/db.py` - SQLite init and access
- `data/courses_seed.json` - mock data

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Optional LLM keys

Set either one:

```bash
export ANTHROPIC_API_KEY=...
# or
export GEMINI_API_KEY=...
```

If no key is set, the app still works with deterministic fallback advice.

## Example questions

- `What CS courses have open seats?`
- `I want MATH classes on TR with available seats`
- `Any MWF class for writing or history?`

