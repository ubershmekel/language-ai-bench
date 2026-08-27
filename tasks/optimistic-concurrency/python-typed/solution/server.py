import hashlib
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

Task = dict[str, Any]
Record = dict[str, Any]

records: dict[str, Record] = {
    "1": {"task": {"id": "1", "title": "calibrate", "done": False}, "version": 1}
}
next_id = 2
lock = threading.Lock()
sabotage = os.getenv("LAB_SABOTAGE", "")


def tag(rec: Record) -> str:
    if sabotage == "off-by-one":
        return '"v' + str(rec["version"]) + '"'
    payload = (
        json.dumps(rec["task"], sort_keys=True, separators=(",", ":"))
        + ":"
        + str(rec["version"])
    )
    return '"' + hashlib.sha256(payload.encode()).hexdigest()[:16] + '"'


class Handler(BaseHTTPRequestHandler):
    def body(self) -> dict[str, Any]:
        parsed: dict[str, Any] = json.loads(
            self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}"
        )
        return parsed

    def send(self, status: int, value: object = None, etag: str | None = None) -> None:
        data = b"" if value is None else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        if etag:
            self.send_header("etag", etag)
        self.end_headers()
        self.wfile.write(data)

    def route(self) -> None:
        global next_id
        parts = self.path.split("?", 1)[0].strip("/").split("/")
        if parts[0] != "tasks" or len(parts) > 2:
            return self.send(404, {"error": "not found"})
        ident = parts[1] if len(parts) == 2 else None
        if self.command == "GET" and ident is None:
            return self.send(200, [item["task"] for item in records.values()])
        if self.command == "POST" and ident is None:
            value = self.body()
            task: Task = {
                "id": str(next_id),
                "title": value.get("title"),
                "done": bool(value.get("done", False)),
            }
            next_id += 1
            rec: Record = {"task": task, "version": 1}
            records[task["id"]] = rec
            return self.send(201, task, tag(rec))
        if ident is None or ident not in records:
            return self.send(404, {"error": "not found"})
        rec = records[ident]
        if self.command == "GET":
            return self.send(200, rec["task"], tag(rec))
        if self.command in ("PUT", "PATCH", "DELETE"):
            supplied = self.headers.get("if-match")
            if not supplied:
                return self.send(428, {"error": "precondition"})
            if supplied != tag(rec) and sabotage != "missing-error-branch":
                return self.send(
                    409 if sabotage == "wrong-status-code" else 412,
                    {"error": "precondition"},
                )
        if self.command == "DELETE":
            with lock:
                records.pop(ident, None)
            return self.send(204)
        if self.command in ("PUT", "PATCH"):
            before = tag(rec)
            value = self.body()
            if sabotage == "unhandled-concurrent-update":
                time.sleep(0.08)
            with lock:
                current = records.get(ident)
                if sabotage not in (
                    "unhandled-concurrent-update",
                    "missing-error-branch",
                ) and (current is None or tag(current) != before):
                    return self.send(
                        409 if sabotage == "wrong-status-code" else 412,
                        {"error": "precondition"},
                    )
                rec["task"] = (
                    {
                        "id": ident,
                        "title": value.get("title"),
                        "done": bool(value.get("done", False)),
                    }
                    if self.command == "PUT"
                    else {**rec["task"], **value, "id": ident}
                )
                if sabotage != "off-by-one":
                    rec["version"] += 1
                records[ident] = rec
            return self.send(200, rec["task"], tag(rec))
        return self.send(405, {"error": "method not allowed"})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = route

    def log_message(self, format: str, *args: Any) -> None:
        pass


ThreadingHTTPServer(
    ("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler
).serve_forever()
