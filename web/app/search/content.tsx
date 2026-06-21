"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import NoteCard from "@/components/NoteCard";
import SearchBar from "@/components/SearchBar";
import { searchNotes, CATEGORIES } from "@/lib/api";

export default function SearchPageContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const catParam = searchParams.get("cat") || "";
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const catLabel = CATEGORIES.find((c) => c.name === catParam)?.label || "";

  useEffect(() => {
    if (!query) return;
    setLoading(true);
    setSearched(true);
    searchNotes(query, catParam || undefined)
      .then((data) => setResults(data.results || []))
      .finally(() => setLoading(false));
  }, [query, catParam]);

  return (
    <div>
      <div className="mb-8">
        <SearchBar />
      </div>

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="border rounded-lg p-5 bg-white dark:bg-gray-800 space-y-3">
              <div className="h-4 bg-gray-200 rounded w-1/4" />
              <div className="h-6 bg-gray-200 rounded w-3/4" />
              <div className="h-4 bg-gray-200 rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {searched && !loading && (
        <>
          <p className="text-gray-500 dark:text-gray-400 dark:text-gray-500 mb-4">
            搜索 &quot;{query}&quot;
            {catLabel && <span>（{catLabel}）</span>}
            — 找到 {results.length} 条结果
          </p>
          {results.length === 0 ? (
            <div className="text-center py-20 text-gray-400 dark:text-gray-500">
              未找到相关笔记，尝试其他关键词
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {results.map((r: any) => (
                <NoteCard key={r.note.id} note={r.note} highlight={query} />
              ))}
            </div>
          )}
        </>
      )}

      {!searched && (
        <div className="text-center py-20 text-gray-400 dark:text-gray-500">
          输入关键词搜索文山州知识库
        </div>
      )}
    </div>
  );
}
