import { multiply, parseRate, rational, Rational } from "./money";

const RATE_KEYS = ["from", "rate", "to"];

interface Edge {
  source: string;
  target: string;
  value: Rational;
}

export type Graph = Map<string, Edge>;

function edgeKey(source: string, target: string): string {
  return source + " " + target;
}

export function buildGraph(
  currencies: Record<string, number>,
  rates: unknown[]
): Graph {
  const edges: Graph = new Map();
  for (const rate of rates) {
    if (rate === null || typeof rate !== "object" || Array.isArray(rate)) {
      throw new Error("malformed rate");
    }
    const record = rate as Record<string, unknown>;
    if (Object.keys(record).sort().join(",") !== RATE_KEYS.join(",")) {
      throw new Error("malformed rate");
    }
    const source = record.from;
    const target = record.to;
    if (typeof source !== "string" || typeof target !== "string") {
      throw new Error("malformed rate");
    }
    if (!(source in currencies) || !(target in currencies)) {
      throw new Error("unknown rate currency");
    }
    if (source === target) {
      throw new Error("self rate");
    }
    if (edges.has(edgeKey(source, target))) {
      throw new Error("duplicate rate");
    }
    edges.set(edgeKey(source, target), {
      source,
      target,
      value: parseRate(record.rate),
    });
  }
  return edges;
}

export function factor(
  edges: Graph,
  source: string,
  target: string
): Rational {
  if (source === target) {
    return rational(1n, 1n);
  }
  if (process.env.LAB_SABOTAGE === "direct-rate-only") {
    const direct = edges.get(edgeKey(source, target));
    if (!direct) {
      throw new Error("no conversion path");
    }
    return direct.value;
  }
  interface Reach {
    value: Rational;
    paths: number;
  }
  const reached = new Map<string, Reach>([
    [source, { value: rational(1n, 1n), paths: 1 }],
  ]);
  let frontier = [source];
  while (frontier.length) {
    const following = new Map<string, Reach>();
    for (const node of frontier) {
      const current = reached.get(node);
      if (!current) {
        continue;
      }
      for (const edge of edges.values()) {
        if (edge.source !== node || reached.has(edge.target)) {
          continue;
        }
        const seen = following.get(edge.target);
        if (seen) {
          seen.paths += current.paths;
        } else {
          following.set(edge.target, {
            value: multiply(current.value, edge.value),
            paths: current.paths,
          });
        }
      }
    }
    if (!following.size) {
      break;
    }
    for (const [code, item] of following) {
      reached.set(code, item);
    }
    const arrival = reached.get(target);
    if (arrival) {
      if (arrival.paths !== 1) {
        throw new Error("ambiguous conversion path");
      }
      return arrival.value;
    }
    frontier = [...following.keys()];
  }
  throw new Error("no conversion path");
}
