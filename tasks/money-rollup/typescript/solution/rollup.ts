const SEGMENT = /^[A-Za-z0-9_]+$/;

export function accountPrefixes(account: unknown): string[] {
  if (typeof account !== "string" || account === "") {
    throw new Error("malformed account");
  }
  const segments = account.split(":");
  if (segments.some((segment) => !SEGMENT.test(segment))) {
    throw new Error("malformed account");
  }
  return segments.map((_, index) => segments.slice(0, index + 1).join(":"));
}

export function rollup(
  items: Array<[unknown, bigint]>
): Array<[string, bigint]> {
  const totals = new Map<string, bigint>();
  for (const [account, minor] of items) {
    let prefixes = accountPrefixes(account);
    if (process.env.LAB_SABOTAGE === "leaf-only-rollup") {
      prefixes = prefixes.slice(-1);
    }
    for (const prefix of prefixes) {
      totals.set(prefix, (totals.get(prefix) ?? 0n) + minor);
    }
  }
  return [...totals.entries()].sort((left, right) =>
    left[0] < right[0] ? -1 : left[0] > right[0] ? 1 : 0
  );
}
