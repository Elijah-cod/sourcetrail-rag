"use client";

import { useState } from "react";
import { Composer } from "@/components/Composer";
import { EmptyChat } from "@/components/EmptyChat";
import { Header } from "@/components/Header";
import { Sidebar, type View } from "@/components/Sidebar";
import { SourcesPanel } from "@/components/SourcesPanel";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  return (
    <div className="flex h-dvh flex-col">
      <Header
        onOpenNav={() => setNavOpen(true)}
        onToggleSources={() => setSourcesOpen((open) => !open)}
        sourcesCount={0}
        chunkCount={null}
      />
      <div className="flex flex-1 overflow-hidden pt-14">
        <Sidebar
          view={view}
          onNavigate={setView}
          onNewQuery={() => {}}
          open={navOpen}
          onClose={() => setNavOpen(false)}
          documentCount={null}
          recentQuestions={[]}
          onPickRecent={() => {}}
          online={null}
        />
        <main className="relative flex flex-1 flex-col justify-between overflow-hidden bg-surface">
          {view === "chat" && (
            <>
              <div className="flex flex-1 flex-col overflow-y-auto px-4 py-8 md:px-8 lg:px-12">
                <EmptyChat onPick={() => {}} />
              </div>
              <Composer onSubmit={() => {}} />
            </>
          )}
          {view !== "chat" && (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
              The {view} view is coming in a later commit.
            </div>
          )}
        </main>
        <SourcesPanel open={sourcesOpen} onClose={() => setSourcesOpen(false)} />
      </div>
    </div>
  );
}
