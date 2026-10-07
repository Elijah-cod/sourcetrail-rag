"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Makes the whole window a drop target for files.
 * Returns true while files are being dragged over the page (to show an overlay).
 */
export function useFileDrop(onFiles: (files: File[]) => void) {
  const [dragging, setDragging] = useState(false);

  // Keep the latest callback in a ref, so the window listeners below are added only once.
  const onFilesRef = useRef(onFiles);
  useEffect(() => {
    onFilesRef.current = onFiles;
  }, [onFiles]);

  useEffect(() => {
    // dragenter/dragleave fire again for every child element the pointer crosses,
    // so we count them; the drag has really left the window when the count is back to 0.
    let depth = 0;
    const carriesFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");

    const onEnter = (e: DragEvent) => {
      if (!carriesFiles(e)) return;            // ignore dragging text or links around
      e.preventDefault();
      depth += 1;
      setDragging(true);
    };
    const onOver = (e: DragEvent) => {
      if (!carriesFiles(e)) return;
      e.preventDefault();                      // required, or the browser refuses the drop
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    };
    const onLeave = (e: DragEvent) => {
      if (!carriesFiles(e)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const onDrop = (e: DragEvent) => {
      if (!carriesFiles(e)) return;
      e.preventDefault();                      // stop the browser opening the file in a tab
      depth = 0;
      setDragging(false);
      const files = Array.from(e.dataTransfer?.files ?? []);
      if (files.length) onFilesRef.current(files);
    };

    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragover", onOver);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, []);

  return dragging;
}
