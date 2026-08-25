import * as fs from "node:fs";

type JsonObject = Record<string, unknown>;
type Input = {
  defaults: JsonObject;
  file: JsonObject;
  env: JsonObject;
  cli: JsonObject;
};

function isObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validate(value: unknown): asserts value is Input {
  const keys = ["defaults", "file", "env", "cli"];
  if (!isObject(value)) throw new Error("invalid input");
  if (Object.keys(value).sort().join(",") !== keys.slice().sort().join(","))
    throw new Error("invalid layers");
  for (const key of keys)
    if (!isObject(value[key])) throw new Error("invalid layer");
}

function merge(value: unknown): JsonObject {
  validate(value);
  return Object.assign({}, value.defaults, value.file, value.env, value.cli);
}

try {
  const input: unknown = JSON.parse(fs.readFileSync(0, "utf8"));
  process.stdout.write(JSON.stringify(merge(input)) + "\n");
} catch (error) {
  process.stderr.write(
    String(error instanceof Error ? error.message : error) + "\n",
  );
  process.exitCode = 1;
}
