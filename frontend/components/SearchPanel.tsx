"use client";

import { FormEvent, useState } from "react";
import { ExternalLink, Search, SlidersHorizontal } from "lucide-react";
import { searchDocuments } from "@/lib/api";
import type { SearchResult } from "@/lib/types";

export default function SearchPanel() {
  const [query, setQuery] = useState("");
  const [alpha, setAlpha] = useState(0.5);
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true); setError(""); setSearched(true);
    try { setResults((await searchDocuments({ query, alpha, top_k: topK, score_threshold: 0 })).results); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Search is unavailable."); setResults([]); }
    finally { setLoading(false); }
  }

  const mode = alpha < .35 ? "Keyword-focused" : alpha > .65 ? "Semantic-focused" : "Balanced hybrid";
  return (
    <div className="grid gap-8 xl:grid-cols-[19rem_minmax(0,1fr)]">
      <form onSubmit={submit} className="panel h-fit rounded-lg p-5 xl:sticky xl:top-24"><div className="flex items-center gap-2 text-sm font-semibold"><SlidersHorizontal size={16} className="text-gold" />Search controls</div><label className="mt-6 block text-[10px] uppercase tracking-[.17em] text-slate-600">Research query</label><textarea className="field mt-2 resize-none" rows={5} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="stablecoin custody SEC guidance" /><div className="mt-6 flex items-end justify-between"><label className="text-[10px] uppercase tracking-[.17em] text-slate-600">Retrieval blend</label><span className="text-xs text-gold">{alpha.toFixed(1)}</span></div><input className="mt-3 w-full accent-[#c8a96a]" type="range" min="0" max="1" step="0.1" value={alpha} onChange={(e) => setAlpha(Number(e.target.value))} /><div className="mt-2 flex justify-between text-[9px] text-slate-600"><span>Keyword</span><span>{mode}</span><span>Semantic</span></div><label className="mt-6 block text-[10px] uppercase tracking-[.17em] text-slate-600">Results</label><select className="field mt-2" value={topK} onChange={(e) => setTopK(Number(e.target.value))}>{[5, 10, 20, 30, 50].map((n) => <option key={n}>{n}</option>)}</select><button disabled={loading || !query.trim()} className="button-primary mt-6 w-full disabled:opacity-40"><Search size={15} />{loading ? "Searching…" : "Search knowledge base"}</button></form>

      <section>{!searched && <div className="panel grid min-h-[28rem] place-items-center rounded-lg p-8 text-center"><div><div className="mx-auto grid h-12 w-12 place-items-center rounded-full border border-line text-slate-600"><Search size={20} /></div><h2 className="mt-5 font-serif text-2xl">Direct corpus search</h2><p className="mx-auto mt-3 max-w-md text-sm leading-7 text-slate-500">Retrieve SEC source materials directly. Adjust the blend to favor exact terminology or conceptual similarity.</p></div></div>}{error && <div className="rounded-md border border-red-900/60 bg-red-950/25 p-4 text-sm text-red-300">{error}</div>}{searched && !loading && !error && results.length === 0 && <div className="panel rounded-lg p-10 text-center text-sm text-slate-500">No documents met the search criteria.</div>}{results.length > 0 && <><div className="mb-4 flex items-center justify-between text-xs text-slate-500"><span>{results.length} sources retrieved</span><span>{mode}</span></div><div className="space-y-3">{results.map((result, index) => <article key={`${result.url}-${index}`} className="panel rounded-lg p-5 sm:p-6"><div className="flex gap-4"><span className="font-mono text-[10px] text-gold">{String(index + 1).padStart(2, "0")}</span><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-4"><h2 className="text-sm font-semibold leading-6 text-slate-100">{result.title}</h2><span className="shrink-0 rounded border border-line px-2 py-1 font-mono text-[10px] text-slate-400">{result.score.toFixed(3)}</span></div><p className="mt-3 text-xs leading-6 text-slate-400">{result.snippet}</p>{result.url && <a href={result.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1.5 text-xs text-gold hover:underline">Open official source <ExternalLink size={12} /></a>}</div></div></article>)}</div></>}</section>
    </div>
  );
}
