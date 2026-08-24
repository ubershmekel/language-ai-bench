const http = require("node:http");
const { URL } = require("node:url");

const tasks = new Map([["1", { id: "1", title: "calibrate", done: false }]]);
let nextId = 2;

function send(res, status, body) {
  const data = body === undefined ? "" : JSON.stringify(body);
  res.writeHead(status, { "content-type": "application/json", "content-length": Buffer.byteLength(data) });
  res.end(data);
}
function read(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", chunk => data += chunk);
    req.on("end", () => { try { resolve(data ? JSON.parse(data) : {}); } catch (e) { reject(e); } });
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const match = url.pathname.match(/^\/tasks(?:\/([^/]+))?$/);
  if (!match) return send(res, 404, { error: "not found" });
  const id = match[1];
  try {
    if (req.method === "GET" && !id) return send(res, 200, [...tasks.values()]);
    if (req.method === "POST" && !id) {
      const body = await read(req); const task = { id: String(nextId++), title: body.title, done: !!body.done };
      tasks.set(task.id, task); return send(res, 201, task);
    }
    if (!id || !tasks.has(id)) return send(res, 404, { error: "not found" });
    if (req.method === "GET") return send(res, 200, tasks.get(id));
    if (req.method === "PUT" || req.method === "PATCH") {
      const body = await read(req); const old = tasks.get(id);
      const task = req.method === "PUT" ? { id, title: body.title, done: !!body.done } : { ...old, ...body, id };
      tasks.set(id, task); return send(res, 200, task);
    }
    if (req.method === "DELETE") { tasks.delete(id); return send(res, 204); }
    return send(res, 405, { error: "method not allowed" });
  } catch { return send(res, 400, { error: "invalid json" }); }
});
server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () => console.log("ready"));

