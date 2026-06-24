"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Eraser, Send, Sparkles } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { sendChatMessage } from "@/lib/api";
import MessageBubble, { type ChatMessage } from "./MessageBubble";
import SampleQuestions from "./SampleQuestions";

const STORAGE_KEY = "sec-crypto-research-session";

export default function ChatInterface() {
  const params = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") as { messages?: ChatMessage[]; sessionId?: string };
      if (saved.messages) setMessages(saved.messages);
      if (saved.sessionId) setSessionId(saved.sessionId);
    } catch {}
    const question = params.get("q");
    if (question) setInput(question);
  }, [params]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, sessionId }));
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sessionId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) return;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const prior = messages;
    setMessages((current) => [...current, userMessage]);
    setInput(""); setError(""); setLoading(true);
    try {
      const response = await sendChatMessage({
        message: question,
        session_id: sessionId,
        history: prior.map(({ role, content }) => ({ role, content })).slice(-12),
      });
      setSessionId(response.session_id);
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: response.answer, sources: response.sources, metadata: response.metadata }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The assistant is unavailable.");
    } finally { setLoading(false); }
  }

  function clear() { setMessages([]); setSessionId(undefined); setError(""); localStorage.removeItem(STORAGE_KEY); }

  return (
    <div className="grid min-h-[calc(100vh-4rem)] xl:grid-cols-[minmax(0,1fr)_19rem]">
      <section className="flex min-w-0 flex-col px-5 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto flex w-full max-w-4xl items-start justify-between gap-4"><div><div className="eyebrow">Conversational research</div><h1 className="mt-2 font-serif text-3xl text-white">Research Chat</h1><p className="mt-2 text-sm text-slate-500">Ask evidence-backed questions across the SEC crypto knowledge base.</p></div>{messages.length > 0 && <button onClick={clear} className="button-secondary !px-3 !py-2 text-xs"><Eraser size={14} />Clear</button>}</div>

        <div className="mx-auto mt-9 w-full max-w-4xl flex-1 space-y-7">
          {messages.length === 0 && <div className="panel rounded-lg p-7 sm:p-10"><div className="grid h-10 w-10 place-items-center rounded-md border border-gold/30 bg-gold/[.08] text-gold"><Sparkles size={18} /></div><h2 className="mt-6 font-serif text-2xl">Begin a regulatory inquiry</h2><p className="mt-3 max-w-xl text-sm leading-7 text-slate-500">Ask a focused question, compare regulatory positions, or trace an issue across source materials. Citations and retrieval context appear with each response.</p><div className="mt-7"><SampleQuestions compact /></div></div>}
          {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
          {loading && <div className="flex items-center gap-3 text-xs text-slate-500"><div className="flex gap-1"><i className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold" /><i className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold [animation-delay:150ms]" /><i className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold [animation-delay:300ms]" /></div>Retrieving and synthesizing source material…</div>}
          {error && <div className="rounded-md border border-red-900/60 bg-red-950/25 px-4 py-3 text-sm text-red-300">{error}</div>}
          <div ref={endRef} />
        </div>

        <form onSubmit={submit} className="sticky bottom-0 mx-auto mt-8 w-full max-w-4xl border-t border-line bg-ink/95 py-5 backdrop-blur"><div className="relative"><textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} rows={3} placeholder="Ask about securities classification, custody, market structure, or compliance…" className="field resize-none !pr-14" /><button disabled={!input.trim() || loading} aria-label="Send question" className="absolute bottom-3 right-3 grid h-9 w-9 place-items-center rounded-md bg-gold text-ink transition hover:bg-[#d7bb82] disabled:cursor-not-allowed disabled:opacity-30"><Send size={16} /></button></div><div className="mt-2 flex justify-between text-[10px] text-slate-600"><span>Enter to submit · Shift + Enter for a new line</span><span>Verify outputs against official materials</span></div></form>
      </section>

      <aside className="hidden border-l border-line bg-panel/25 px-5 py-8 xl:block"><div className="eyebrow">Research context</div><dl className="mt-6 space-y-5 text-xs"><div><dt className="text-slate-600">Retrieval</dt><dd className="mt-1 text-slate-300">Dense + SPLADE hybrid</dd></div><div><dt className="text-slate-600">Corpus</dt><dd className="mt-1 text-slate-300">SEC crypto knowledge base</dd></div><div><dt className="text-slate-600">Session</dt><dd className="mt-1 truncate font-mono text-[10px] text-slate-400">{sessionId || "Created on first inquiry"}</dd></div></dl><div className="mt-8 border-t border-line pt-6"><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-slate-600">Review protocol</p><p className="mt-3 text-xs leading-6 text-slate-500">Open cited sources and confirm the governing text, date, authority level, and current status before relying on an answer.</p></div></aside>
    </div>
  );
}
