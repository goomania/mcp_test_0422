"""Very small MCP-style server over stdio (JSON-RPC 2.0, one JSON object per line)."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from app.db import get_conn, init_db, serialize  # noqa: E402


def search_courses(subject: str | None = None, only_open: bool = False, days: str | None = None) -> list[dict]:
    conn = get_conn()
    q = "SELECT * FROM courses WHERE 1=1"
    params: list[object] = []
    if subject:
        q += " AND upper(subject)=upper(?)"
        params.append(subject)
    if days:
        q += " AND upper(days)=upper(?)"
        params.append(days)
    rows = [serialize(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    if only_open:
        rows = [r for r in rows if r["open_seats"] > 0]
    return rows


def get_course(course_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    conn.close()
    return serialize(row) if row else None


def list_tools() -> list[dict]:
    return [
        {
            "name": "search_courses",
            "description": "Search courses by subject, days, and open seat availability.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "only_open": {"type": "boolean"},
                    "days": {"type": "string"},
                },
            },
        },
        {
            "name": "get_course",
            "description": "Get exact course details by course id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "course_id": {"type": "string"},
                },
                "required": ["course_id"],
            },
        },
    ]


def handle_request(req: dict) -> dict:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"server": "course-mcp", "version": "0.1.0"}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "search_courses":
            result = search_courses(
                subject=args.get("subject"),
                only_open=bool(args.get("only_open", False)),
                days=args.get("days"),
            )
        elif name == "get_course":
            result = get_course(args["course_id"])
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": result}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}


def main() -> None:
    init_db()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle_request(req)
        except Exception as e:  # broad by design for server stability
            res = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
