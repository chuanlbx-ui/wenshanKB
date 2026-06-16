"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function Navbar() {
  const [dark, setDark] = useState(false);

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
        <Link href="/" className="text-xl font-bold text-primary">
          文山州知识库
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/notes" className="hover:text-primary dark:text-gray-300 dark:hover:text-primary transition-colors">
            全部笔记
          </Link>
          <Link href="/search" className="hover:text-primary dark:text-gray-300 dark:hover:text-primary transition-colors">
            搜索
          </Link>
          <button
            onClick={toggle}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-lg"
            title={dark ? "切换日间模式" : "切换夜间模式"}
          >
            {dark ? "☀️" : "🌙"}
          </button>
        </nav>
      </div>
    </header>
  );
}
