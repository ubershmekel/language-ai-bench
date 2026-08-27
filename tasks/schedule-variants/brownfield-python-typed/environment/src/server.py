import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlparse

Schedule = dict[str, Any]
Job = dict[str, Any]

jobs: dict[str, Job] = {
    "1": {
        "id": "1",
        "name": "backup",
        "schedule": {"kind": "once", "at": "2030-01-01T00:00:00.000Z"},
    }
}
next_id = 2


def instant(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return (
            parsed.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
    except ValueError:
        return None


def normalize(value: object) -> Schedule | None:
    if (
        not isinstance(value, dict)
        or set(value) != {"kind", "at"}
        or value.get("kind") != "once"
    ):
        return None
    at = instant(value.get("at"))
    return {"kind": "once", "at": at} if at else None


class Handler(BaseHTTPRequestHandler):
    def body(self) -> Any:
        return json.loads(
            self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}"
        )

    def send(self, status: int, value: object) -> None:
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def route(self) -> None:
        global next_id
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        if not parts or parts[0] != "jobs" or len(parts) > 3:
            return self.send(404, {"error": "not found"})
        ident = parts[1] if len(parts) >= 2 else None
        is_next = len(parts) == 3 and parts[2] == "next"
        try:
            if self.command == "POST" and ident is None:
                value = self.body()
                schedule = (
                    normalize(value.get("schedule"))
                    if isinstance(value, dict) and set(value) <= {"name", "schedule"}
                    else None
                )
                if (
                    not isinstance(value.get("name"), str)
                    or not value["name"]
                    or not schedule
                ):
                    return self.send(400, {"error": "invalid job"})
                job: Job = {
                    "id": str(next_id),
                    "name": value["name"],
                    "schedule": schedule,
                }
                next_id += 1
                jobs[job["id"]] = job
                return self.send(201, job)
            if ident is None:
                return self.send(405, {"error": "method not allowed"})
            existing = jobs.get(ident)
            if not existing:
                return self.send(404, {"error": "not found"})
            if self.command == "GET" and is_next:
                query = dict(parse_qsl(urlparse(self.path).query))
                after = instant(query.get("after"))
                if not after:
                    return self.send(400, {"error": "invalid after"})
                return self.send(
                    200,
                    {
                        "nextRun": (
                            existing["schedule"]["at"]
                            if existing["schedule"]["at"] > after
                            else None
                        )
                    },
                )
            if self.command == "GET" and not is_next:
                return self.send(200, existing)
            if self.command == "PATCH" and not is_next:
                value = self.body()
                if (
                    not isinstance(value, dict)
                    or not value
                    or not set(value) <= {"name", "schedule"}
                ):
                    return self.send(400, {"error": "invalid patch"})
                name = value.get("name", existing["name"])
                schedule = (
                    existing["schedule"]
                    if "schedule" not in value
                    else normalize(value["schedule"])
                )
                if not isinstance(name, str) or not name or not schedule:
                    return self.send(400, {"error": "invalid patch"})
                changed: Job = {"id": ident, "name": name, "schedule": schedule}
                jobs[ident] = changed
                return self.send(200, changed)
            return self.send(405, {"error": "method not allowed"})
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.send(400, {"error": "invalid json"})

    do_GET = do_POST = do_PATCH = route

    def log_message(self, format: str, *args: Any) -> None:
        pass


ThreadingHTTPServer(
    ("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler
).serve_forever()
