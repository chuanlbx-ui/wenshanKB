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
  recent_updates: { title: string; slug: string; updated_at: string; view_count: number }[];
}

export default function AdminDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/admin/dashboard`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-2">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-2">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">📊 管理总览</h1>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <div className="rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-blue-600">{data?.total ?? "—"}</div>
          <div className="text-sm text-gray-500 mt-1">已发布笔记</div>
        </div>
        <Link href="/admin/review" className="block">
          <div className="rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 p-4 hover:shadow-md transition-shadow">
            <div className="text-2xl font-bold text-amber-600">{data?.drafts ?? "—"}</div>
            <div className="text-sm text-gray-500 mt-1">待审核草稿</div>
          </div>
        </Link>
        <div className="rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-red-500">{data?.broken_links ?? "—"}</div>
          <div className="text-sm text-gray-500 mt-1">失效链接</div>
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-green-600">{data?.categories ?? "—"}</div>
          <div className="text-sm text-gray-500 mt-1">分类数</div>
        </div>
      </div>

      {/* 最近更新 */}
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">最近更新</h2>
      <div className="space-y-2">
        {(data?.recent_updates ?? []).map((note) => (
          <Link key={note.slug} href={`/notes/${note.slug}`}
            className="block p-3 rounded-lg bg-white dark:bg-gray-800 border dark:border-gray-700 hover:shadow-sm transition-shadow">
            <div className="flex justify-between items-center">
              <span className="font-medium text-gray-900 dark:text-gray-100">{note.title}</span>
              <span className="text-xs text-gray-400">{note.view_count} 次浏览</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {note.updated_at ? new Date(note.updated_at).toLocaleString("zh-CN") : ""}
            </div>
          </Link>
        ))}
        {(!data?.recent_updates || data.recent_updates.length === 0) && (
          <p className="text-gray-400 text-sm">暂无数据</p>
        )}
      </div>
    </div>
  );
}
