import http from "node:http";

// Greenfield scaffold: replace this placeholder with the service in instruction.md.
const seed = { id: "1", title: "calibrate", done: false };
const server = http.createServer((req, res) => {
  const found = req.method === "GET" && req.url === "/tasks/1";
  const body = JSON.stringify(found ? seed : { error: "not implemented" });
  res.writeHead(found ? 200 : 501, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(body),
  });
  res.end(body);
});
server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () => console.log("ready"));
