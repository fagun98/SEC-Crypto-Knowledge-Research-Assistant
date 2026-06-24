"use client";

import { useState } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="lg:pl-72">
        <TopBar onMenu={() => setOpen(true)} />
        <main>{children}</main>
        <footer className="border-t border-line/60 px-6 py-8 text-center text-[11px] leading-5 text-slate-600">
          <span className="text-slate-500">SEC Crypto Knowledge Intelligence · Internal Research Interface</span><br />
          This assistant is intended for research support only. Outputs should be reviewed against official SEC materials before use in policy, legal, compliance, or enforcement decisions.
        </footer>
      </div>
    </div>
  );
}
