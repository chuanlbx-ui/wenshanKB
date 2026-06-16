import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import ThemeScript from "@/components/ThemeScript";

export const metadata: Metadata = {
  title: "文山州知识库",
  description: "文山壮族苗族自治州综合性知识库",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="bg-gray-50 dark:bg-gray-900 min-h-screen text-gray-900 dark:text-gray-100 transition-colors">
        <Navbar />
        <main className="max-w-6xl mx-auto px-3 sm:px-4 py-6 sm:py-8">{children}</main>
      </body>
    </html>
  );
}
