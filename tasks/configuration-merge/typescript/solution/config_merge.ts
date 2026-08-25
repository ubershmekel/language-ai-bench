import * as fs from "node:fs";

type JsonValue = null | boolean | number | string | JsonValue[] | JsonObject;
type JsonObject = { [key: string]: JsonValue };
type Input = { defaults: JsonObject; file: JsonObject; env: JsonObject; cli: JsonObject };

function isObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validate(value: unknown): asserts value is Input {
  const keys = ["defaults", "file", "env", "cli"];
  if (!isObject(value)) throw new Error("invalid input");
  if (Object.keys(value).sort().join(",") !== keys.slice().sort().join(",")) throw new Error("invalid layers");
  for (const key of keys) if (!isObject(value[key])) throw new Error("invalid layer");
}

function clone(value: JsonValue): JsonValue {
  if (Array.isArray(value)) return value.map(clone);
  if (isObject(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, clone(item)]));
  return value;
}

function mergeInto(target: JsonObject, layer: JsonObject, sabotage: string): JsonObject {
  for (const [key, value] of Object.entries(layer)) {
    if (value === null && sabotage !== "ignore-delete") {
      delete target[key];
    } else if (isObject(value) && sabotage !== "shallow-merge") {
      const base = target[key];
      target[key] = mergeInto(isObject(base) ? clone(base) as JsonObject : {}, value, sabotage);
    } else if (Array.isArray(value) && sabotage === "merge-arrays" && Array.isArray(target[key])) {
      target[key] = [...target[key] as JsonValue[], ...clone(value) as JsonValue[]];
    } else {
      target[key] = clone(value);
    }
  }
  return target;
}

function merge(value: unknown): JsonObject {
  validate(value);
  const sabotage = process.env.LAB_SABOTAGE || "";
  const layers = [value.defaults, value.file, value.env, value.cli];
  if (sabotage === "reverse-precedence") layers.reverse();
  return layers.reduce((result, layer) => mergeInto(result, layer, sabotage), {});
}

try {
  const input: unknown = JSON.parse(fs.readFileSync(0, "utf8"));
  process.stdout.write(JSON.stringify(merge(input)) + "\n");
} catch (error) {
  process.stderr.write(String(error instanceof Error ? error.message : error) + "\n");
  process.exitCode = 1;
}
