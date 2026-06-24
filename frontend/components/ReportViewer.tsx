"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, CalendarDays, Clock3, ExternalLink, FileText, RefreshCw, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getLatestReport, getReport, getReports } from "@/lib/api";
import type { ReportDetail, ReportSummary } from "@/lib/types";

function formatDate(date: string, options?: Intl.DateTimeFormatOptions) {
  return new Date(`${date}T12:00:00`).toLocaleDateString(
    undefined,
    options || { year: "numeric", month: "long", day: "numeric" },
  );
}

function reportBody(content: string) {
  const lines = content.split("\n");
  let index = 0;
  while (index < lines.length && (!lines[index].trim() || /^#{1,3}\s/.test(lines[index]))) index += 1;
  return lines.slice(index).join("\n").trim();
}

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

  const content = report ? reportBody(report.content) : "";
  const readingMinutes = Math.max(1, Math.ceil(content.split(/\s+/).length / 220));
  const sourceCount = new Set(content.match(/https?:\/\/[^\s)]+/g) || []).size;
  const isLatest = report?.filename === reports[0]?.filename;

  return (
    <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_19rem]">
      <section>
        {loading && !report && <div className="panel grid min-h-[30rem] place-items-center rounded-lg text-sm text-slate-500"><RefreshCw className="mr-2 inline animate-spin" size={16} />Preparing memorandum…</div>}
        {error && !report && <div className="panel grid min-h-[30rem] place-items-center rounded-lg p-8 text-center"><div><FileText className="mx-auto text-slate-600" size={32} /><h2 className="mt-5 font-serif text-xl">No weekly report is available yet.</h2><p className="mt-2 text-sm text-slate-500">{error}</p><button onClick={() => void refresh()} className="button-secondary mt-6"><RefreshCw size={14} />Refresh</button></div></div>}
        {report && (
          <article
            key={report.filename}
            className={`report-document panel overflow-hidden rounded-xl transition-opacity duration-300 ${loading ? "opacity-55" : "opacity-100"}`}
          >
            <header className="relative overflow-hidden border-b border-line px-6 py-8 sm:px-10 sm:py-10">
              <div className="pointer-events-none absolute -right-16 -top-28 h-64 w-64 rounded-full border border-gold/10" />
              <div className="pointer-events-none absolute -right-3 -top-12 h-40 w-40 rounded-full border border-slate-700/40" />
              <div className="relative">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="eyebrow">Custody Intelligence Weekly</div>
                  <span className="rounded-full border border-emerald-400/20 bg-emerald-400/[.07] px-2.5 py-1 text-[9px] font-bold uppercase tracking-[.16em] text-emerald-300">
                    {isLatest ? "Latest issue" : "Archive issue"}
                  </span>
                </div>
                <h2 className="mt-5 max-w-3xl font-serif text-3xl leading-tight text-white sm:text-4xl">
                  The regulatory digest for crypto custodians
                </h2>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
                  A source-grounded review of the week’s custody developments, role-specific implications,
                  enforcement signals, and compliance priorities.
                </p>
                <div className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-xs text-slate-500">
                  <span className="flex items-center gap-2"><CalendarDays size={14} className="text-gold" />Week ending {formatDate(report.date)}</span>
                  <span className="flex items-center gap-2"><Clock3 size={14} />{readingMinutes} min read</span>
                  <span className="flex items-center gap-2"><ExternalLink size={14} />{sourceCount} source links</span>
                  <span className="flex items-center gap-2"><ShieldCheck size={14} />Research support only</span>
                </div>
              </div>
            </header>
            <div className="report-prose prose prose-invert max-w-none px-6 py-9 sm:px-10 sm:py-12">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ children, ...props }) => <a {...props} target="_blank" rel="noreferrer">{children}</a>,
                  table: ({ children, ...props }) => <div className="report-table-wrap"><table {...props}>{children}</table></div>,
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          </article>
        )}
      </section>

      <aside>
        <div className="sticky top-24 overflow-hidden rounded-xl border border-line bg-panel/70 shadow-panel backdrop-blur-xl">
          <div className="border-b border-line/80 p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="eyebrow">Report archive</div>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                  <BookOpen size={13} /> {reports.length} issues available
                </div>
              </div>
              <button onClick={() => void refresh()} disabled={loading} className="rounded-md border border-line p-2 text-slate-500 transition hover:border-gold/30 hover:text-gold" title="Refresh reports">
                <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              </button>
            </div>
          </div>
          <div className="p-2">
            {reports.map((item, index) => {
              const active = report?.filename === item.filename;
              return (
                <button
                  key={item.filename}
                  onClick={() => void select(item.filename)}
                  aria-current={active ? "true" : undefined}
                  className={`group relative w-full rounded-lg border px-4 py-4 text-left transition-all duration-200 ${active ? "border-gold/25 bg-gold/[.07]" : "border-transparent hover:bg-slate-800/55"}`}
                >
                  {active && <span className="absolute inset-y-4 left-0 w-0.5 rounded-full bg-gold" />}
                  <span className={`block text-[9px] font-bold uppercase tracking-[.16em] ${active ? "text-gold" : "text-slate-700"}`}>
                    Issue {String(reports.length - index).padStart(2, "0")}
                  </span>
                  <span className={`mt-1.5 block text-xs font-semibold ${active ? "text-slate-100" : "text-slate-400 group-hover:text-slate-200"}`}>
                    Week ending {formatDate(item.date, { month: "short", day: "numeric", year: "numeric" })}
                  </span>
                  <span className="mt-1.5 block truncate text-[10px] text-slate-600">{item.filename}</span>
                </button>
              );
            })}
          </div>
          <div className="border-t border-line/70 px-5 py-4 text-[10px] leading-5 text-slate-600">
            Issues are generated from the shared SEC knowledge pipeline and retained for week-over-week comparison.
          </div>
        </div>
      </aside>
    </div>
  );
}
