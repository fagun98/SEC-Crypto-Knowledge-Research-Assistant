import Link from "next/link";
import {
  ArrowDown,
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  CalendarCheck2,
  CheckCircle2,
  FileCheck2,
  Landmark,
  Radar,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const useCases = [
  {
    icon: CalendarCheck2,
    label: "Monday stand-up",
    title: "Set the week’s priorities",
    body: "Open with the executive summary and turn compliance action items into named owners.",
  },
  {
    icon: BriefcaseBusiness,
    label: "Executive briefing",
    title: "Explain what changed",
    body: "Share the bottom line and top developments without sending leaders through the full regulatory record.",
  },
  {
    icon: Scale,
    label: "Legal & risk",
    title: "Verify every conclusion",
    body: "Trace facts to official SEC materials and keep analysis and forward-looking inference clearly separated.",
  },
  {
    icon: Building2,
    label: "Product & strategy",
    title: "See around the corner",
    body: "Use the tracker and forward calendar to anticipate rulemaking, deadlines, and custody-control expectations.",
  },
] as const;

const reportLayers = [
  ["01", "Signal", "Official SEC releases, speeches, enforcement and rulemaking"],
  ["02", "Meaning", "Facts separated from analysis and clearly labeled inference"],
  ["03", "Impact", "Implications for BDs, RIAs, banks, trusts and custodians"],
  ["04", "Action", "A practical checklist, calendar and primary-source library"],
] as const;

export default function WeeklyReportOverview() {
  return (
    <section className="report-overview relative overflow-hidden border-b border-line/70 px-6 pb-16 pt-12 sm:px-8 lg:px-12 lg:pb-20 lg:pt-16">
      <div className="intelligence-grid pointer-events-none absolute inset-0 opacity-40" />
      <div className="pointer-events-none absolute left-[18%] top-0 h-72 w-72 rounded-full bg-blue-500/[.06] blur-[90px]" />
      <div className="pointer-events-none absolute right-[8%] top-10 h-80 w-80 rounded-full bg-gold/[.07] blur-[100px]" />

      <div className="relative mx-auto max-w-[92rem]">
        <div className="grid items-center gap-12 xl:grid-cols-[minmax(0,1.15fr)_minmax(25rem,.85fr)]">
          <div className="report-reveal">
            <div className="eyebrow flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              </span>
              Weekly intelligence product
            </div>
            <h1 className="mt-6 max-w-4xl font-serif text-4xl leading-[1.04] tracking-[-.035em] text-white sm:text-5xl lg:text-[4.25rem]">
              From regulatory signal
              <span className="block bg-gradient-to-r from-[#f1d59c] via-[#c8a96a] to-[#8bb9e8] bg-clip-text text-transparent">
                to defensible action.
              </span>
            </h1>
            <p className="mt-7 max-w-3xl text-base leading-8 text-slate-300 sm:text-lg">
              Custody Intelligence Weekly turns the prior week’s official SEC developments into a
              source-grounded operating brief for legal, compliance, policy, and executive teams.
            </p>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-500">
              Every issue separates facts, analysis, and inference; translates developments by
              institution type; and closes with concrete action items and direct links to primary sources.
            </p>

            <div className="mt-8 flex flex-wrap gap-2.5">
              {[
                [ShieldCheck, "SEC-primary sources"],
                [CalendarCheck2, "Published weekly"],
                [FileCheck2, "Audit-ready citations"],
                [Landmark, "Role-specific implications"],
              ].map(([Icon, label]) => (
                <span key={label as string} className="intelligence-chip">
                  <Icon size={14} />
                  {label as string}
                </span>
              ))}
            </div>

            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="#latest-report" className="button-primary">
                Read latest issue <ArrowDown size={15} />
              </Link>
              <Link href="/chat" className="button-secondary">
                Research a development <ArrowRight size={15} />
              </Link>
            </div>
          </div>

          <div className="report-reveal report-reveal-delay relative mx-auto w-full max-w-[34rem]">
            <div className="intelligence-orbit" aria-hidden="true">
              <div className="orbit-ring orbit-ring-one" />
              <div className="orbit-ring orbit-ring-two" />
              <div className="orbit-scan" />
              <span className="orbit-node orbit-node-one" />
              <span className="orbit-node orbit-node-two" />
              <span className="orbit-node orbit-node-three" />
              <div className="orbit-core">
                <Radar size={27} />
                <span>SEC</span>
                <small>signal engine</small>
              </div>
            </div>
            <div className="relative -mt-9 grid grid-cols-3 overflow-hidden rounded-xl border border-line/80 bg-[#0b121d]/90 shadow-2xl shadow-black/30 backdrop-blur-xl">
              {[
                ["Primary", "Sources"],
                ["Role-aware", "Analysis"],
                ["Weekly", "Actions"],
              ].map(([value, label], index) => (
                <div key={value} className={`px-3 py-4 text-center ${index ? "border-l border-line/70" : ""}`}>
                  <div className="text-xs font-semibold text-slate-200">{value}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[.16em] text-slate-600">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="report-reveal report-reveal-delay-2 mt-16 rounded-xl border border-line/80 bg-panel/55 p-2 shadow-panel backdrop-blur-xl lg:mt-20">
          <div className="grid gap-px overflow-hidden rounded-lg bg-line/80 md:grid-cols-2 xl:grid-cols-4">
            {reportLayers.map(([number, title, body]) => (
              <div key={number} className="group bg-[#0a111b] p-5 transition-colors duration-300 hover:bg-[#101a28] sm:p-6">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] tracking-[.18em] text-gold">{number}</span>
                  <Sparkles size={14} className="text-slate-700 transition-colors group-hover:text-gold/70" />
                </div>
                <h2 className="mt-5 text-sm font-semibold text-white">{title}</h2>
                <p className="mt-2 text-xs leading-6 text-slate-500">{body}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 grid gap-10 xl:grid-cols-[.7fr_1.3fr]">
          <div className="report-reveal">
            <div className="eyebrow">How clients use it</div>
            <h2 className="mt-4 max-w-md font-serif text-3xl leading-tight text-white sm:text-4xl">
              One brief, built for the whole decision chain.
            </h2>
            <p className="mt-5 max-w-lg text-sm leading-7 text-slate-500">
              Read the first screen in minutes for orientation, then move into the sections that match
              your role. The consistent weekly structure makes handoffs and comparisons effortless.
            </p>
            <div className="mt-7 flex items-center gap-3 text-xs text-slate-400">
              <CheckCircle2 size={16} className="text-emerald-400" />
              Designed for briefing, verification, planning, and audit support
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {useCases.map(({ icon: Icon, label, title, body }, index) => (
              <article
                key={title}
                className="report-use-card report-reveal rounded-lg border border-line/80 bg-[#0b121d]/75 p-5"
                style={{ animationDelay: `${240 + index * 80}ms` }}
              >
                <div className="flex items-center justify-between">
                  <span className="grid h-9 w-9 place-items-center rounded-md border border-gold/20 bg-gold/[.07] text-gold">
                    <Icon size={17} />
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-[.16em] text-slate-600">{label}</span>
                </div>
                <h3 className="mt-5 text-sm font-semibold text-slate-100">{title}</h3>
                <p className="mt-2 text-xs leading-6 text-slate-500">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
