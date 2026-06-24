import AppShell from "@/components/AppShell";
import ReportViewer from "@/components/ReportViewer";

export default function ReportsPage() {
  return <AppShell><div className="px-6 py-10 sm:px-8 lg:px-12"><div className="mb-9"><div className="eyebrow">Research archive</div><h1 className="mt-2 font-serif text-3xl">Weekly SEC Report</h1><p className="mt-2 text-sm text-slate-500">Latest generated research summary from the SEC crypto knowledge pipeline.</p></div><ReportViewer /></div></AppShell>;
}
