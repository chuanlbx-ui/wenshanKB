"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
}> {
  const url = new URL(`${API}/api/v1/notes`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString());
  return res.json();
}

export async function fetchNote(slug: string): Promise<any> {
  const res = await fetch(`${API}/api/v1/notes/${slug}`);
  if (!res.ok) throw new Error("笔记不存在");
  return res.json();
}

export async function searchNotes(query: string): Promise<any> {
  const res = await fetch(`${API}/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, page_size: 20 }),
  });
  return res.json();
}
