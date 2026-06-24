import Link from "next/link";
import { ArrowRight, BookOpenText, Database, ShieldCheck } from "lucide-react";

export default function IntroHero() {
  return (
    <section className="relative overflow-hidden border-b border-line/70 px-6 py-20 sm:px-10 lg:px-14 lg:py-28">
      <div className="pointer-events-none absolute right-[-12rem] top-[-15rem] h-[34rem] w-[34rem] rounded-full border border-gold/10" />
      <div className="pointer-events-none absolute right-[-5rem] top-[-8rem] h-[22rem] w-[22rem] rounded-full border border-slate-700/50" />
      <div className="relative max-w-5xl">
        <div className="eyebrow flex items-center gap-2"><ShieldCheck size={14} /> Source-grounded regulatory intelligence</div>
        <h1 className="mt-6 max-w-4xl font-serif text-4xl leading-[1.08] tracking-[-.025em] text-white sm:text-6xl lg:text-[4.4rem]">SEC Crypto Knowledge<br /><span className="text-slate-400">Intelligence</span></h1>
        <p className="mt-7 max-w-3xl text-lg leading-8 text-slate-400">A research-grade AI assistant for exploring SEC cryptocurrency regulation, market structure, custody, tokenization, and compliance guidance.</p>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-500">Ask natural-language questions across SEC crypto-related materials, inspect supporting sources, and review weekly research summaries generated from the underlying knowledge pipeline.</p>
        <div className="mt-9 flex flex-wrap gap-3">
          <Link href="/chat" className="button-primary">Start Research <ArrowRight size={16} /></Link>
          <Link href="/reports" className="button-secondary"><BookOpenText size={16} />View Weekly Report</Link>
        </div>
        <div className="mt-14 flex flex-wrap gap-x-8 gap-y-3 border-t border-line/70 pt-5 text-xs text-slate-500">
          <span className="flex items-center gap-2"><Database size={14} className="text-gold" />Pinecone hybrid retrieval</span>
          <span className="flex items-center gap-2"><ShieldCheck size={14} className="text-gold" />Evidence-backed answers</span>
          <span className="flex items-center gap-2"><BookOpenText size={14} className="text-gold" />Weekly research memoranda</span>
        </div>
      </div>
    </section>
  );
}
