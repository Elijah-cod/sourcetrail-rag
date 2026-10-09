/** The SourceTrail logo artwork. Decorative wherever the name sits beside it. */
export function LogoMark({ className = "h-7 w-7" }: { className?: string }) {
  // A static SVG: next/image would add nothing here, and the app is a static export.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src="/sourcetrail-icon.svg" alt="" aria-hidden className={`shrink-0 ${className}`} />;
}

/** The SourceTrail wordmark: logo + name + RAG badge. */
export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <LogoMark className="h-8 w-8" />
      <div className="flex items-baseline gap-1.5">
        <span className="font-heading text-[15px] font-bold tracking-tight text-ink-900">SourceTrail</span>
        <span className="rounded border border-brand-100/80 bg-brand-50 px-1.5 py-0.5 text-[12px] font-semibold text-brand-600">
          RAG
        </span>
      </div>
    </div>
  );
}
