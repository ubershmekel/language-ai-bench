"use strict";

const { parseRate } = require("./money");

function edgeKey(source, target) {
  return source + " " + target;
}

function buildGraph(currencies, rates) {
  const edges = new Map();
  for (const rate of rates) {
    edges.set(edgeKey(rate.from, rate.to), parseRate(rate.rate));
  }
  return edges;
}

function factor(edges, source, target) {
  if (source === target) {
    return 1;
  }
  const direct = edges.get(edgeKey(source, target));
  if (direct === undefined) {
    throw new Error("no conversion rate");
  }
  return direct;
}

module.exports = { buildGraph, factor };
