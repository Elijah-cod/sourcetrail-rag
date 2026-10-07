"use client";

import { useState } from "react";
import { Composer } from "@/components/Composer";
import { DocumentsView } from "@/components/DocumentsView";
import { DropOverlay } from "@/components/DropOverlay";
import { EmptyChat } from "@/components/EmptyChat";
import { Header } from "@/components/Header";
import { Sidebar, type View } from "@/components/Sidebar";
import { SourcesPanel } from "@/components/SourcesPanel";
import { Toast, useToast } from "@/components/Toast";
import { useDocuments } from "@/hooks/useDocuments";
import { useFileDrop } from "@/hooks/useFileDrop";
import { useHealth } from "@/hooks/useHealth";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const { toast, show } = useToast();
  const online = useHealth();
  const docs = useDocuments(show);
  const dragging = useFileDrop((files) => {
    if (docs.busy) show("Please wait for the current upload to finish.", "error");
    else void docs.upload(files);
  });

  return (
    <div className="flex h-dvh flex-col">
      <Header
        onOpenNav={() => setNavOpen(true)}
        onToggleSources={() => setSourcesOpen((open) => !open)}
        sourcesCount={0}
      />
      <div className="flex flex-1 overflow-hidden pt-14">
        <Sidebar
          view={view}
          onNavigate={setView}
          onNewQuery={() => {}}
          open={navOpen}
          onClose={() => setNavOpen(false)}
          documentCount={docs.documents?.length ?? null}
          recentQuestions={[]}
          onPickRecent={() => {}}
          online={online}
        />
        <main className="relative flex flex-1 flex-col justify-between overflow-hidden bg-surface">
          {view === "chat" && (
            <>
              <div className="flex flex-1 flex-col overflow-y-auto px-4 py-8 md:px-8 lg:px-12">
                <EmptyChat onPick={() => {}} />
              </div>
              <Composer
                onSubmit={() => {}}
                onAttach={(files) => void docs.upload(files)}
                uploading={docs.busy}
                uploads={docs.uploads}
                onDismissUpload={docs.dismissUpload}
                onOpenDocuments={() => setView("documents")}
              />
            </>
          )}
          {view === "documents" && (
            <div className="flex-1 overflow-y-auto">
              <DocumentsView
                documents={docs.documents}
                onUpload={docs.upload}
                onAddUrl={docs.addPage}
                onDelete={docs.remove}
                busy={docs.busy}
                dragging={dragging}
                uploads={docs.uploads}
                onDismissUpload={docs.dismissUpload}
              />
            </div>
          )}
          {view === "benchmarks" && (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
              The benchmarks view is coming in a later commit.
            </div>
          )}
        </main>
        <SourcesPanel open={sourcesOpen} onClose={() => setSourcesOpen(false)} />
      </div>
      <DropOverlay visible={dragging} />
      <Toast toast={toast} />
    </div>
  );
}
