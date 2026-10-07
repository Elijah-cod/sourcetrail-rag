"use client";

import { ArrowUp, Loader2, Paperclip } from "lucide-react";
import { useRef, useState, type KeyboardEvent } from "react";
import type { UploadItem } from "@/hooks/useDocuments";
import { ACCEPTED_FILES } from "@/lib/uploads";
import { UploadChips } from "./UploadStatus";

type Props = {
  onSubmit: (question: string) => void;
  onAttach: (files: File[]) => void;
  uploading: boolean;
  uploads: UploadItem[];
  onDismissUpload: (id: number) => void;
  onOpenDocuments: () => void;
  disabled?: boolean;
};

/** The prompt box at the bottom of the chat. Enter sends, Shift+Enter adds a new line. */
export function Composer({ onSubmit, onAttach, uploading, uploads, onDismissUpload, onOpenDocuments, disabled }: Props) {
  const [text, setText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const send = () => {
    const question = text.trim();
    if (!question || disabled) return;
    onSubmit(question);
    setText("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send();
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl p-3 sm:p-4 md:px-8 lg:px-12">
      <UploadChips uploads={uploads} onDismiss={onDismissUpload} onOpen={onOpenDocuments} />
      <div className="relative rounded-2xl border border-slate-200/90 bg-white p-3 shadow-lg shadow-indigo-950/5 transition-all focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100">
        <label htmlFor="prompt-input" className="sr-only">
          Your question
        </label>
        <textarea
          id="prompt-input"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          maxLength={1000}
          placeholder="Ask a question about the demo docs or your uploads…"
          className="w-full resize-none bg-transparent px-2 py-1 text-[14px] leading-relaxed text-slate-800 placeholder:text-slate-400 focus:outline-none"
        />
        <div className="mt-1 flex items-center justify-between border-t border-slate-100 px-1 pt-2">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:cursor-wait disabled:opacity-60"
              title="Upload a document to your workspace"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Paperclip className="h-4 w-4" aria-hidden />}
              {uploading ? "Uploading…" : "Attach"}
            </button>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept={ACCEPTED_FILES}
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) onAttach(Array.from(e.target.files));
                e.target.value = "";
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden font-mono text-[11px] text-slate-400 md:inline">Enter to send</span>
            <button
              type="button"
              onClick={send}
              disabled={disabled || !text.trim()}
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm shadow-indigo-600/30 transition-all hover:bg-indigo-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send question"
            >
              <ArrowUp className="h-[18px] w-[18px]" />
            </button>
          </div>
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-slate-500">
        Answers cite your documents. Always check important facts against the sources.
      </p>
    </div>
  );
}
