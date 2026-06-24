"use client";

import { Check, Copy, Landmark, UserRound } from "lucide-react";
import { useMemo, useState } from "react";
import type { Source } from "@/lib/types";
import SourceCard from "./SourceCard";

export type ChatMessage = { id: string; role: "user" | "assistant"; content: string; sources?: Source[]; metadata?: Record<string, unknown> };

function sanitizeAssistantHtml(html: string) {
  if (typeof window === "undefined") return html;
  const document = new DOMParser().parseFromString(html, "text/html");
  document.querySelectorAll("script, style, iframe, object, embed, form, input, button").forEach((node) => node.remove());
  document.querySelectorAll("*").forEach((node) => {
    for (const attribute of Array.from(node.attributes)) {
      if (attribute.name.toLowerCase().startsWith("on")) node.removeAttribute(attribute.name);
    }
    if (node instanceof HTMLAnchorElement) {
      const href = node.getAttribute("href") || "";
      if (!/^https?:\/\//i.test(href)) node.removeAttribute("href");
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noreferrer");
    }
  });
  return document.body.innerHTML;
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false);
  const assistant = message.role === "assistant";
  const safeContent = useMemo(() => assistant ? sanitizeAssistantHtml(message.content) : message.content, [assistant, message.content]);
  async function copy() {
    const text = new DOMParser().parseFromString(message.content, "text/html").body.textContent || message.content;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <article className={`flex gap-3 ${assistant ? "" : "justify-end"}`}>
      {assistant && <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-md border border-gold/25 bg-gold/[.07] text-gold"><Landmark size={15} /></div>}
      <div className={`max-w-3xl ${assistant ? "w-full" : "rounded-lg border border-slate-600/60 bg-slate-800/70 px-5 py-3.5"}`}>
        {assistant ? (
          <div className="panel rounded-lg p-5 sm:p-7"><div className="answer-html" dangerouslySetInnerHTML={{ __html: safeContent }} /><div className="mt-5 flex items-center justify-between border-t border-line/60 pt-4"><span className="text-[10px] uppercase tracking-[.17em] text-slate-600">AI research synthesis</span><button onClick={copy} className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-slate-200">{copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "Copied" : "Copy answer"}</button></div></div>
        ) : <p className="text-sm leading-6 text-slate-100">{message.content}</p>}
        {assistant && message.sources && message.sources.length > 0 && <div className="mt-4"><div className="mb-2 text-[10px] font-semibold uppercase tracking-[.18em] text-slate-600">Supporting sources · {message.sources.length}</div><div className="grid gap-2 sm:grid-cols-2">{message.sources.map((source, index) => <SourceCard key={`${source.url}-${index}`} source={source} index={index} />)}</div></div>}
      </div>
      {!assistant && <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-md border border-slate-700 bg-slate-800 text-slate-400"><UserRound size={15} /></div>}
    </article>
  );
}
