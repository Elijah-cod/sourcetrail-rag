"use client";

import { CheckCircle2, Download } from "lucide-react";
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
import { useRecentQuestions } from "@/hooks/useRecentQuestions";
import { answerWithSources, citationsMarkdown, copyText, downloadText } from "@/lib/clipboard";
import type { QueryResult } from "@/lib/types";

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
  const recent = useRecentQuestions();
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
    recent.remember(question);
    const answerId = await chat.ask(question);
    // On wide screens, open the sources panel automatically the first time there's something to show.
    if (answerId && window.matchMedia("(min-width: 1024px)").matches) {
      setInspected({ answerId, n: 1 });
      setSourcesOpen(true);
    }
  };

  const copyAndTell = async (text: string, done: string) => {
    const ok = await copyText(text);
    show(ok ? done : "Couldn't copy — your browser blocked clipboard access", ok ? "success" : "error");
  };
  const copyAnswer = (result: QueryResult) => copyAndTell(answerWithSources(result), "Answer copied with its sources");
  const copyPassage = (text: string) => copyAndTell(text, "Passage copied");

  const exportCitations = () => {
    if (!panelResult || panelAnswer?.role !== "assistant") return;
    downloadText("sourcetrail-citations.md", citationsMarkdown(panelAnswer.question, panelResult));
    show("Citations downloaded as sourcetrail-citations.md");
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
          recentQuestions={recent.questions}
          onPickRecent={(q) => void ask(q)}
          online={online}
        />
        <main className="relative flex flex-1 flex-col justify-between overflow-hidden bg-surface">
          {view === "chat" && (
            <>
              <div className="flex flex-1 flex-col overflow-y-auto px-4 py-6 md:px-8 md:py-8 lg:px-12">
                {chat.messages.length === 0 ? (
                  <EmptyChat onPick={(q) => void ask(q)} />
                ) : (
                  <ChatMessages
                    messages={chat.messages}
                    onCite={inspect}
                    onCopy={(result) => void copyAnswer(result)}
                    onRegenerate={(id) => void chat.regenerate(id)}
                    busy={chat.loading}
                  />
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
        <SourcesPanel
          open={sourcesOpen}
          onClose={() => setSourcesOpen(false)}
          footer={
            panelResult && panelResult.citations.length > 0 ? (
              <>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />
                  <span className="font-medium text-slate-700">
                    {panelResult.citations.length} cited passage{panelResult.citations.length === 1 ? "" : "s"}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={exportCitations}
                  className="flex items-center gap-1 text-xs font-semibold text-indigo-600 transition-colors hover:text-indigo-700"
                >
                  <Download className="h-3.5 w-3.5" aria-hidden />
                  Export citations
                </button>
              </>
            ) : undefined
          }
        >
          {panelResult && panelAnswer && (
            <SourceInspector
              result={panelResult}
              selected={inspected?.answerId === panelAnswer.id ? inspected.n : 1}
              onSelect={(n) => setInspected({ answerId: panelAnswer.id, n })}
              onCopyPassage={(text) => void copyPassage(text)}
            />
          )}
        </SourcesPanel>
      </div>
      <DropOverlay visible={dragging} />
      <Toast toast={toast} />
    </div>
  );
}
