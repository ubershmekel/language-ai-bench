import http, { IncomingMessage, ServerResponse } from "node:http";
import { URL } from "node:url";
import * as store from "./store";
import { normalizeSchedule, nextRun } from "./schedule";
function send(res: ServerResponse, status: number, body: unknown): void { const data = JSON.stringify(body); res.writeHead(status, { "content-type": "application/json", "content-length": Buffer.byteLength(data) }); res.end(data); }
function read(req: IncomingMessage): Promise<unknown> { return new Promise((resolve, reject) => { let data = ""; req.on("data", chunk => data += chunk); req.on("end", () => { try { resolve(data ? JSON.parse(data) : {}); } catch (error) { reject(error); } }); }); }
function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === "object" && !Array.isArray(value); }
function allowed(value: unknown, keys: string[]): value is Record<string, unknown> { return record(value) && Object.keys(value).every(key => keys.includes(key)); }
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", "http://localhost"), match = url.pathname.match(/^\/jobs(?:\/([^/]+)(\/next)?)?$/);
  if (!match) return send(res, 404, { error: "not found" }); const id = match[1], next = match[2];
  try {
    if (req.method === "POST" && !id) { const body = await read(req); if (!allowed(body, ["name", "schedule"])) return send(res, 400, { error: "invalid job" }); const schedule = normalizeSchedule(body.schedule); if (typeof body.name !== "string" || !body.name || !schedule) return send(res, 400, { error: "invalid job" }); return send(res, 201, store.create(body.name, schedule)); }
    if (!id) return send(res, 405, { error: "method not allowed" }); const job = store.get(id); if (!job) return send(res, 404, { error: "not found" });
    if (req.method === "GET" && next) { const result = nextRun(job.schedule, url.searchParams.get("after")); return result === undefined ? send(res, 400, { error: "invalid after" }) : send(res, 200, { nextRun: result }); }
    if (req.method === "GET" && !next) return send(res, 200, job);
    if (req.method === "PATCH" && !next) { const body = await read(req); if (!allowed(body, ["name", "schedule"]) || Object.keys(body).length === 0) return send(res, 400, { error: "invalid patch" }); const name = body.name === undefined ? job.name : body.name; const schedule = body.schedule === undefined ? job.schedule : normalizeSchedule(body.schedule); if (typeof name !== "string" || !name || !schedule) return send(res, 400, { error: "invalid patch" }); return send(res, 200, store.replace({ id, name, schedule })); }
    return send(res, 405, { error: "method not allowed" });
  } catch { return send(res, 400, { error: "invalid json" }); }
});
server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () => console.log("ready"));
