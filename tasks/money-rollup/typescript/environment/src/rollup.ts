export type Item = readonly [account: string, minor: bigint];

export function rollup(items: readonly Item[]): Item[] {
  const totals = new Map<string, bigint>();
  for (const [account, minor] of items) {
    totals.set(account, (totals.get(account) ?? 0n) + minor);
  }
  return [...totals.entries()].sort(([left], [right]) =>
    left < right ? -1 : left > right ? 1 : 0,
  );
}
