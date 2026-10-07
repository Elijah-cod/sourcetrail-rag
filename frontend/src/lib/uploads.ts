// Upload rules, checked in the browser *before* sending, so problems show up instantly.
// Keep these in sync with the backend (backend/app/config.py: max_upload_mb).

export const MAX_UPLOAD_MB = 10;
export const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".md", ".markdown", ".txt", ".csv"];
export const ACCEPTED_FILES = ACCEPTED_EXTENSIONS.join(",");   // for <input accept="...">

/** Returns a reason the file can't be uploaded, or null if it looks fine. */
export function uploadProblem(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `${file.name}: unsupported type. Use PDF, DOCX, Markdown, TXT or CSV.`;
  }
  const mb = file.size / (1024 * 1024);
  if (mb > MAX_UPLOAD_MB) {
    return `${file.name} is ${mb.toFixed(1)} MB — the limit is ${MAX_UPLOAD_MB} MB per file.`;
  }
  if (file.size === 0) return `${file.name} is empty.`;
  return null;
}
