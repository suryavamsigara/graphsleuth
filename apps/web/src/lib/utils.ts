export function cn(...args: Array<string | false | null | undefined>): string {
  return args.filter(Boolean).join(" ");
}

export function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatPct(v: number): string {
  // Accepts either 0-1 or 0-100 scale confidence values
  const pct = v <= 1 ? v * 100 : v;
  return `${pct.toFixed(1)}%`;
}
