import { FileSpreadsheet, FileText, FileType, Globe, type LucideIcon } from "lucide-react";
import type { SourceType } from "@/lib/types";

// One hue per file type: categorical, so raw palette colours on purpose (see DESIGN.md).
const ICONS: Record<SourceType, { icon: LucideIcon; color: string }> = {
  pdf: { icon: FileType, color: "bg-rose-50 text-rose-600 border-rose-100" },
  docx: { icon: FileText, color: "bg-sky-50 text-sky-600 border-sky-100" },
  md: { icon: FileText, color: "bg-indigo-50 text-indigo-600 border-indigo-100" },
  txt: { icon: FileText, color: "bg-slate-50 text-slate-600 border-slate-200" },
  csv: { icon: FileSpreadsheet, color: "bg-emerald-50 text-emerald-600 border-emerald-100" },
  url: { icon: Globe, color: "bg-amber-50 text-amber-700 border-amber-100" },
};

export function FileTypeIcon({ type }: { type: SourceType }) {
  const { icon: Icon, color } = ICONS[type] ?? ICONS.txt;
  return (
    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${color}`}>
      <Icon className="h-4 w-4" aria-hidden />
    </div>
  );
}
