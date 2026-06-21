"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface Draft {
  slug: string;
  title: string;
  summary: string;
  source_url: string;
  created_at: string;
  content_preview: string;
}

export default function AdminReviewPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const fetchDrafts = () => {
    setLoading(true);
    fetch(`${API}/api/v1/admin/drafts`)
      .then((r) => r.json())
      .then((d) => setDrafts(d.drafts || []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDrafts(); }, []);

  const handleReview = async (slug: string, action: "approve" | "reject") => {
    const res = await fetch(`${API}/api/v1/admin/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug, action }),
    });
    if (res.ok) {
      setMessage(`${action === "approve" ? "✅ 已发布" : "🗑️ 已驳回"}: ${slug}`);
      setDrafts((prev) => prev.filter((d) => d.slug !== slug));
    } else {
      setMessage("操作失败，请重试");
    }
    setTimeout(() => setMessage(""), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto px-2">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">📋 采集草稿审核</h1>
        <Link href="/" className="text-sm text-gray-500 hover:text-primary">← 返回首页</Link>
      </div>

      {message && (
        <div className="mb-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-sm text-blue-700 dark:text-blue-300">
          {message}
        </div>
      )}

      {loading ? (
        <div className="space-y-4 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      ) : drafts.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-gray-500">
          🎉 没有待审核的草稿
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <div key={draft.slug}
              className="border dark:border-gray-700 rounded-lg p-5 bg-white dark:bg-gray-800">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">{draft.title}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{draft.summary}</p>
                  {draft.source_url && (
                    <a href={draft.source_url} target="_blank" rel="noopener"
                      className="text-xs text-blue-500 hover:underline break-all">
                      来源: {draft.source_url}
                    </a>
                  )}
                  <div className="mt-3 p-3 rounded bg-gray-50 dark:bg-gray-900 text-sm text-gray-600 dark:text-gray-400 max-h-32 overflow-y-auto">
                    {draft.content_preview}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 mt-4 pt-3 border-t dark:border-gray-700">
                <button onClick={() => handleReview(draft.slug, "approve")}
                  className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors">
                  ✅ 发布
                </button>
                <button onClick={() => handleReview(draft.slug, "reject")}
                  className="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors">
                  🗑️ 驳回
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
