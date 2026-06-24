import { Binary, BookOpenCheck, Database, FileSearch, MessagesSquare, Network } from "lucide-react";
import AppShell from "@/components/AppShell";
import IntroHero from "@/components/IntroHero";
import SampleQuestions from "@/components/SampleQuestions";

const capabilities = [
  [MessagesSquare, "Conversational research", "Maintain context across a structured regulatory research workflow."],
  [Binary, "Hybrid retrieval", "Blend sparse keyword precision with dense semantic relevance."],
  [BookOpenCheck, "Source-grounded answers", "Inspect the SEC materials supporting each substantive response."],
  [FileSearch, "Weekly report viewer", "Read recurring research summaries in a focused memorandum format."],
  [Network, "LangGraph workflows", "Coordinate classification, retrieval, reranking, and answer synthesis."],
  [Database, "Pinecone vector search", "Search the indexed SEC crypto corpus with configurable controls."],
] as const;

export default function Home() {
  return (
    <AppShell>
      <IntroHero />
      <section className="px-6 py-16 sm:px-10 lg:px-14">
        <div className="grid gap-12 xl:grid-cols-[.75fr_1.25fr]">
          <div><div className="eyebrow">Mandate</div><h2 className="mt-4 font-serif text-3xl text-white">A clearer path through a fast-moving regulatory record.</h2><p className="mt-5 text-sm leading-7 text-slate-400">This assistant helps researchers and officials analyze written submissions, meetings, staff statements, guidance, and related SEC materials—then move from retrieval to a transparent, evidence-backed synthesis.</p></div>
          <div className="panel rounded-lg p-6 sm:p-8"><div className="eyebrow">Research process</div><div className="mt-7 grid gap-3 sm:grid-cols-5">{["User question", "Hybrid retrieval", "SEC knowledge base", "LangGraph agent", "Evidence-backed answer"].map((label, i) => <div key={label} className="relative rounded-md border border-line bg-ink/50 px-3 py-4 text-center text-xs leading-5 text-slate-300"><span className="mb-2 block font-mono text-[10px] text-gold">0{i + 1}</span>{label}{i < 4 && <span className="absolute -right-2 top-1/2 z-10 hidden text-slate-600 sm:block">›</span>}</div>)}</div></div>
        </div>

        <div className="mt-20"><div className="eyebrow">Capabilities</div><h2 className="mt-3 font-serif text-3xl">Built for disciplined inquiry</h2><div className="mt-8 grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-2 xl:grid-cols-3">{capabilities.map(([Icon, title, body]) => <div key={title} className="bg-panel p-6"><Icon size={20} className="text-gold" /><h3 className="mt-5 text-sm font-semibold text-white">{title}</h3><p className="mt-2 text-xs leading-6 text-slate-500">{body}</p></div>)}</div></div>

        <div className="mt-20 grid gap-12 xl:grid-cols-[1fr_2fr]"><div><div className="eyebrow">Designed for</div><h2 className="mt-3 font-serif text-3xl">Policy, legal, and market practitioners</h2><p className="mt-4 text-sm leading-7 text-slate-500">SEC officials, compliance and legal teams, crypto firms, broker-dealers, exchanges, custodians, tokenization startups, and policy researchers.</p></div><div><div className="eyebrow mb-5">Begin with a sample inquiry</div><SampleQuestions /></div></div>
      </section>
    </AppShell>
  );
}
