// Which sentences of a passage support a sentence of the answer?
// We compare words: the answer sentence next to the clicked [n] against every sentence of the
// cited passage, and mark the ones that share the most meaningful words (numbers count double,
// since "99.9 percent" or "30 days" is usually exactly what's being cited).

const STOP = new Set(
  ("the and for are was were that this with from have has had not but you your our its their them they " +
    "into than then there these those which what when where who whom how why can could should would will " +
    "may might also such each other more most some any all one two per via about over under between both " +
    "only very just like using used use does did done been being is it in on of to a an as at by or be if so no")
    .split(" "),
);

/** Meaningful words, roughly stemmed: "targets" -> "target", "availability" stays. */
export function terms(text: string): string[] {
  return (text.toLowerCase().match(/[a-z0-9]+(?:[.'][a-z0-9]+)*/g) ?? [])
    .filter((w) => /\d/.test(w) || (w.length >= 3 && !STOP.has(w)))
    .map((w) => (w.length > 4 ? w.replace(/(ing|ed|es|s)$/, "") : w));
}

/** Split text into sentences, keeping the separators so the text can be put back together exactly.
 *  Returns alternating [sentence, separator, sentence, ...]. */
export function splitSentences(text: string): string[] {
  return text.split(/((?<=[.!?])\s+(?=\S)|\n+)/);
}

/** The sentences (trimmed) that best support `claim`, at most three. Empty if nothing fits well. */
export function supportingSentences(claim: string, sentences: string[]): Set<string> {
  const wanted = new Set(terms(claim));
  if (wanted.size < 2) return new Set();

  const scored = sentences
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map((sentence) => {
      let points = 0;
      for (const t of new Set(terms(sentence))) if (wanted.has(t)) points += /\d/.test(t) ? 2 : 1;
      return { sentence, score: points / wanted.size };
    })
    .sort((a, b) => b.score - a.score);

  const best = scored[0]?.score ?? 0;
  if (best < 0.2) return new Set();
  return new Set(scored.filter((s) => s.score >= Math.max(0.2, best * 0.75)).slice(0, 3).map((s) => s.sentence));
}

/** The answer sentence a citation belongs to: the text just before the [n], back to the
 *  previous full stop. "Revenue fell [1]. Demand was low [2]." -> [2] belongs to "Demand was low". */
export function claimBefore(textBefore: string): string {
  const plain = textBefore.replace(/\[\d+\]/g, " ").replace(/[*`]/g, "").trim();
  const sentences = plain.split(/(?<=[.!?])\s+/).filter((s) => terms(s).length > 0);
  return sentences.at(-1) ?? plain;
}
