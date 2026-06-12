"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import NoteCard from "@/components/NoteCard";
import CategoryNav from "@/components/CategoryNav";
import { fetchNotes, NoteSummary } from "@/lib/api";

export default function NotesPage() {
  const searchParams = useSearchParams();
  const category = searchParams.get("category") || "";
  const [notes, setNotes] = useState<NoteSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({ total: 0, page: 1, total_pages: 1 });

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (category) params.category = category;
    fetchNotes(params)
      .then((data) => {
        setNotes(data.notes);
        setPagination(data.pagination);
      })
      .finally(() => setLoading(false));
  }, [category]);

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {category ? category.replace(/^\d{2}-/, "") : "全部笔记"}
      </h1>
      <p className="text-gray-500 mb-4">共 {pagination.total} 篇</p>

      <CategoryNav />

      {loading ? (
        <div className="text-center py-20 text-gray-400">加载中...</div>
      ) : notes.length === 0 ? (
        <div className="text-center py-20 text-gray-400">暂无笔记</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {notes.map((note) => (
            <NoteCard key={note.id} note={note} />
          ))}
        </div>
      )}
    </div>
  );
}
