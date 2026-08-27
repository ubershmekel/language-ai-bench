import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

Task = dict[str, Any]

tasks: dict[str, Task] = {"1": {"id": "1", "title": "calibrate", "done": False}}
next_id = 2


class Handler(BaseHTTPRequestHandler):
    def body(self) -> dict[str, Any]:
        size = int(self.headers.get("content-length", 0))
        parsed: dict[str, Any] = json.loads(self.rfile.read(size) or b"{}")
        return parsed

    def send(self, status: int, value: object = None) -> None:
        data = b"" if value is None else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def route(self) -> None:
        global next_id
        parts = self.path.split("?", 1)[0].strip("/").split("/")
        if not parts or parts[0] != "tasks" or len(parts) > 2:
            return self.send(404, {"error": "not found"})
        ident = parts[1] if len(parts) == 2 else None
        if self.command == "GET" and ident is None:
            return self.send(200, list(tasks.values()))
        if self.command == "POST" and ident is None:
            value = self.body()
            task: Task = {
                "id": str(next_id),
                "title": value.get("title"),
                "done": bool(value.get("done", False)),
            }
            next_id += 1
            tasks[task["id"]] = task
            return self.send(201, task)
        if ident not in tasks:
            return self.send(404, {"error": "not found"})
        if self.command == "GET":
            return self.send(200, tasks[ident])
        if self.command in ("PUT", "PATCH"):
            value = self.body()
            old = tasks[ident]
            changed: Task = (
                {
                    "id": ident,
                    "title": value.get("title"),
                    "done": bool(value.get("done", False)),
                }
                if self.command == "PUT"
                else {**old, **value, "id": ident}
            )
            tasks[ident] = changed
            return self.send(200, changed)
        if self.command == "DELETE":
            del tasks[ident]
            return self.send(204)
        return self.send(405, {"error": "method not allowed"})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = route

    def log_message(self, format: str, *args: Any) -> None:
        pass


ThreadingHTTPServer(
    ("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler
).serve_forever()
