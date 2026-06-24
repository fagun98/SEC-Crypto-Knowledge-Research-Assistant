"use client";

import { Menu, ShieldCheck } from "lucide-react";

export default function TopBar({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line/70 bg-ink/80 px-5 backdrop-blur-xl sm:px-8">
      <button onClick={onMenu} className="rounded-md border border-line p-2 text-slate-300 lg:hidden" aria-label="Open navigation"><Menu size={19} /></button>
      <div className="hidden text-xs tracking-wide text-slate-500 sm:block">Digital Assets · Market Structure · Regulatory Research</div>
      <div className="ml-auto flex items-center gap-2 text-xs text-slate-500"><ShieldCheck size={15} className="text-gold" />Research support only</div>
    </header>
  );
}
