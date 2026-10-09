"use client";

import { ArrowUp, Link2, Loader2, Paperclip } from "lucide-react";
import { useRef, useState, type ClipboardEvent, type KeyboardEvent } from "react";
import type { Settings } from "@/hooks/useChat";
import type { UploadItem } from "@/hooks/useDocuments";
import { splitLinks } from "@/lib/links";
import { ACCEPTED_FILES } from "@/lib/uploads";
import { SettingsPopover } from "./SettingsPopover";
import { UploadChips } from "./UploadStatus";

type Props = {
  onSubmit: (message: string) => Promise<string | null>;   // text to put back in the box, if any
  onAttach: (files: File[]) => void;
  uploading: boolean;
  uploads: UploadItem[];
  onDismissUpload: (id: number) => void;
  onOpenDocuments: () => void;
  settings: Settings;
  onChangeSettings: (settings: Settings) => void;
  disabled?: boolean;
};

/** The prompt box at the bottom of the chat. Enter sends, Shift+Enter adds a new line.
 *  It takes everything the workspace can: questions, web links (typed or pasted) and files
 *  (Attach, paste from the clipboard, or drop anywhere on the page). */
export function Composer(props: Props) {
  const { onSubmit, onAttach, uploading, uploads, onDismissUpload, onOpenDocuments, disabled } = props;
  const [text, setText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const send = async () => {
    const message = text.trim();
    if (!message || disabled) return;
    setText("");
    const putBack = await onSubmit(message);    // e.g. a link that couldn't be added, to fix
    if (putBack) setText(putBack);
  };

  // Files copied to the clipboard (e.g. Copy in Finder, then Cmd+V here) become uploads.
  const onPaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(event.clipboardData.files);
    if (files.length === 0) return;      // ordinary text: let the browser paste it
    event.preventDefault();
    onAttach(files);
  };

  // Live hint under the box when the message contains links.
  const { urls, question } = splitLinks(text);
  const hint =
    urls.length === 0
      ? null
      : `${urls.length === 1 ? "This page" : `These ${urls.length} pages`} will be added to your workspace${
          question ? ", then your question is answered" : ""
        }.`;

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void send();
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl p-3 sm:p-4 md:px-8 lg:px-12">
      <UploadChips uploads={uploads} onDismiss={onDismissUpload} onOpen={onOpenDocuments} />
      <div className="relative rounded-2xl border border-ink-200/90 bg-raised p-3 shadow-lg shadow-brand-950/5 transition-all focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100">
        <label htmlFor="prompt-input" className="sr-only">
          Your question
        </label>
        <textarea
          id="prompt-input"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          maxLength={1000}
          placeholder="Ask a question, paste a link, or attach a file…"
          className="w-full resize-none bg-transparent px-2 py-1 text-[14px] leading-relaxed text-ink-800 placeholder:text-ink-500 focus:outline-none"
        />
        {hint && (
          <p className="flex items-center gap-1.5 px-2 pb-1 text-[13px] text-brand-700">
            <Link2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
            {hint}
          </p>
        )}
        <div className="mt-1 flex items-center justify-between border-t border-ink-100 px-1 pt-2">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className="flex h-10 items-center gap-1 rounded-lg px-2.5 text-xs font-medium text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900"
              title="Add a PDF, DOCX, Markdown, TXT or CSV file (or paste a link in the box)"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Paperclip className="h-4 w-4" aria-hidden />}
              Attach
            </button>
            <SettingsPopover settings={props.settings} onChange={props.onChangeSettings} />
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
            <span className="hidden font-mono text-[12px] text-ink-500 md:inline">Enter to send</span>
            <button
              type="button"
              onClick={() => void send()}
              disabled={disabled || !text.trim()}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm shadow-brand-600/30 transition-all hover:bg-brand-700 active:scale-95 motion-reduce:active:scale-100 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send"
            >
              <ArrowUp className="h-[18px] w-[18px]" />
            </button>
          </div>
        </div>
      </div>
      <p className="mt-2 text-center text-[12px] text-ink-500">
        Answers cite your documents. Always check important facts against the sources.
      </p>
    </div>
  );
}
