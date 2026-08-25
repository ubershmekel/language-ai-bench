const fs = require("node:fs");

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validate(input) {
  const keys = ["defaults", "file", "env", "cli"];
  if (!isObject(input)) throw new Error("invalid input");
  if (Object.keys(input).sort().join(",") !== keys.slice().sort().join(","))
    throw new Error("invalid layers");
  for (const key of keys)
    if (!isObject(input[key])) throw new Error("invalid layer");
}

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (isObject(value))
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, clone(item)]),
    );
  return value;
}

function mergeInto(target, layer, sabotage) {
  for (const [key, value] of Object.entries(layer)) {
    if (value === null && sabotage !== "ignore-delete") {
      delete target[key];
    } else if (isObject(value) && sabotage !== "shallow-merge") {
      const base = isObject(target[key]) ? target[key] : {};
      target[key] = mergeInto(clone(base), value, sabotage);
    } else if (
      Array.isArray(value) &&
      sabotage === "merge-arrays" &&
      Array.isArray(target[key])
    ) {
      target[key] = [...target[key], ...clone(value)];
    } else {
      target[key] = clone(value);
    }
  }
  return target;
}

function merge(input) {
  validate(input);
  const sabotage = process.env.LAB_SABOTAGE || "";
  const layers = [input.defaults, input.file, input.env, input.cli];
  if (sabotage === "reverse-precedence") layers.reverse();
  return layers.reduce(
    (result, layer) => mergeInto(result, layer, sabotage),
    {},
  );
}

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  process.stdout.write(JSON.stringify(merge(input)) + "\n");
} catch (error) {
  process.stderr.write(String(error.message || error) + "\n");
  process.exitCode = 1;
}
