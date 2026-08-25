import json, math, os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

jobs = {
    "1": {
        "id": "1",
        "name": "backup",
        "schedule": {"kind": "once", "at": "2030-01-01T00:00:00.000Z"},
    }
}
next_id = 2
sabotage = os.getenv("LAB_SABOTAGE", "")


def parse_instant(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def canonical(value):
    parsed = parse_instant(value)
    return (
        parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if parsed
        else None
    )


def normalize(value):
    if not isinstance(value, dict):
        return None
    if set(value) == {"kind", "at"} and value.get("kind") == "once":
        at = canonical(value.get("at"))
        return {"kind": "once", "at": at} if at else None
    allowed = set(value) == {"kind", "startAt", "everyMinutes"} or (
        sabotage == "missing-error-branch" and set(value) == {"kind", "startAt"}
    )
    if allowed and value.get("kind") == "interval":
        start = canonical(value.get("startAt"))
        every = value.get("everyMinutes", 1)
        if (
            start
            and isinstance(every, int)
            and not isinstance(every, bool)
            and every > 0
        ):
            return {"kind": "interval", "startAt": start, "everyMinutes": every}
    return None


def next_run(schedule, after_value):
    after = parse_instant(after_value)
    if not after:
        return False, None
    if schedule["kind"] == "once":
        return True, schedule["at"] if parse_instant(schedule["at"]) > after else None
    start = parse_instant(schedule["startAt"])
    if after < start:
        return True, schedule["startAt"]
    seconds = schedule["everyMinutes"] * 60
    periods = math.floor((after - start).total_seconds() / seconds) + (
        0 if sabotage == "off-by-one" else 1
    )
    result = start.timestamp() + periods * seconds
    return True, datetime.fromtimestamp(result, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


class Handler(BaseHTTPRequestHandler):
    def body(self):
        return json.loads(
            self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}"
        )

    def send(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def bad(self, message):
        return self.send(
            422 if sabotage == "wrong-status-code" else 400, {"error": message}
        )

    def route(self):
        global next_id
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
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
                    return self.bad("invalid job")
                job = {"id": str(next_id), "name": value["name"], "schedule": schedule}
                next_id += 1
                jobs[job["id"]] = job
                return self.send(201, job)
            if ident is None:
                return self.send(405, {"error": "method not allowed"})
            job = jobs.get(ident)
            if not job:
                return self.send(404, {"error": "not found"})
            if self.command == "GET" and is_next:
                valid, result = next_run(
                    job["schedule"], parse_qs(parsed.query).get("after", [None])[0]
                )
                return (
                    self.send(200, {"nextRun": result})
                    if valid
                    else self.bad("invalid after")
                )
            if self.command == "GET" and not is_next:
                return self.send(200, job)
            if self.command == "PATCH" and not is_next:
                value = self.body()
                if (
                    not isinstance(value, dict)
                    or not value
                    or not set(value) <= {"name", "schedule"}
                ):
                    return self.bad("invalid patch")
                name = value.get("name", job["name"])
                schedule = (
                    job["schedule"]
                    if "schedule" not in value
                    else normalize(value["schedule"])
                )
                if not isinstance(name, str) or not name or not schedule:
                    return self.bad("invalid patch")
                if sabotage == "unhandled-concurrent-update" and "schedule" in value:
                    schedule = {**job["schedule"], **schedule}
                changed = {"id": ident, "name": name, "schedule": schedule}
                jobs[ident] = changed
                return self.send(200, changed)
            return self.send(405, {"error": "method not allowed"})
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.bad("invalid json")

    do_GET = do_POST = do_PATCH = route

    def log_message(self, *_):
        pass


ThreadingHTTPServer(
    ("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler
).serve_forever()
