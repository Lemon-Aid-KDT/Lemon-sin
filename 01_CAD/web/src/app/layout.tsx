import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";
import TopNav from "@/components/layout/TopNav";
import Sidebar from "@/components/layout/Sidebar";
import StatusFooter from "@/components/layout/StatusFooter";

export const metadata: Metadata = {
  title: "CAD Vision — AI Drawing Search System",
  description:
    "Engineering Drawing Retrieval & Classification powered by Open-Source Multimodal LLM",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full bg-background text-text-primary font-body">
        <Providers>
          <TopNav />
          <Sidebar />
          <main className="ml-64 pt-16 pb-8 min-h-screen">
            <div className="p-6">{children}</div>
          </main>
          <StatusFooter />
        </Providers>
      </body>
    </html>
  );
}
