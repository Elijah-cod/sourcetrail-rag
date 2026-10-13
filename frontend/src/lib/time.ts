/** "9:42 AM" (or "21:42", by the visitor's locale), with the date when it isn't today. */
export function messageTime(value: string | number | Date): { text: string; iso: string } | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const today = new Date().toDateString() === date.toDateString();
  const text = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    ...(today ? {} : { day: "numeric", month: "short" }),
  }).format(date);
  return { text, iso: date.toISOString() };
}
