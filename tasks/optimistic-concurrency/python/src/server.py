import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tasks = {"1": {"id": "1", "title": "calibrate", "done": False}}
next_id = 2


class Handler(BaseHTTPRequestHandler):
    def body(self):
        size = int(self.headers.get("content-length", 0))
        return json.loads(self.rfile.read(size) or b"{}")

    def send(self, status, value=None):
        data = b"" if value is None else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def route(self):
        global next_id
        parts = self.path.split("?", 1)[0].strip("/").split("/")
        if not parts or parts[0] != "tasks" or len(parts) > 2:
            return self.send(404, {"error": "not found"})
        ident = parts[1] if len(parts) == 2 else None
        if self.command == "GET" and ident is None:
            return self.send(200, list(tasks.values()))
        if self.command == "POST" and ident is None:
            value = self.body()
            task = {
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
            task = (
                {
                    "id": ident,
                    "title": value.get("title"),
                    "done": bool(value.get("done", False)),
                }
                if self.command == "PUT"
                else {**old, **value, "id": ident}
            )
            tasks[ident] = task
            return self.send(200, task)
        if self.command == "DELETE":
            del tasks[ident]
            return self.send(204)
        return self.send(405, {"error": "method not allowed"})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = route

    def log_message(self, *_):
        pass


ThreadingHTTPServer(
    ("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler
).serve_forever()
