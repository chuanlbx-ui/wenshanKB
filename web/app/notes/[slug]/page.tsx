"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchNote } from "@/lib/api";

export default function NoteDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [note, setNote] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchNote(slug)
      .then(setNote)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="text-center py-20 text-gray-400">加载中...</div>;
  if (error) return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!note) return null;

  return (
    <article className="max-w-3xl mx-auto">
      {/* 分类标签 */}
      {note.category && (
        <span className="text-sm px-3 py-1 rounded-full bg-blue-50 text-blue-700">
          {note.category}
        </span>
      )}

      {/* 标题 */}
      <h1 className="text-3xl font-bold text-gray-900 mt-4 mb-2">{note.title}</h1>

      {/* 元信息 */}
      <div className="flex items-center gap-4 text-sm text-gray-400 mb-8">
        <span>👁 {note.view_count} 次浏览</span>
        {note.updated_at && (
          <span>更新于 {new Date(note.updated_at).toLocaleDateString("zh-CN")}</span>
        )}
      </div>

      {/* 正文 */}
      <div className="prose prose-lg max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {note.content || ""}
        </ReactMarkdown>
      </div>
    </article>
  );
}
