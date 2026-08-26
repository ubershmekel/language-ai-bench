const http = require("node:http");
const { URL } = require("node:url");
const crypto = require("node:crypto");

const records = new Map([
  ["1", { task: { id: "1", title: "calibrate", done: false }, version: 1 }],
]);
let nextId = 2;
const sabotage = process.env.LAB_SABOTAGE || "";

function tag(record) {
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

function send(res, status, body, etag) {
  const data = body === undefined ? "" : JSON.stringify(body);
  const headers = {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(data),
  };
  if (etag) headers.etag = etag;
  res.writeHead(status, headers);
  res.end(data);
}

/** Read the request body as a JSON object; callers validate what they need. */
function read(req) {
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

/** Returns the status to reject with, or 0 when the precondition holds. */
function precondition(req, record) {
  if (!req.headers["if-match"]) return 428;
  if (req.headers["if-match"] !== tag(record))
    return sabotage === "missing-error-branch" ? 0 : 412;
  return 0;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const match = url.pathname.match(/^\/tasks(?:\/([^/]+))?$/);
  if (!match) return send(res, 404, { error: "not found" });
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
      const task = { id: String(nextId++), title: body.title, done: !!body.done };
      const record = { task, version: 1 };
      records.set(task.id, record);
      return send(res, 201, task, tag(record));
    }
    const record = id && records.get(id);
    if (!record) return send(res, 404, { error: "not found" });
    if (req.method === "GET") return send(res, 200, record.task, tag(record));
    if (["PUT", "PATCH", "DELETE"].includes(req.method)) {
      const status = precondition(req, record);
      if (status)
        return send(
          res,
          status === 412 && sabotage === "wrong-status-code" ? 409 : status,
          { error: "precondition" },
        );
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
        return send(res, sabotage === "wrong-status-code" ? 409 : 412, {
          error: "precondition",
        });
      record.task =
        req.method === "PUT"
          ? { id, title: body.title, done: !!body.done }
          : // PATCH copies the body over the stored task without checking it.
            { ...record.task, ...body, id };
      if (sabotage !== "off-by-one") record.version++;
      records.set(id, record);
      return send(res, 200, record.task, tag(record));
    }
    return send(res, 405, { error: "method not allowed" });
  } catch {
    return send(res, 400, { error: "invalid json" });
  }
});

server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () =>
  console.log("ready"),
);
