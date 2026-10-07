// Finding web links inside a chat message, so "Summarise https://example.com/post"
// can add the page to the workspace first and then answer the rest of the message.

// http(s):// followed by anything up to whitespace. Trailing punctuation is trimmed below,
// so "see https://x.com/a." doesn't include the full stop.
const LINK = /https?:\/\/[^\s<>"']+/gi;
const TRAILING = /[).,;:!?\]'"»”]+$/;

export type SplitMessage = {
  urls: string[];      // each link found, once, in order
  question: string;    // the message with the links taken out ("" if it was only links)
};

export function splitLinks(text: string): SplitMessage {
  const urls: string[] = [];
  const question = text
    .replace(LINK, (match) => {
      const url = match.replace(TRAILING, "");
      if (!urls.includes(url)) urls.push(url);
      return match.slice(url.length);              // keep any punctuation we trimmed off
    })
    .replace(/\s{2,}/g, " ")
    .trim()
    .replace(/^[\s.,;:!?-]+$/, "");                // nothing left but punctuation -> no question
  return { urls, question };
}

/** "https://en.wikipedia.org/wiki/HTTP" -> "en.wikipedia.org/wiki/HTTP", for a short label. */
export function shortUrl(url: string): string {
  return url.replace(/^https?:\/\//i, "").replace(/\/$/, "");
}
