import { UploadCloud } from "lucide-react";
import { MAX_UPLOAD_MB } from "@/lib/uploads";

/** Full-screen hint shown while a file is dragged over the window. */
export function DropOverlay({ visible }: { visible: boolean }) {
  return (
    <div
      aria-hidden
      // pointer-events-none: the drop still reaches the window listener underneath
      className={`pointer-events-none fixed inset-0 z-[70] flex items-center justify-center bg-brand-950/20 p-6 backdrop-blur-[2px] transition-opacity duration-150 ${
        visible ? "opacity-100" : "opacity-0"
      }`}
    >
      <div className="flex w-full max-w-md flex-col items-center gap-2 rounded-3xl border-2 border-dashed border-brand-500 bg-raised/95 px-6 py-10 text-center shadow-2xl">
        <UploadCloud className="h-10 w-10 text-brand-600" />
        <p className="font-heading text-lg font-bold text-ink-900">Drop to add to your workspace</p>
        <p className="text-[12.5px] text-ink-500">PDF, DOCX, Markdown, TXT or CSV · up to {MAX_UPLOAD_MB} MB each</p>
      </div>
    </div>
  );
}
