"use client";

import { Link2, Loader2, Search, Trash2, UploadCloud } from "lucide-react";
import { useMemo, useRef, useState, type DragEvent, type FormEvent } from "react";
import { plural } from "@/lib/format";
import type { DocumentInfo } from "@/lib/types";
import { FileTypeIcon } from "./FileTypeIcon";

export const ACCEPTED_FILES = ".pdf,.docx,.md,.markdown,.txt,.csv";

type Props = {
  documents: DocumentInfo[] | null;              // null = still loading
  onUpload: (files: File[]) => Promise<void>;
  onAddUrl: (url: string) => Promise<boolean>;   // true if it worked (so we can clear the box)
  onDelete: (doc: DocumentInfo) => Promise<void>;
  busy: boolean;                                 // an upload / URL import is running
};

export function DocumentsView({ documents, onUpload, onAddUrl, onDelete, busy }: Props) {
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // Filter by title or filename as you type. useMemo re-computes only when inputs change.
  const [mine, demo] = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const match = (d: DocumentInfo) =>
      !needle || d.title.toLowerCase().includes(needle) || (d.source_uri ?? "").toLowerCase().includes(needle);
    const visible = (documents ?? []).filter(match);
    return [visible.filter((d) => !d.is_demo), visible.filter((d) => d.is_demo)];
  }, [documents, query]);

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (!busy && event.dataTransfer.files.length) void onUpload(Array.from(event.dataTransfer.files));
  };

  const submitUrl = async (event: FormEvent) => {
    event.preventDefault();
    if (url.trim() && (await onAddUrl(url.trim()))) setUrl("");
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <div>
        <h1 className="font-heading text-xl font-bold text-slate-900">Documents</h1>
        <p className="mt-1 text-[13px] text-slate-600">
          Add files or web pages to your private workspace. Up to 10 documents, 10 MB each — deleted automatically after
          24 hours of inactivity.
        </p>
      </div>

      {/* Upload area: click to choose files, or drag them in */}
      <div className="grid gap-3 md:grid-cols-[1fr_1fr]">
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          disabled={busy}
          className={`flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-4 py-6 text-center transition-colors disabled:cursor-wait disabled:opacity-60 ${
            dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400 hover:bg-indigo-50/40"
          }`}
        >
          {busy ? (
            <Loader2 className="h-6 w-6 animate-spin text-indigo-600" aria-hidden />
          ) : (
            <UploadCloud className="h-6 w-6 text-indigo-600" aria-hidden />
          )}
          <span className="text-[13px] font-semibold text-slate-800">{busy ? "Processing…" : "Upload files"}</span>
          <span className="text-[11.5px] text-slate-500">PDF, DOCX, Markdown, TXT or CSV — click or drop here</span>
        </button>
        <input
          ref={fileInput}
          type="file"
          multiple
          accept={ACCEPTED_FILES}
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) void onUpload(Array.from(e.target.files));
            e.target.value = ""; // allow choosing the same file again later
          }}
        />

        <form onSubmit={submitUrl} className="flex flex-col justify-center gap-2 rounded-2xl border border-slate-200 bg-white p-4">
          <label htmlFor="url-input" className="flex items-center gap-2 text-[13px] font-semibold text-slate-800">
            <Link2 className="h-4 w-4 text-indigo-600" aria-hidden />
            Add a web page
          </label>
          <div className="flex gap-2">
            <input
              id="url-input"
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
              className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-[13px] focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            <button
              type="submit"
              disabled={busy || !url.trim()}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Add
            </button>
          </div>
          <span className="text-[11.5px] text-slate-500">We keep the main article text and drop menus and footers.</span>
        </form>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter documents…"
          aria-label="Filter documents"
          className="w-full rounded-full border border-slate-200 bg-white py-2 pl-9 pr-4 text-[13px] shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      {documents === null ? (
        <p className="flex items-center gap-2 text-[13px] text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Loading documents…
        </p>
      ) : (
        <>
          <DocumentList
            title="Your uploads"
            empty={query ? "No uploads match your filter." : "Nothing uploaded yet — your files will appear here."}
            documents={mine}
            onDelete={onDelete}
          />
          <DocumentList title="Demo collection" empty="No demo documents match your filter." documents={demo} />
        </>
      )}
    </div>
  );
}

function DocumentList({
  title,
  empty,
  documents,
  onDelete,
}: {
  title: string;
  empty: string;
  documents: DocumentInfo[];
  onDelete?: (doc: DocumentInfo) => Promise<void>;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 font-mono text-[10.5px] font-bold uppercase tracking-wider text-slate-400">
        {title} · {documents.length}
      </h2>
      {documents.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 px-4 py-5 text-center text-[12.5px] text-slate-500">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {documents.map((doc) => (
            <li key={doc.id} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
              <FileTypeIcon type={doc.source_type} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-semibold text-slate-900">{doc.title}</p>
                <p className="truncate text-[11.5px] text-slate-500">
                  {doc.source_uri ?? doc.source_type.toUpperCase()} · {plural(doc.chunk_count, "chunk")}
                  {doc.published_year ? ` · ${doc.published_year}` : ""}
                </p>
              </div>
              {onDelete && (
                <button
                  type="button"
                  onClick={() => void onDelete(doc)}
                  className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
                  aria-label={`Delete ${doc.title}`}
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
