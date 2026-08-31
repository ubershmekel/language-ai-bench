const TOP_LEVEL = ["config", "programs"];

export interface Token {
  value: number | string;
  at: number;
}

export interface Source {
  id: string;
  source: string;
}

export interface Document {
  maxDepth: number;
  programs: Source[];
}

/** Only the top-level key set is checked so far. */
export function parseDocument(value: Record<string, unknown>): Document {
  if (Object.keys(value).sort().join(",") !== TOP_LEVEL.join(",")) {
    throw new Error("malformed document");
  }
  const config = value["config"] as { maxDepth: number };
  return { maxDepth: config.maxDepth, programs: value["programs"] as Source[] };
}

/** Decimal literals and the two operators that are understood so far. */
export function tokenize(source: string): Token[] {
  const tokens: Token[] = [];
  let index = 0;
  while (index < source.length) {
    const character = source[index] as string;
    if (character === " ") {
      index += 1;
      continue;
    }
    if (character === "+" || character === "*") {
      tokens.push({ value: character, at: index });
      index += 1;
      continue;
    }
    const start = index;
    while (index < source.length && (source[index] as string) >= "0" && (source[index] as string) <= "9") {
      index += 1;
    }
    if (index === start) {
      throw new Error(`unexpected character at ${index}`);
    }
    tokens.push({ value: Number(source.slice(start, index)), at: start });
  }
  return tokens;
}
