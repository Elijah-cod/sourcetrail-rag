import { BookOpen, FolderClosed, Menu, User } from "lucide-react";
import { Logo } from "./Logo";

type Props = {
  onOpenNav: () => void;
  onToggleSources: () => void;
  sourcesCount: number;
};

export function Header({ onOpenNav, onToggleSources, sourcesCount }: Props) {
  return (
    <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center justify-between border-b border-slate-200/80 bg-white/90 px-3 backdrop-blur-md sm:px-5">
      <div className="flex min-w-0 items-center gap-3 sm:gap-6">
        {/* Hamburger: only below the lg breakpoint, where the left rail becomes a drawer */}
        <button
          type="button"
          onClick={onOpenNav}
          className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Logo />
        <div className="hidden h-4 w-px bg-slate-200 md:block" />
        {/* Workspace indicator (there are no accounts: each browser gets a private workspace) */}
        <div
          className="hidden items-center gap-2 rounded-lg border border-slate-200/60 bg-white px-2.5 py-1.5 text-[13px] font-medium text-slate-700 shadow-2xs md:flex"
          title="Your uploads are private to this browser and deleted after 24 hours of inactivity."
        >
          <FolderClosed className="h-4 w-4 text-indigo-600" aria-hidden />
          <span className="truncate">Your workspace</span>
          <span className="text-[11px] font-normal text-slate-400">· 24h</span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={onToggleSources}
          className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12.5px] font-medium text-slate-700 transition-colors hover:bg-indigo-50/70 hover:text-indigo-600"
          title="Toggle sources panel"
        >
          <BookOpen className="h-4 w-4 text-indigo-600" aria-hidden />
          <span className="hidden md:inline">Sources</span>
          <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-indigo-100 px-1 font-mono text-[10px] font-semibold text-indigo-700">
            {sourcesCount}
          </span>
        </button>
        <div className="hidden h-4 w-px bg-slate-200 sm:block" />
        <div
          className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-800 text-white shadow-xs ring-2 ring-indigo-100"
          title="Guest — no account needed"
        >
          <User className="h-4 w-4" aria-hidden />
        </div>
      </div>
    </header>
  );
}
