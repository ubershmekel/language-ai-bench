import http, { type IncomingMessage, type ServerResponse } from "node:http";
import { URL } from "node:url";

interface Task {
  id: string;
  title: string;
  done: boolean;
}

const tasks = new Map<string, Task>([
  ["1", { id: "1", title: "calibrate", done: false }],
]);
let nextId = 2;

function send(res: ServerResponse, status: number, body?: unknown): void {
  const data = body === undefined ? "" : JSON.stringify(body);
  res.writeHead(status, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(data),
  });
  res.end(data);
}

/**
 * Read the request body as a JSON object. The current implementation trusts
 * the shape of what it parses and validates nothing below the top level.
 */
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
  if (!match) return send(res, 404, { error: "not found" });
  const id = match[1];
  try {
    if (req.method === "GET" && !id) return send(res, 200, [...tasks.values()]);
    if (req.method === "POST" && !id) {
      const body = await read(req);
      const task: Task = {
        id: String(nextId++),
        title: String(body.title ?? ""),
        done: Boolean(body.done),
      };
      tasks.set(task.id, task);
      return send(res, 201, task);
    }
    if (!id) return send(res, 404, { error: "not found" });
    const existing = tasks.get(id);
    if (!existing) return send(res, 404, { error: "not found" });
    if (req.method === "GET") return send(res, 200, existing);
    if (req.method === "PUT" || req.method === "PATCH") {
      const body = await read(req);
      const task: Task =
        req.method === "PUT"
          ? { id, title: String(body.title ?? ""), done: Boolean(body.done) }
          : // PATCH copies the body over the stored task without checking it.
            ({ ...existing, ...body, id } as Task);
      tasks.set(id, task);
      return send(res, 200, task);
    }
    if (req.method === "DELETE") {
      tasks.delete(id);
      return send(res, 204);
    }
    return send(res, 405, { error: "method not allowed" });
  } catch {
    return send(res, 400, { error: "invalid json" });
  }
});

server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () =>
  console.log("ready"),
);
