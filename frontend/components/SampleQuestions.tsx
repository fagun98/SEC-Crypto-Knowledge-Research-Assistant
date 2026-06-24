import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export const sampleQuestions = [
  "When should a crypto asset or crypto transaction be treated as a securities transaction?",
  "What exact compliance path should a crypto trading platform, ATS, exchange, or broker-dealer follow?",
  "How should custody rules apply to crypto assets, tokenized securities, and stablecoins?",
  "What rules are needed for tokenized securities to work in real markets?",
  "Where do SEC and CFTC rules need to be harmonized for crypto products and venues?",
];

export default function SampleQuestions({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "space-y-2" : "grid gap-3 md:grid-cols-2"}>
      {sampleQuestions.map((question, index) => (
        <Link key={question} href={`/chat?q=${encodeURIComponent(question)}`} className={`group flex items-start justify-between gap-4 rounded-md border border-line bg-raised/35 text-left text-slate-300 transition hover:border-gold/35 hover:bg-gold/[.04] ${compact ? "p-3 text-xs leading-5" : "p-5 text-sm leading-6"}`}>
          <span><span className="mr-3 font-mono text-[10px] text-gold">0{index + 1}</span>{question}</span><ArrowUpRight size={15} className="mt-1 shrink-0 text-slate-600 transition group-hover:text-gold" />
        </Link>
      ))}
    </div>
  );
}
