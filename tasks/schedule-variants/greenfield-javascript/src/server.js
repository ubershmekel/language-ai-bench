const http = require("node:http");
const seed = {
  id: "1",
  name: "backup",
  schedule: { kind: "once", at: "2030-01-01T00:00:00.000Z" },
};
const server = http.createServer((req, res) => {
  const found = req.method === "GET" && req.url === "/jobs/1";
  const body = JSON.stringify(found ? seed : { error: "not implemented" });
  res.writeHead(found ? 200 : 501, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(body),
  });
  res.end(body);
});
server.listen(Number(process.env.PORT || 8080), "0.0.0.0", () =>
  console.log("ready"),
);
