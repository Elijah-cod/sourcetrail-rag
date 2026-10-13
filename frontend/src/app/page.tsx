"use client";

import { CheckCircle2, Download } from "lucide-react";
import { useState } from "react";
import { BenchmarksView } from "@/components/BenchmarksView";
import { ChatMessages } from "@/components/ChatMessages";
import { Composer } from "@/components/Composer";
import { DocumentsView } from "@/components/DocumentsView";
import { DropOverlay } from "@/components/DropOverlay";
import { EmptyChat } from "@/components/EmptyChat";
import { Header } from "@/components/Header";
import { Sidebar, type View } from "@/components/Sidebar";
import { SourceInspector } from "@/components/SourceInspector";
import { SourcesPanel } from "@/components/SourcesPanel";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import { useFileDrop } from "@/hooks/useFileDrop";
import { useHealth } from "@/hooks/useHealth";
import { useRecentQuestions } from "@/hooks/useRecentQuestions";
import { citationsMarkdown, downloadText } from "@/lib/clipboard";
import { splitLinks } from "@/lib/links";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  // Which answer and which [n] the sources panel is showing. `flash` counts clicks, so clicking
  // the same citation twice still replays the highlight in the panel.
  // `claim` is the answer sentence the clicked [n] belongs to, highlighted in the passage.
  const [inspected, setInspected] = useState<{ answerId: number; n: number; flash: number; claim?: string } | null>(null);

  const [addingLinks, setAddingLinks] = useState(false);

  const health = useHealth();
  const docs = useDocuments();
  const chat = useChat();
  const recent = useRecentQuestions();
  // Files dropped while another is indexing simply join the queue. The chat box and the Documents
  // page show upload progress; dropped anywhere else, go to Documents so it's visible.
  const dragging = useFileDrop((files) => {
    setView((current) => (current === "chat" ? current : "documents"));
    void docs.upload(files);
  });

  // The answer shown in the sources panel: the inspected one, or else the latest finished one.
  const answers = chat.messages.filter((m) => m.role === "assistant" && m.status === "done");
  const panelAnswer =
    answers.find((m) => m.id === inspected?.answerId) ?? (answers.length ? answers[answers.length - 1] : undefined);
  const panelResult = panelAnswer?.role === "assistant" ? panelAnswer.result : undefined;

  const inspect = (answerId: number, n: number, claim?: string) => {
    setInspected((prev) => ({ answerId, n, claim, flash: (prev?.flash ?? 0) + 1 }));
    setSourcesOpen(true);
  };

  const ask = async (question: string, query?: string) => {
    setView("chat");
    recent.remember(question);
    const answerId = await chat.ask(question, query);
    // On wide screens, open the sources panel automatically the first time there's something to show.
    if (answerId && window.matchMedia("(min-width: 1024px)").matches) {
      setInspected({ answerId, n: 1, flash: 0 });
      setSourcesOpen(true);
    }
  };

  /** Everything typed in the chat box comes here. Links are added to the workspace first
   *  (their chips show progress), then whatever text is left is asked as a question.
   *  Returns text to put back in the box when something needs fixing. */
  const submit = async (message: string): Promise<string | null> => {
    const { urls, question } = splitLinks(message);
    if (urls.length === 0) {
      void ask(message);
      return null;
    }

    setAddingLinks(true);
    const added = await Promise.all(urls.map((url) => docs.addPage(url)));
    setAddingLinks(false);

    const failed = urls.filter((_, i) => added[i] === null);
    if (failed.length > 0) {
      // The chip says why. Put back the message minus the links that worked, so retrying
      // doesn't add those pages twice.
      return urls.reduce((text, url, i) => (added[i] ? text.replace(url, "") : text), message).replace(/\s{2,}/g, " ").trim();
    }
    if (!question) return null;            // just links: the "added" chips are the confirmation

    // "Summarise https://…" alone would search for "Summarise". Naming the page(s) points the
    // search at what was just added, while the chat still shows the message as typed.
    const titles = added.map((doc) => `“${doc!.title}”`).join(", ");
    void ask(message, `${question} (about ${urls.length === 1 ? "the page" : "the pages"} ${titles})`);
    return null;
  };

  const exportCitations = () => {
    if (!panelResult || panelAnswer?.role !== "assistant") return;
    downloadText("sourcetrail-citations.md", citationsMarkdown(panelAnswer.question, panelResult));
  };

  return (
    <div className="flex h-dvh flex-col">
      <Header
        onOpenNav={() => setNavOpen(true)}
        onToggleSources={() => setSourcesOpen((open) => !open)}
        sourcesOpen={sourcesOpen}
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
          documentCount={docs.documents ? docs.documents.filter((d) => !d.is_demo).length : null}
          recentQuestions={recent.questions}
          onPickRecent={(q) => void ask(q)}
          health={health}
        />
        <main className="relative flex flex-1 flex-col justify-between overflow-hidden bg-surface">
          {view === "chat" && (
            <>
              <div className="flex flex-1 flex-col overflow-y-auto px-4 py-6 md:px-8 md:py-8 lg:px-12">
                {chat.messages.length === 0 ? (
                  <EmptyChat onPick={(q) => void ask(q)} />
                ) : (
                  <>
                    <h1 className="sr-only">Chat</h1>
                    <ChatMessages
                      messages={chat.messages}
                      onCite={inspect}
                      active={sourcesOpen ? inspected : null}
                      onRegenerate={(id) => void chat.regenerate(id)}
                      onStop={chat.stop}
                      busy={chat.loading}
                    />
                  </>
                )}
              </div>
              <Composer
                onSubmit={submit}
                disabled={chat.loading || addingLinks}
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
            <div className="flex-1 overflow-y-auto">
              <BenchmarksView />
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
                  <CheckCircle2 className="h-4 w-4 text-success-600" aria-hidden />
                  <span className="font-medium text-ink-700">
                    {panelResult.citations.length} cited passage{panelResult.citations.length === 1 ? "" : "s"}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={exportCitations}
                  className="-my-1.5 flex min-h-11 items-center gap-1 rounded-lg px-2 text-xs font-semibold text-brand-600 transition-colors hover:bg-brand-50 hover:text-brand-700"
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
              flash={inspected?.flash ?? 0}
              claim={inspected?.answerId === panelAnswer.id ? inspected.claim : undefined}
              onSelect={(n) => setInspected((prev) => ({ answerId: panelAnswer.id, n, flash: prev?.flash ?? 0 }))}
            />
          )}
        </SourcesPanel>
      </div>
      <DropOverlay visible={dragging} />
    </div>
  );
}
