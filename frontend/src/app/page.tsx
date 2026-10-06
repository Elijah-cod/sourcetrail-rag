"use client";

import { useState } from "react";
import { Composer } from "@/components/Composer";
import { DocumentsView } from "@/components/DocumentsView";
import { EmptyChat } from "@/components/EmptyChat";
import { Header } from "@/components/Header";
import { Sidebar, type View } from "@/components/Sidebar";
import { SourcesPanel } from "@/components/SourcesPanel";
import { Toast, useToast } from "@/components/Toast";
import { useDocuments } from "@/hooks/useDocuments";
import { useHealth } from "@/hooks/useHealth";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const { toast, show } = useToast();
  const online = useHealth();
  const docs = useDocuments(show);

  return (
    <div className="flex h-dvh flex-col">
      <Header
        onOpenNav={() => setNavOpen(true)}
        onToggleSources={() => setSourcesOpen((open) => !open)}
        sourcesCount={0}
        chunkCount={docs.chunkCount}
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
              <Composer onSubmit={() => {}} onAttach={(files) => void docs.upload(files)} uploading={docs.busy} />
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
      <Toast toast={toast} />
    </div>
  );
}
