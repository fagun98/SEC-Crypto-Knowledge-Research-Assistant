import { ExternalLink } from "lucide-react";
import type { Source } from "@/lib/types";

export default function SourceCard({ source, index }: { source: Source; index: number }) {
  const content = (
    <div className="group rounded-md border border-line bg-ink/45 p-4 transition hover:border-slate-500">
      <div className="flex items-start gap-3"><span className="font-mono text-[10px] text-gold">{String(index + 1).padStart(2, "0")}</span><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-3"><h4 className="text-xs font-semibold leading-5 text-slate-200">{source.title}</h4>{source.url && <ExternalLink size={13} className="mt-1 shrink-0 text-slate-600 group-hover:text-gold" />}</div>{source.snippet && <p className="mt-2 line-clamp-3 text-[11px] leading-5 text-slate-500">{source.snippet}</p>}{typeof source.score === "number" && <div className="mt-3 text-[10px] uppercase tracking-wider text-slate-600">Relevance {(source.score * 100).toFixed(0)}%</div>}</div></div>
    </div>
  );
  return source.url ? <a href={source.url} target="_blank" rel="noreferrer">{content}</a> : content;
}
