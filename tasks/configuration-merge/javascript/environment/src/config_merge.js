const fs = require("node:fs");

function validate(input) {
  const keys = ["defaults", "file", "env", "cli"];
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("invalid input");
  if (Object.keys(input).sort().join(",") !== keys.slice().sort().join(",")) throw new Error("invalid layers");
  for (const key of keys) {
    if (!input[key] || typeof input[key] !== "object" || Array.isArray(input[key])) throw new Error("invalid layer");
  }
}

function merge(input) {
  validate(input);
  return Object.assign({}, input.defaults, input.file, input.env, input.cli);
}

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  process.stdout.write(JSON.stringify(merge(input)) + "\n");
} catch (error) {
  process.stderr.write(String(error.message || error) + "\n");
  process.exitCode = 1;
}
