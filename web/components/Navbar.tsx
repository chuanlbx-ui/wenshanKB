"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function Navbar() {
  const [dark, setDark] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  return (
    <header className="border-b bg-white dark:bg-gray-800 dark:border-gray-700 sticky top-0 z-50 transition-colors">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="text-lg sm:text-xl font-bold text-primary shrink-0">
          文山州知识库
        </Link>

        {/* 桌面端导航 */}
        <nav className="hidden sm:flex items-center gap-6 text-sm">
          <Link href="/notes" className="hover:text-primary dark:text-gray-300 dark:hover:text-primary transition-colors">全部笔记</Link>
          <Link href="/search" className="hover:text-primary dark:text-gray-300 dark:hover:text-primary transition-colors">搜索</Link>
          <Link href="/knowledge-graph" className="hover:text-primary dark:text-gray-300 dark:hover:text-primary transition-colors">图谱</Link>
          <button onClick={toggle} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-lg"
            title={dark ? "切换日间模式" : "切换夜间模式"}>{dark ? "☀️" : "🌙"}</button>
        </nav>

        {/* 移动端汉堡菜单 */}
        <div className="flex sm:hidden items-center gap-2">
          <button onClick={toggle} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-lg">
            {dark ? "☀️" : "🌙"}
          </button>
          <button onClick={() => setMenuOpen(!menuOpen)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>
      </div>

      {/* 移动端下拉菜单 */}
      {menuOpen && (
        <nav className="sm:hidden border-t dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 space-y-2">
          <Link href="/notes" onClick={() => setMenuOpen(false)}
            className="block px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-sm">全部笔记</Link>
          <Link href="/search" onClick={() => setMenuOpen(false)}
            className="block px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-sm">搜索</Link>
          <Link href="/knowledge-graph" className="hover:text-primary dark:text-gray-300 dark:hover:text-primary transition-colors">图谱</Link>
        </nav>
      )}
    </header>
  );
}
