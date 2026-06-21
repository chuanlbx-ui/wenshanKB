"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface DashboardData {
  total: number;
  drafts: number;
  stale: number;
  categories: number;
  broken_links: number;
  recent_updates: { title: string; slug: string; updated_at: string | null; view_count: number }[];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/admin/dashboard`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return null;

  return (
    <section className="mb-12">
      <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-5">📊 知识库概览</h2>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
        <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 text-center">
          <div className="text-2xl font-bold text-primary">{data.total}</div>
          <div className="text-xs text-gray-500 mt-1">笔记</div>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 text-center">
          <div className="text-2xl font-bold text-emerald-600">{data.categories}</div>
          <div className="text-xs text-gray-500 mt-1">分类</div>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 text-center">
          <div className={`text-2xl font-bold ${data.drafts > 0 ? "text-orange-500" : "text-gray-400"}`}>
            {data.drafts}
          </div>
          <div className="text-xs text-gray-500 mt-1">待审核</div>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 text-center">
          <div className={`text-2xl font-bold ${data.stale > 0 ? "text-red-500" : "text-gray-400"}`}>
            {data.stale}
          </div>
          <div className="text-xs text-gray-500 mt-1">过期</div>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 text-center">
          <div className={`text-2xl font-bold ${data.broken_links > 200 ? "text-yellow-500" : "text-green-600"}`}>
            {data.broken_links}
          </div>
          <div className="text-xs text-gray-500 mt-1">失效链接</div>
        </div>
      </div>

      {/* 最近更新 */}
      {data.recent_updates.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            最近更新
          </h3>
          <div className="space-y-2">
            {data.recent_updates.map((note) => (
              <Link
                key={note.slug}
                href={`/notes/${encodeURIComponent(note.slug)}`}
                className="flex items-center justify-between p-3 rounded-lg bg-white dark:bg-gray-800 border dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
              >
                <span className="text-sm text-gray-800 dark:text-gray-200 truncate flex-1 mr-4">
                  {note.title}
                </span>
                <span className="text-xs text-gray-400 shrink-0">
                  {note.updated_at
                    ? new Date(note.updated_at).toLocaleDateString("zh-CN")
                    : ""}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
