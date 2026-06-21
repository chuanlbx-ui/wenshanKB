"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import NoteCard from "@/components/NoteCard";
import CategoryNav from "@/components/CategoryNav";
import { fetchNotes, NoteSummary } from "@/lib/api";

export default function NotesPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const category = searchParams.get("category") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);

  const [notes, setNotes] = useState<NoteSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pagination, setPagination] = useState({ total: 0, page: 1, total_pages: 1 });

  useEffect(() => {
    setLoading(true);
    setError("");
    const params: Record<string, string> = { page: String(page) };
    if (category) params.category = category;
    fetchNotes(params)
      .then((data: any) => {
        if (data.error) {
          setError(data.error);
        } else {
          setNotes(data.notes);
          setPagination(data.pagination);
        }
      })
      .finally(() => setLoading(false));
  }, [category, page]);

  const goToPage = useCallback(
    (p: number) => {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      params.set("page", String(p));
      router.push(`/notes?${params.toString()}`);
    },
    [category, router],
  );

  const totalPages = pagination.total_pages;
  const pageNumbers: (number | string)[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pageNumbers.push(i);
  } else {
    pageNumbers.push(1);
    if (page > 3) pageNumbers.push("...");
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
      pageNumbers.push(i);
    }
    if (page < totalPages - 2) pageNumbers.push("...");
    pageNumbers.push(totalPages);
  }

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
        {category ? category.replace(/^\d{2}-/, "") : "全部笔记"}
      </h1>
      <p className="text-gray-500 dark:text-gray-400 dark:text-gray-500 mb-4">共 {pagination.total} 篇</p>

      <CategoryNav />

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="border rounded-lg p-5 bg-white dark:bg-gray-800 space-y-3">
              <div className="h-4 bg-gray-200 rounded w-1/4" />
              <div className="h-6 bg-gray-200 rounded w-3/4" />
              <div className="h-4 bg-gray-200 rounded w-full" />
              <div className="h-4 bg-gray-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-20">
          <p className="text-red-500 mb-2">⚠️ 无法连接到后端 API</p>
          <p className="text-gray-400 dark:text-gray-500 text-sm">{error}</p>
        </div>
      ) : notes.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-gray-500">暂无笔记</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {notes.map((note) => (
              <NoteCard key={note.id} note={note} />
            ))}
          </div>

          {totalPages > 1 && (
            <nav className="flex items-center justify-center gap-1 py-6">
              <button
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
                className="px-3 py-2 text-sm rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                ← 上一页
              </button>
              {pageNumbers.map((p, i) =>
                p === "..." ? (
                  <span key={`e-${i}`} className="px-2 text-gray-400 dark:text-gray-500">...</span>
                ) : (
                  <button
                    key={p}
                    onClick={() => goToPage(p as number)}
                    className={`w-9 h-9 text-sm rounded transition-colors ${
                      p === page
                        ? "bg-primary text-white"
                        : "border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700"
                    }`}
                  >
                    {p}
                  </button>
                ),
              )}
              <button
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
                className="px-3 py-2 text-sm rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                下一页 →
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
