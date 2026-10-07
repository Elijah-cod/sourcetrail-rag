"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, addUrl, deleteDocument, listDocuments, uploadDocument } from "@/lib/api";
import { uploadProblem } from "@/lib/uploads";
import type { DocumentInfo } from "@/lib/types";

type Notify = (message: string, kind?: "success" | "error") => void;

/** One file the visitor added in this session, and how it's going. */
export type UploadItem = {
  id: number;
  name: string;
  status: "processing" | "done" | "error";
  message?: string;      // the reason, when it failed
};

/** Everything about the document list: loading it, uploading, adding URLs, deleting. */
export function useDocuments(notify: Notify) {
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const nextId = useRef(1);

  // Add an upload to the list (returns its id) / change its status later.
  const track = useCallback((name: string, status: UploadItem["status"], message?: string) => {
    const item = { id: nextId.current++, name, status, message };
    setUploads((list) => [...list, item]);
    return item.id;
  }, []);
  const update = useCallback((id: number, changes: Partial<UploadItem>) => {
    setUploads((list) => list.map((u) => (u.id === id ? { ...u, ...changes } : u)));
  }, []);
  const dismissUpload = useCallback(
    (id: number) => setUploads((list) => list.filter((u) => u.id !== id)),
    [],
  );

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch (error) {
      setDocuments((current) => current ?? []);
      if (error instanceof ApiError) notify(error.message, "error");
    }
  }, [notify]);

  // Load once when the page opens. State is only set inside the promise callbacks,
  // and `cancelled` stops a late response from updating a page that's already gone.
  useEffect(() => {
    let cancelled = false;
    listDocuments()
      .then((list) => !cancelled && setDocuments(list))
      .catch((error) => {
        if (cancelled) return;
        setDocuments([]);
        if (error instanceof ApiError) notify(error.message, "error");
      });
    return () => {
      cancelled = true;
    };
  }, [notify]);

  const upload = useCallback(
    async (files: File[]) => {
      // Catch wrong types and oversized files instantly, without uploading them.
      const ok: { file: File; id: number }[] = [];
      for (const file of files) {
        const problem = uploadProblem(file);
        if (problem) track(file.name, "error", problem);
        else ok.push({ file, id: track(file.name, "processing") });
      }
      if (ok.length === 0) return;

      setBusy(true);
      try {
        // One at a time: each file is extracted, chunked and embedded on the server.
        for (const { file, id } of ok) {
          try {
            const result = await uploadDocument(file);
            update(id, { status: "done", name: result.title });
            notify(`Added “${result.title}”`);
            await refresh();                   // show it in the list straight away
          } catch (error) {
            update(id, { status: "error", message: error instanceof Error ? error.message : "Upload failed" });
          }
        }
      } finally {
        setBusy(false);
        await refresh();
      }
    },
    [notify, refresh, track, update],
  );

  const addPage = useCallback(
    async (url: string) => {
      setBusy(true);
      try {
        const result = await addUrl(url);
        notify(`Added “${result.title}”`);
        await refresh();
        return true;
      } catch (error) {
        notify(error instanceof Error ? error.message : "Could not add that page", "error");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [notify, refresh],
  );

  const remove = useCallback(
    async (doc: DocumentInfo) => {
      if (!window.confirm(`Delete “${doc.title}”? This can't be undone.`)) return;
      try {
        await deleteDocument(doc.id);
        notify(`Deleted “${doc.title}”`);
      } catch (error) {
        notify(error instanceof Error ? error.message : "Delete failed", "error");
      } finally {
        await refresh();
      }
    },
    [notify, refresh],
  );

  return { documents, busy, upload, addPage, remove, uploads, dismissUpload };
}
