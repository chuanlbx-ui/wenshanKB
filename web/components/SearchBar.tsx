"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { CATEGORIES } from "@/lib/api";

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    const params = new URLSearchParams();
    params.set("q", query.trim());
    if (category) params.set("cat", category);
    router.push(`/search?${params.toString()}`);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      {/* 桌面端：水平排列 */}
      <div className="hidden sm:flex gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-4 py-3.5 rounded-full border border-gray-200 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary appearance-none cursor-pointer shrink-0"
        >
          {CATEGORIES.map((c) => (
            <option key={c.name} value={c.name}>{c.label}</option>
          ))}
        </select>
        <div className="relative flex-1">
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索文山州知识库…"
            className="w-full px-5 py-3.5 rounded-full border border-gray-200 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 shadow-sm text-lg focus:outline-none focus:ring-2 focus:ring-primary" />
          <button type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 bg-primary text-white rounded-full hover:bg-blue-700 transition-colors text-sm">搜索</button>
        </div>
      </div>

      {/* 移动端：垂直堆叠 */}
      <div className="sm:hidden space-y-3">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {CATEGORIES.map((c) => (
            <option key={c.name} value={c.name}>{c.label}</option>
          ))}
        </select>
        <div className="relative">
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索文山州知识库…"
            className="w-full px-5 py-3 rounded-xl border border-gray-200 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 text-base focus:outline-none focus:ring-2 focus:ring-primary" />
          <button type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 px-4 py-1.5 bg-primary text-white rounded-lg hover:bg-blue-700 text-sm">搜索</button>
        </div>
      </div>
    </form>
  );
}
