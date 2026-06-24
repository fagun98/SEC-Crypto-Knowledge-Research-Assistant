import AppShell from "@/components/AppShell";
import SearchPanel from "@/components/SearchPanel";

export default function SearchPage() {
  return <AppShell><div className="px-6 py-10 sm:px-8 lg:px-12"><div className="mb-9"><div className="eyebrow">Advanced retrieval</div><h1 className="mt-2 font-serif text-3xl">Knowledge Search</h1><p className="mt-2 text-sm text-slate-500">Search SEC crypto materials using a configurable semantic and keyword blend.</p></div><SearchPanel /></div></AppShell>;
}
