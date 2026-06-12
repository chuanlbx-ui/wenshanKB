"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import NoteCard from "@/components/NoteCard";
import SearchBar from "@/components/SearchBar";
import { searchNotes, NoteSummary } from "@/lib/api";

export default function SearchPage() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (!query) return;
    setLoading(true);
    setSearched(true);
    searchNotes(query)
      .then((data) => setResults(data.results || []))
      .finally(() => setLoading(false));
  }, [query]);

  return (
    <div>
      <div className="mb-8">
        <SearchBar />
      </div>

      {loading && <div className="text-center py-12 text-gray-400">搜索中...</div>}

      {searched && !loading && (
        <>
          <p className="text-gray-500 mb-4">
            搜索 &quot;{query}&quot; — 找到 {results.length} 条结果
          </p>
          {results.length === 0 ? (
            <div className="text-center py-20 text-gray-400">
              未找到相关笔记，尝试其他关键词
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {results.map((r: any) => (
                <NoteCard key={r.note.id} note={r.note} />
              ))}
            </div>
          )}
        </>
      )}

      {!searched && (
        <div className="text-center py-20 text-gray-400">
          输入关键词搜索文山州知识库
        </div>
      )}
    </div>
  );
}
