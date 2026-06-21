"use client";

// 本地开发用 localhost:8000，生产环境用相对路径（Nginx 代理 /api/）
const API = process.env.NEXT_PUBLIC_API_URL || "";

export interface NoteSummary {
  id: string;
  title: string;
  slug: string;
  category: string | null;
  status: string;
  excerpt: string | null;
  view_count: number;
  updated_at: string | null;
}

export async function fetchNotes(params?: Record<string, string>): Promise<{
  notes: NoteSummary[];
  pagination: { total: number; page: number; total_pages: number };
  error?: string;
}> {
  try {
    let urlStr = `${API}/api/v1/notes`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      urlStr += `?${searchParams.toString()}`;
    }
    const res = await fetch(urlStr);
    if (!res.ok) return { notes: [], pagination: { total: 0, page: 1, total_pages: 0 } };
    return res.json();
  } catch (e: any) {
    return { notes: [], pagination: { total: 0, page: 1, total_pages: 0 }, error: e.message };
  }
}

export async function fetchNote(slug: string): Promise<any> {
  const res = await fetch(`${API}/api/v1/notes/${slug}`);
  if (!res.ok) throw new Error("笔记不存在");
  return res.json();
}

export async function searchNotes(query: string, category?: string): Promise<any> {
  const body: any = { query, page_size: 20 };
  if (category) body.category = category;
  const res = await fetch(`${API}/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

// 分类列表
export const CATEGORIES = [
  { name: "", label: "全部分类" },
  { name: "00-总览", label: "总览" },
  { name: "01-地理与自然环境", label: "地理" },
  { name: "02-历史沿革", label: "历史" },
  { name: "03-行政区划", label: "区划" },
  { name: "04-人口与民族", label: "民族" },
  { name: "05-经济发展", label: "经济" },
  { name: "06-文化旅游", label: "文旅" },
  { name: "07-特产与资源", label: "特产" },
  { name: "08-交通与基础设施", label: "交通" },
  { name: "09-政策与治理", label: "政策" },
  { name: "10-社会民生", label: "民生" },
];
