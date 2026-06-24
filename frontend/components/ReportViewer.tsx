"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarDays, FileText, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getLatestReport, getReport, getReports } from "@/lib/api";
import type { ReportDetail, ReportSummary } from "@/lib/types";

export default function ReportViewer() {
  const [report, setReport] = useState<ReportDetail>();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [latest, available] = await Promise.all([getLatestReport(), getReports()]);
      setReport(latest); setReports(available.reports);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No weekly report is available yet."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function select(filename: string) {
    setLoading(true); setError("");
    try { setReport(await getReport(filename)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The report could not be loaded."); }
    finally { setLoading(false); }
  }

  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_18rem]">
      <section>
        {loading && !report && <div className="panel grid min-h-[30rem] place-items-center rounded-lg text-sm text-slate-500"><RefreshCw className="mr-2 inline animate-spin" size={16} />Preparing memorandum…</div>}
        {error && !report && <div className="panel grid min-h-[30rem] place-items-center rounded-lg p-8 text-center"><div><FileText className="mx-auto text-slate-600" size={32} /><h2 className="mt-5 font-serif text-xl">No weekly report is available yet.</h2><p className="mt-2 text-sm text-slate-500">{error}</p><button onClick={() => void refresh()} className="button-secondary mt-6"><RefreshCw size={14} />Refresh</button></div></div>}
        {report && <article className={`panel rounded-lg transition-opacity ${loading ? "opacity-60" : "opacity-100"}`}><header className="border-b border-line px-6 py-8 sm:px-10"><div className="eyebrow">Internal research memorandum</div><h2 className="mt-4 font-serif text-3xl text-white">{report.title}</h2><div className="mt-5 flex flex-wrap gap-5 text-xs text-slate-500"><span className="flex items-center gap-2"><CalendarDays size={14} className="text-gold" />{new Date(`${report.date}T12:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</span><span className="flex items-center gap-2"><FileText size={14} />{report.filename}</span></div></header><div className="prose prose-invert max-w-none px-6 py-8 prose-headings:font-serif prose-headings:font-medium prose-headings:text-slate-100 prose-p:text-slate-300 prose-p:leading-8 prose-li:text-slate-300 prose-a:text-gold prose-strong:text-slate-100 prose-hr:border-line sm:px-10 sm:py-12"><ReactMarkdown remarkPlugins={[remarkGfm]}>{report.content}</ReactMarkdown></div></article>}
      </section>

      <aside><div className="sticky top-24 rounded-lg border border-line bg-panel/60 p-4"><div className="flex items-center justify-between"><div><div className="eyebrow">Archive</div><div className="mt-1 text-xs text-slate-500">{reports.length} reports</div></div><button onClick={() => void refresh()} disabled={loading} className="rounded-md border border-line p-2 text-slate-500 hover:text-gold" title="Refresh reports"><RefreshCw size={14} className={loading ? "animate-spin" : ""} /></button></div><div className="mt-5 space-y-1">{reports.map((item) => <button key={item.filename} onClick={() => void select(item.filename)} className={`w-full rounded-md border px-3 py-3 text-left transition ${report?.filename === item.filename ? "border-gold/30 bg-gold/[.07]" : "border-transparent hover:bg-slate-800/60"}`}><span className="block text-xs font-medium text-slate-300">{new Date(`${item.date}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</span><span className="mt-1 block truncate text-[10px] text-slate-600">{item.filename}</span></button>)}</div></div></aside>
    </div>
  );
}
