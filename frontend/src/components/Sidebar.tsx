"use client";

import { BarChart3, FileText, MessageSquare, Plus, RotateCcw, X } from "lucide-react";
import type { ReactNode } from "react";
import type { Health } from "@/hooks/useHealth";
import { useModalDrawer } from "@/hooks/useModalDrawer";

export type View = "chat" | "documents" | "benchmarks";

const HEALTH: Record<Health, { label: string; dot: string }> = {
  connecting: { label: "Connecting…", dot: "bg-ink-300" },
  starting: { label: "Starting up…", dot: "animate-pulse bg-warning-500" },
  online: { label: "Engine Online", dot: "bg-success-500" },
  offline: { label: "Engine Offline", dot: "bg-danger-500" },
};

type Props = {
  view: View;
  onNavigate: (view: View) => void;
  onNewQuery: () => void;
  open: boolean;              // drawer state on small screens (always visible on lg+)
  onClose: () => void;
  documentCount: number | null;   // the visitor's own documents (the demo collection isn't counted)
  recentQuestions: string[];
  onPickRecent: (question: string) => void;
  health: Health;
};

export function Sidebar(props: Props) {
  const { view, onNavigate, open, onClose } = props;
  const { panel, modal } = useModalDrawer<HTMLDivElement>(open, onClose);

  const go = (next: View) => {
    onNavigate(next);
    onClose(); // on phones, close the drawer after choosing
  };

  return (
    <>
      {/* Dimmed backdrop behind the drawer (small screens only) */}
      <div
        className={`fixed inset-0 z-40 bg-ink-900/30 transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panel}
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 select-none flex-col justify-between border-r border-ink-200 bg-raised p-3 transition-[transform,visibility] duration-200 lg:static lg:z-auto lg:w-56 lg:translate-x-0 ${
          open ? "translate-x-0" : "invisible -translate-x-full lg:visible"
        }`}
        aria-label="Main navigation"
        // A drawer over the page on small screens; an ordinary side column on lg and up.
        {...(modal ? { role: "dialog", "aria-modal": true } : { role: "complementary" })}
        inert={modal && !open}
      >
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-end lg:hidden">
            <button type="button" onClick={onClose} data-autofocus className="flex h-11 w-11 items-center justify-center rounded-lg text-ink-500 hover:bg-ink-100" aria-label="Close navigation">
              <X className="h-5 w-5" />
            </button>
          </div>

          <button
            type="button"
            onClick={() => {
              props.onNewQuery();
              go("chat");
            }}
            className="group flex w-full items-center justify-center gap-2 rounded-lg border border-brand-200/80 bg-brand-50 px-3 py-2.5 text-[13px] font-semibold text-brand-700 shadow-2xs transition-all hover:bg-brand-100/80"
          >
            <Plus className="h-4 w-4 transition-transform group-hover:scale-110 motion-reduce:group-hover:scale-100" aria-hidden />
            New Query
          </button>

          <nav className="flex flex-col gap-1">
            <SectionLabel>Workspace</SectionLabel>
            <NavItem active={view === "chat"} onClick={() => go("chat")} icon={<MessageSquare className="h-[18px] w-[18px]" />}>
              Chat Assistant
            </NavItem>
            <NavItem
              active={view === "documents"}
              onClick={() => go("documents")}
              icon={<FileText className="h-[18px] w-[18px]" />}
              badge={props.documentCount ?? undefined}
            >
              Documents
            </NavItem>
            <NavItem active={view === "benchmarks"} onClick={() => go("benchmarks")} icon={<BarChart3 className="h-[18px] w-[18px]" />}>
              Benchmarks
            </NavItem>
          </nav>

          {props.recentQuestions.length > 0 && (
            <div className="mt-2 flex flex-col gap-1">
              {/* Not saved conversations: picking one asks it again, so the label says so. */}
              <SectionLabel>Ask again</SectionLabel>
              {props.recentQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => {
                    props.onPickRecent(question);
                    go("chat");
                  }}
                  className="group flex min-h-11 items-center gap-2 rounded-md px-2.5 py-2 text-left text-[12px] text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900"
                  title={`Ask again: ${question}`}
                  aria-label={`Ask again: ${question}`}
                >
                  <RotateCcw className="h-3.5 w-3.5 shrink-0 text-ink-400 group-hover:text-brand-600" aria-hidden />
                  <span className="truncate">{question}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-ink-200 px-1 pt-3 text-xs text-ink-500">
          <span className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${HEALTH[props.health].dot}`} />
            <span className="font-medium text-ink-600">{HEALTH[props.health].label}</span>
          </span>
          <span className="rounded bg-ink-100 px-1 font-mono text-[12px] text-ink-600">v0.1</span>
        </div>
      </div>
    </>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return <span className="px-2 font-mono text-[12px] font-bold uppercase tracking-wider text-ink-500">{children}</span>;
}

type NavItemProps = {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  badge?: number;
  children: ReactNode;
};

function NavItem({ active, onClick, icon, badge, children }: NavItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`flex min-h-11 items-center justify-between rounded-lg px-2.5 py-2 text-[13px] transition-colors ${
        active
          ? "bg-brand-600/10 font-semibold text-brand-700"
          : "font-medium text-ink-600 hover:bg-ink-100/80 hover:text-ink-900"
      }`}
    >
      <span className="flex items-center gap-2.5">
        <span className={active ? "text-brand-600" : "text-ink-500"}>{icon}</span>
        {children}
      </span>
      {badge !== undefined && (
        <span className="rounded border border-ink-200/60 bg-ink-100 px-1.5 py-0.5 font-mono text-[12px] text-ink-500">{badge}</span>
      )}
      {active && badge === undefined && <span className="h-1.5 w-1.5 rounded-full bg-brand-600" />}
    </button>
  );
}
