import { BarChart3, FileText, MessageSquare, Plus, X } from "lucide-react";
import type { ReactNode } from "react";

export type View = "chat" | "documents" | "benchmarks";

type Props = {
  view: View;
  onNavigate: (view: View) => void;
  onNewQuery: () => void;
  open: boolean;              // drawer state on small screens (always visible on lg+)
  onClose: () => void;
  documentCount: number | null;
  recentQuestions: string[];
  onPickRecent: (question: string) => void;
  online: boolean | null;     // null = still checking
};

export function Sidebar(props: Props) {
  const { view, onNavigate, open, onClose } = props;

  const go = (next: View) => {
    onNavigate(next);
    onClose(); // on phones, close the drawer after choosing
  };

  return (
    <>
      {/* Dimmed backdrop behind the drawer (small screens only) */}
      <div
        className={`fixed inset-0 z-40 bg-slate-900/30 transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 select-none flex-col justify-between border-r border-slate-200 bg-white p-3 transition-transform duration-200 lg:static lg:z-auto lg:w-56 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Main navigation"
      >
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-end lg:hidden">
            <button type="button" onClick={onClose} className="rounded-md p-1 text-slate-500 hover:bg-slate-100" aria-label="Close navigation">
              <X className="h-5 w-5" />
            </button>
          </div>

          <button
            type="button"
            onClick={() => {
              props.onNewQuery();
              go("chat");
            }}
            className="group flex w-full items-center justify-center gap-2 rounded-lg border border-indigo-200/80 bg-indigo-50 px-3 py-2 text-[13px] font-semibold text-indigo-700 shadow-2xs transition-all hover:bg-indigo-100/80"
          >
            <Plus className="h-4 w-4 transition-transform group-hover:scale-110" aria-hidden />
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
              <SectionLabel>Recent Topics</SectionLabel>
              {props.recentQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => {
                    props.onPickRecent(question);
                    go("chat");
                  }}
                  className="truncate rounded-md px-2.5 py-1.5 text-left text-[12px] text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
                  title={question}
                >
                  {question}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-1 pt-3 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <span
              className={`h-2 w-2 rounded-full ${
                props.online === null ? "bg-slate-300" : props.online ? "bg-emerald-500" : "bg-rose-500"
              }`}
            />
            <span className="font-medium text-slate-600">
              {props.online === null ? "Connecting…" : props.online ? "Engine Online" : "Engine Offline"}
            </span>
          </span>
          <span className="rounded bg-slate-100 px-1 font-mono text-[11px] text-slate-400">v0.1</span>
        </div>
      </aside>
    </>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return <span className="px-2 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">{children}</span>;
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
      className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-[13px] transition-colors ${
        active
          ? "border-l-2 border-indigo-600 bg-indigo-600/10 font-semibold text-indigo-700"
          : "font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
      }`}
    >
      <span className="flex items-center gap-2.5">
        <span className={active ? "text-indigo-600" : "text-slate-400"}>{icon}</span>
        {children}
      </span>
      {badge !== undefined && (
        <span className="rounded border border-slate-200/60 bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-500">{badge}</span>
      )}
      {active && badge === undefined && <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />}
    </button>
  );
}
