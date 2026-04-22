from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


class MCPClient:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parent.parent
        server_path = root / "mcp_server" / "server.py"
        self.proc = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._id = 0
        self._call("initialize", {})

    def _call(self, method: str, params: dict) -> dict:
        self._id += 1
        req = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        res = json.loads(line)
        if "error" in res:
            raise RuntimeError(res["error"]["message"])
        return res["result"]

    def search_courses(self, **kwargs) -> list[dict]:
        result = self._call("tools/call", {"name": "search_courses", "arguments": kwargs})
        return result["content"]

    def get_course(self, course_id: str) -> dict | None:
        result = self._call("tools/call", {"name": "get_course", "arguments": {"course_id": course_id}})
        return result["content"]

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
