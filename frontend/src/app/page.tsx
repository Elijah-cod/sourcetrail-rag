"use client";

import { useState } from "react";
import { ChatMessages } from "@/components/ChatMessages";
import { Composer } from "@/components/Composer";
import { DocumentsView } from "@/components/DocumentsView";
import { DropOverlay } from "@/components/DropOverlay";
import { EmptyChat } from "@/components/EmptyChat";
import { Header } from "@/components/Header";
import { Sidebar, type View } from "@/components/Sidebar";
import { SourceInspector } from "@/components/SourceInspector";
import { SourcesPanel } from "@/components/SourcesPanel";
import { Toast, useToast } from "@/components/Toast";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import { useFileDrop } from "@/hooks/useFileDrop";
import { useHealth } from "@/hooks/useHealth";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  // Which answer and which [n] the sources panel is showing.
  const [inspected, setInspected] = useState<{ answerId: number; n: number } | null>(null);

  const { toast, show } = useToast();
  const online = useHealth();
  const docs = useDocuments(show);
  const chat = useChat();
  const dragging = useFileDrop((files) => {
    if (docs.busy) show("Please wait for the current upload to finish.", "error");
    else void docs.upload(files);
  });

  // The answer shown in the sources panel: the inspected one, or else the latest finished one.
  const answers = chat.messages.filter((m) => m.role === "assistant" && m.status === "done");
  const panelAnswer =
    answers.find((m) => m.id === inspected?.answerId) ?? (answers.length ? answers[answers.length - 1] : undefined);
  const panelResult = panelAnswer?.role === "assistant" ? panelAnswer.result : undefined;

  const inspect = (answerId: number, n: number) => {
    setInspected({ answerId, n });
    setSourcesOpen(true);
  };

  const ask = async (question: string) => {
    setView("chat");
    const answerId = await chat.ask(question);
    // On wide screens, open the sources panel automatically the first time there's something to show.
    if (answerId && window.matchMedia("(min-width: 1024px)").matches) {
      setInspected({ answerId, n: 1 });
      setSourcesOpen(true);
    }
  };

  return (
    <div className="flex h-dvh flex-col">
      <Header
        onOpenNav={() => setNavOpen(true)}
        onToggleSources={() => setSourcesOpen((open) => !open)}
        sourcesCount={panelResult?.citations.length ?? 0}
      />
      <div className="flex flex-1 overflow-hidden pt-14">
        <Sidebar
          view={view}
          onNavigate={setView}
          onNewQuery={() => {
            chat.clear();
            setInspected(null);
          }}
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
              <div className="flex flex-1 flex-col overflow-y-auto px-4 py-6 md:px-8 md:py-8 lg:px-12">
                {chat.messages.length === 0 ? (
                  <EmptyChat onPick={(q) => void ask(q)} />
                ) : (
                  <ChatMessages messages={chat.messages} onCite={inspect} />
                )}
              </div>
              <Composer
                onSubmit={(q) => void ask(q)}
                disabled={chat.loading}
                onAttach={(files) => void docs.upload(files)}
                uploading={docs.busy}
                uploads={docs.uploads}
                onDismissUpload={docs.dismissUpload}
                onOpenDocuments={() => setView("documents")}
                settings={chat.settings}
                onChangeSettings={chat.setSettings}
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
        <SourcesPanel open={sourcesOpen} onClose={() => setSourcesOpen(false)}>
          {panelResult && panelAnswer && (
            <SourceInspector
              result={panelResult}
              selected={inspected?.answerId === panelAnswer.id ? inspected.n : 1}
              onSelect={(n) => setInspected({ answerId: panelAnswer.id, n })}
            />
          )}
        </SourcesPanel>
      </div>
      <DropOverlay visible={dragging} />
      <Toast toast={toast} />
    </div>
  );
}
