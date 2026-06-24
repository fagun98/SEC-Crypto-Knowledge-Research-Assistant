"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpenText, Landmark, MessageSquareText, Search, X } from "lucide-react";

const items = [
  { href: "/", label: "Overview", icon: Landmark },
  { href: "/chat", label: "Research Chat", icon: MessageSquareText },
  { href: "/reports", label: "Weekly Reports", icon: BookOpenText },
  { href: "/search", label: "Knowledge Search", icon: Search },
];

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {open && <button aria-label="Close navigation" onClick={onClose} className="fixed inset-0 z-30 bg-black/70 lg:hidden" />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-line bg-[#080d15]/95 p-6 backdrop-blur-xl transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-start justify-between">
          <Link href="/" className="flex items-center gap-3" onClick={onClose}>
            <span className="grid h-10 w-10 place-items-center rounded-md border border-gold/40 bg-gold/10 text-gold"><Landmark size={20} /></span>
            <span><span className="block text-sm font-semibold tracking-wide">SEC Crypto Knowledge</span><span className="block text-xs text-slate-500">Intelligence</span></span>
          </Link>
          <button onClick={onClose} className="text-slate-400 lg:hidden" aria-label="Close menu"><X size={20} /></button>
        </div>

        <div className="mt-10 text-[10px] font-semibold uppercase tracking-[.2em] text-slate-600">Research workspace</div>
        <nav className="mt-3 space-y-1">
          {items.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link key={href} href={href} onClick={onClose} className={`flex items-center gap-3 rounded-md border px-3 py-3 text-sm transition ${active ? "border-gold/25 bg-gold/[.08] text-slate-50" : "border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-100"}`}>
                <Icon size={17} className={active ? "text-gold" : "text-slate-500"} />{label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-line pt-5">
          <div className="flex items-center gap-2 text-xs text-slate-500"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />Knowledge pipeline connected</div>
          <p className="mt-3 text-[11px] leading-5 text-slate-600">Internal Research Interface<br />Source-grounded analysis</p>
        </div>
      </aside>
    </>
  );
}
