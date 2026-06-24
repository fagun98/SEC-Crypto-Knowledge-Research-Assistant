import { Suspense } from "react";
import AppShell from "@/components/AppShell";
import ChatInterface from "@/components/ChatInterface";

export default function ChatPage() {
  return <AppShell><Suspense fallback={<div className="p-10 text-sm text-slate-500">Opening research workspace…</div>}><ChatInterface /></Suspense></AppShell>;
}
