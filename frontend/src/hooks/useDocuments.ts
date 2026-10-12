"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { addUrl, deleteDocument, listDocuments, uploadDocument } from "@/lib/api";
import { shortUrl } from "@/lib/links";
import { uploadProblem } from "@/lib/uploads";
import type { DocumentInfo, IngestResult } from "@/lib/types";

/** One file or web page the visitor added in this session, and how it's going.
 *  Problems (e.g. a failed delete) also appear here, so nothing needs a pop-up. */
export type UploadItem = {
  id: number;
  kind: "file" | "link" | "notice";
  name: string;
  status: "processing" | "done" | "error";
  message?: string;      // the reason, when it failed; or a warning about a finished one
  detail?: string;       // what was indexed, e.g. "12 passages, 8,431 characters"
};

const errorText = (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback);

/** Everything about the document list: loading it, uploading, adding web pages, deleting. */
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const nextId = useRef(1);
  // A queue: each new job waits for the one before it. The server indexes one document
  // at a time per visitor anyway, and this means adding more while busy just works.
  const queue = useRef<Promise<unknown>>(Promise.resolve());

  const track = useCallback((kind: UploadItem["kind"], name: string, status: UploadItem["status"], message?: string) => {
    const item = { id: nextId.current++, kind, name, status, message };
    setUploads((list) => [...list, item]);
    return item.id;
  }, []);
  const update = useCallback((id: number, changes: Partial<UploadItem>) => {
    setUploads((list) => list.map((u) => (u.id === id ? { ...u, ...changes } : u)));
  }, []);
  const dismissUpload = useCallback((id: number) => setUploads((list) => list.filter((u) => u.id !== id)), []);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch {
      setDocuments((current) => current ?? []);
    }
  }, []);

  // Load once when the page opens. State is only set inside the promise callbacks,
  // and `cancelled` stops a late response from updating a page that's already gone.
  useEffect(() => {
    let cancelled = false;
    listDocuments()
      .then((list) => !cancelled && setDocuments(list))
      .catch((error) => {
        if (cancelled) return;
        setDocuments([]);
        track("notice", "Couldn't load your documents", "error", errorText(error, "Is the server running?"));
      });
    return () => {
      cancelled = true;
    };
  }, [track]);

  /** Put a job at the back of the queue; resolves with its result when its turn is done. */
  const enqueue = useCallback(<T,>(job: () => Promise<T>): Promise<T> => {
    const run = queue.current.then(job, job);
    queue.current = run.catch(() => undefined);
    return run;
  }, []);

  /** Index one item (file or page), keeping its chip up to date. Resolves to the result, or null. */
  const ingest = useCallback(
    (id: number, send: () => Promise<IngestResult>) =>
      enqueue(async () => {
        try {
          const result = await send();
          update(id, {
            status: "done",
            name: result.title,
            detail: `${result.chunk_count} passage${result.chunk_count === 1 ? "" : "s"}, ${result.characters.toLocaleString()} characters`,
            message: result.warning ?? undefined,
          });
          await refresh();                                   // show it in the list straight away
          return result;
        } catch (error) {
          update(id, { status: "error", message: errorText(error, "Could not add it") });
          return null;
        }
      }),
    [enqueue, refresh, update],
  );

  const upload = useCallback(
    async (files: File[]) => {
      // Catch wrong types and oversized files instantly, without uploading them.
      const jobs = files.map((file) => {
        const problem = uploadProblem(file);
        if (problem) {
          track("file", file.name, "error", problem);
          return Promise.resolve(null);
        }
        return ingest(track("file", file.name, "processing"), () => uploadDocument(file));
      });
      return Promise.all(jobs);
    },
    [ingest, track],
  );

  /** Add a web page. Resolves to its title and id, or null if it couldn't be added. */
  const addPage = useCallback(
    (url: string) => ingest(track("link", shortUrl(url), "processing"), () => addUrl(url)),
    [ingest, track],
  );

  const remove = useCallback(
    async (doc: DocumentInfo) => {
      if (!window.confirm(`Delete “${doc.title}”? This can't be undone.`)) return;
      // Take it off the list at once; the refresh below puts it back if the delete failed.
      setDocuments((list) => list?.filter((d) => d.id !== doc.id) ?? null);
      try {
        await deleteDocument(doc.id);
      } catch (error) {
        track("notice", `Couldn't delete “${doc.title}”`, "error", errorText(error, "Delete failed"));
      } finally {
        await refresh();
      }
    },
    [refresh, track],
  );

  const busy = uploads.some((u) => u.status === "processing");
  return { documents, busy, upload, addPage, remove, uploads, dismissUpload };
}
