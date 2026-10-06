/** plural(1, "chunk") -> "1 chunk", plural(3, "chunk") -> "3 chunks" */
export function plural(count: number, word: string): string {
  return `${count.toLocaleString()} ${word}${count === 1 ? "" : "s"}`;
}
