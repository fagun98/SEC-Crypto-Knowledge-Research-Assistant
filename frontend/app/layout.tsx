import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "SEC Crypto Knowledge Intelligence", template: "%s · SEC Crypto Intelligence" },
  description: "Source-grounded research across SEC cryptocurrency materials.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
