import hashlib, json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

records = {
    "1": {"task": {"id": "1", "title": "calibrate", "done": False}, "version": 1}
}
next_id = 2
lock = threading.Lock()
sabotage = os.getenv("LAB_SABOTAGE", "")


def tag(rec):
    return (
        '"v' + str(rec["version"]) + '"'
        if sabotage == "off-by-one"
        else '"'
        + hashlib.sha256(
            (
                json.dumps(rec["task"], sort_keys=True, separators=(",", ":"))
                + ":"
                + str(rec["version"])
            ).encode()
        ).hexdigest()[:16]
        + '"'
    )


class Handler(BaseHTTPRequestHandler):
    def body(self):
        return json.loads(
            self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}"
        )

    def send(self, status, value=None, etag=None):
        data = b"" if value is None else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        etag and self.send_header("etag", etag)
        self.end_headers()
        self.wfile.write(data)

    def route(self):
        global next_id
        parts = self.path.split("?", 1)[0].strip("/").split("/")
        ident = parts[1] if len(parts) == 2 and parts[0] == "tasks" else None
        if parts[0] != "tasks" or len(parts) > 2:
            return self.send(404, {"error": "not found"})
        if self.command == "GET" and ident is None:
            return self.send(200, [x["task"] for x in records.values()])
        if self.command == "POST" and ident is None:
            value = self.body()
            task = {
                "id": str(next_id),
                "title": value.get("title"),
                "done": bool(value.get("done", False)),
            }
            next_id += 1
            rec = {"task": task, "version": 1}
            records[task["id"]] = rec
            return self.send(201, task, tag(rec))
        rec = records.get(ident)
        if rec is None:
            return self.send(404, {"error": "not found"})
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

    def log_message(self, *_):
        pass


ThreadingHTTPServer(
    ("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler
).serve_forever()
