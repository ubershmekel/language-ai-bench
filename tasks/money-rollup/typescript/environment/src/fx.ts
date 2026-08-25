import { parseRate } from "./money";

export type Graph = Map<string, number>;

function edgeKey(source: string, target: string): string {
  return source + " " + target;
}

export function buildGraph(
  currencies: Record<string, number>,
  rates: Array<Record<string, string>>
): Graph {
  const edges: Graph = new Map();
  for (const rate of rates) {
    edges.set(edgeKey(rate.from, rate.to), parseRate(rate.rate));
  }
  return edges;
}

export function factor(edges: Graph, source: string, target: string): number {
  if (source === target) {
    return 1;
  }
  const direct = edges.get(edgeKey(source, target));
  if (direct === undefined) {
    throw new Error("no conversion rate");
  }
  return direct;
}
