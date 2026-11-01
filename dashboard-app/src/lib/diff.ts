export type DiffLine = { t: 'same' | 'add' | 'del'; s: string };

/** Paragraph-level LCS diff (old → new). */
export function diffLines(a: string[], b: string[]): DiffLine[] {
  const n = a.length, m = b.length;
  if (n * m > 4_000_000) return [...a.map(s => ({ t: 'del' as const, s })), ...b.map(s => ({ t: 'add' as const, s }))];
  const dp: Uint32Array[] = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: DiffLine[] = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { out.push({ t: 'same', s: a[i] }); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ t: 'del', s: a[i++] });
    else out.push({ t: 'add', s: b[j++] });
  }
  while (i < n) out.push({ t: 'del', s: a[i++] });
  while (j < m) out.push({ t: 'add', s: b[j++] });
  return out;
}
