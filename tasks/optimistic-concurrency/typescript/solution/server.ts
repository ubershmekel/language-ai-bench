import http, { type IncomingMessage, type ServerResponse } from "node:http";
import { URL } from "node:url";
import crypto from "node:crypto";

interface Task {
  id: string;
  title: string;
  done: boolean;
}

interface StoredTask {
  task: Task;
  version: number;
}

const records = new Map<string, StoredTask>([
  ["1", { task: { id: "1", title: "calibrate", done: false }, version: 1 }],
]);
let nextId = 2;
const sabotage = process.env.LAB_SABOTAGE ?? "";

function tag(record: StoredTask): string {
  if (sabotage === "off-by-one") {
    return `"v${record.version}"`;
  }
  const digest = crypto
    .createHash("sha256")
    .update(JSON.stringify(record.task) + ":" + record.version)
    .digest("hex")
    .slice(0, 16);
  return `"${digest}"`;
}

function send(
  res: ServerResponse,
  status: number,
  body?: unknown,
  etag?: string,
): void {
  const data = body === undefined ? "" : JSON.stringify(body);
  const headers: Record<string, string | number> = {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(data),
  };
  if (etag) headers.etag = etag;
  res.writeHead(status, headers);
  res.end(data);
}

/** Read the request body as a JSON object; callers validate what they need. */
function read(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (error) {
        reject(error);
      }
    });
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", "http://localhost");
  const match = url.pathname.match(/^\/tasks(?:\/([^/]+))?$/);
  if (!match) return send(res, 404);
  const id = match[1];
  try {
    if (req.method === "GET" && !id) {
      return send(
        res,
        200,
        [...records.values()].map((entry) => entry.task),
      );
    }
    if (req.method === "POST" && !id) {
      const body = await read(req);
      const task: Task = {
        id: String(nextId++),
        title: String(body.title ?? ""),
        done: Boolean(body.done),
      };
      const record: StoredTask = { task, version: 1 };
      records.set(task.id, record);
      return send(res, 201, task, tag(record));
    }
    if (!id) return send(res, 404);
    const record = records.get(id);
    if (!record) return send(res, 404);
    if (req.method === "GET") return send(res, 200, record.task, tag(record));
    if (["PUT", "PATCH", "DELETE"].includes(req.method ?? "")) {
      const ifMatch = req.headers["if-match"];
      if (!ifMatch) return send(res, 428);
      if (ifMatch !== tag(record) && sabotage !== "missing-error-branch")
        return send(res, sabotage === "wrong-status-code" ? 409 : 412);
    }
    if (req.method === "DELETE") {
      records.delete(id);
      return send(res, 204);
    }
    if (req.method === "PUT" || req.method === "PATCH") {
      const before = tag(record);
      const body = await read(req);
      if (sabotage === "unhandled-concurrent-update")
        await new Promise((resume) => setTimeout(resume, 80));
      const current = records.get(id);
      if (
        sabotage !== "unhandled-concurrent-update" &&
        sabotage !== "missing-error-branch" &&
        (!current || tag(current) !== before)
      )
        return send(res, sabotage === "wrong-status-code" ? 409 : 412);
      record.task =
        req.method === "PUT"
          ? { id, title: String(body.title ?? ""), done: Boolean(body.done) }
          : // PATCH copies the body over the stored task without checking it.
            ({ ...record.task, ...body, id } as Task);
      if (sabotage !== "off-by-one") record.version++;
      records.set(id, record);
      return send(res, 200, record.task, tag(record));
    }
    return send(res, 405);
  } catch {
    return send(res, 400);
  }
});

server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () =>
  console.log("ready"),
);
