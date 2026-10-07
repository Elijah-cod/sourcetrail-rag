"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, addUrl, deleteDocument, listDocuments, uploadDocument } from "@/lib/api";
import { plural } from "@/lib/format";
import { uploadProblem } from "@/lib/uploads";
import type { DocumentInfo } from "@/lib/types";

type Notify = (message: string, kind?: "success" | "error") => void;

/** Everything about the document list: loading it, uploading, adding URLs, deleting. */
export function useDocuments(notify: Notify) {
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);
  const [busy, setBusy] = useState(false);

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
      const ok: File[] = [];
      for (const file of files) {
        const problem = uploadProblem(file);
        if (problem) notify(problem, "error");
        else ok.push(file);
      }
      if (ok.length === 0) return;

      setBusy(true);
      try {
        // One at a time: each file is extracted, chunked and embedded on the server.
        for (const file of ok) {
          try {
            const result = await uploadDocument(file);
            notify(`Added “${result.title}” (${plural(result.chunk_count, "chunk")})`);
          } catch (error) {
            notify(`${file.name}: ${error instanceof Error ? error.message : "upload failed"}`, "error");
          }
        }
      } finally {
        setBusy(false);
        await refresh();
      }
    },
    [notify, refresh],
  );

  const addPage = useCallback(
    async (url: string) => {
      setBusy(true);
      try {
        const result = await addUrl(url);
        notify(`Added “${result.title}” (${plural(result.chunk_count, "chunk")})`);
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

  const chunkCount = documents?.reduce((total, d) => total + d.chunk_count, 0) ?? null;
  const ownCount = documents?.filter((d) => !d.is_demo).length ?? null;

  return { documents, busy, upload, addPage, remove, chunkCount, ownCount };
}
