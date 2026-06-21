"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeHighlight from "rehype-highlight";
import TocSidebar from "@/components/TocSidebar";
import MobileToc from "@/components/MobileToc";
import { remarkHeadingIds } from "@/lib/remark-heading-ids";
import { fetchNote } from "@/lib/api";
import { renderWikilinks } from "@/lib/wikilink";
import { highlightText } from "@/lib/highlight";

const API = process.env.NEXT_PUBLIC_API_URL || "";

function rewriteImages(content: string, sourcePath?: string): string {
  if (!sourcePath) return content;
  const parts = sourcePath.replace(/\\/g, "/").split("/");
  const baseDir = parts.length > 1 ? parts.slice(0, -1).join("/") : "";
  return content.replace(/!\[([^\]]*)\]\(assets\//g, (_m, alt) => {
    return `![${alt}](${API}/static/${baseDir}/assets/`;
  });
}

export default function NoteDetailPage() {
  const { slug } = useParams<{ slug: string }>();

  // ── 所有 hooks 必须先声明（React 规则）──
  const [note, setNote] = useState<any>(null);
  const [related, setRelated] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [highlightQuery, setHighlightQuery] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // 从 URL 读取 ?hl= 参数（避免 useSearchParams 的 Suspense 限制）
    const params = new URLSearchParams(window.location.search);
    setHighlightQuery(params.get("hl") || "");
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchNote(slug),
      fetch(`${API}/api/v1/notes/${slug}/related`).then((r) =>
        r.json().then((d) => d.notes || []).catch(() => []),
      ),
    ])
      .then(([noteData, relatedData]) => {
        setNote(noteData);
        setRelated(relatedData);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  // 预处理正文（所有 hooks 之后、条件返回之前）
  const processedContent = useMemo(() => {
    if (!note) return "";
    let content = note.content || "";
    content = renderWikilinks(content);
    content = rewriteImages(content, note.source_path);
    if (highlightQuery) {
      content = highlightText(content, highlightQuery);
    }
    return content;
  }, [note?.content, note?.source_path, highlightQuery]);

  // ── 条件返回 ──
  if (loading)
    return (
      <div className="max-w-3xl mx-auto px-1 animate-pulse space-y-4 py-10">
        <div className="h-4 bg-gray-200 rounded w-1/4" />
        <div className="h-8 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/3" />
        <div className="h-40 bg-gray-200 rounded" />
        <div className="h-40 bg-gray-200 rounded" />
      </div>
    );

  if (error) return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!note) return null;

  const tags: string[] = [];
  if (note.frontmatter?.tags) {
    const raw = note.frontmatter.tags;
    tags.push(...(Array.isArray(raw) ? raw : [raw]));
  }
  const confidence = note.frontmatter?.confidence;

  return (
    <article className="max-w-3xl mx-auto px-1">
      <nav className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500 mb-4">
        <Link href="/" className="hover:text-primary">首页</Link>
        <span>/</span>
        {note.category ? (
          <>
            <Link href={`/notes?category=${encodeURIComponent(note.category)}`} className="hover:text-primary">{note.category}</Link>
            <span>/</span>
          </>
        ) : null}
        <span className="text-gray-600 dark:text-gray-400 dark:text-gray-500 truncate max-w-[200px]">{note.title}</span>
      </nav>

      {note.category && (
        <Link href={`/notes?category=${encodeURIComponent(note.category)}`}
          className="inline-block text-sm px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 transition-colors"
        >{note.category}</Link>
      )}

      <div className="flex items-start justify-between gap-4 mt-3 mb-2"><h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100 flex-1">{note.title}</h1><button onClick={async () => { await navigator.clipboard.writeText(window.location.href); setCopied(true); setTimeout(() => setCopied(false), 2000); }} className="shrink-0 px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors mt-1">{copied ? "✅ 已复制" : "🔗 分享"}</button></div>

      <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400 dark:text-gray-500 mb-4">
        <span>👁 {note.view_count} 次浏览</span>
        {note.updated_at && <span>更新于 {new Date(note.updated_at).toLocaleDateString("zh-CN")}</span>}
        {confidence && (
          <span className={`px-2 py-0.5 rounded text-xs ${
            confidence === "高" ? "bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400" :
            confidence === "中" ? "bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400" :
            "bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 dark:text-gray-500"
          }`}>可信度: {confidence}</span>
        )}
        {note.source_path && (
          <span className="text-xs text-gray-400 dark:text-gray-500">源文件: {note.source_path.replace(/\\/g, "/")}</span>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {tags.map((tag) => (
            <span key={tag} className="text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 dark:text-gray-500">#{tag}</span>
          ))}
        </div>
      )}

      <div className="prose prose-lg max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkHeadingIds]} rehypePlugins={[rehypeRaw, rehypeHighlight]}>{processedContent}</ReactMarkdown>
      </div>

      {note.frontmatter?.sources && Array.isArray(note.frontmatter.sources) && note.frontmatter.sources.length > 0 && (
        <section className="mt-12 pt-8 border-t dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">📚 数据来源</h2>
          <ul className="space-y-1">
            {note.frontmatter.sources.map((s: string, i: number) => (
              <li key={i} className="text-sm text-gray-500 dark:text-gray-400">
                {s.startsWith('http') ? (
                  <a href={s} target="_blank" rel="noopener" className="text-blue-500 hover:underline break-all">{s}</a>
                ) : (
                  <span>{s}</span>
                )}
              </li>
            ))}
          </ul>
          {note.created_at && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
              创建于 {new Date(note.created_at).toLocaleDateString("zh-CN")}
            </p>
          )}
        </section>
      )}

      {related.length > 0 && (
        <section className="mt-16 pt-8 border-t">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">📎 相关笔记</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {related.map((r: any) => (
              <Link key={r.id} href={`/notes/${encodeURIComponent(r.slug)}`}
                className="block p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm transition-all"
              >
                {r.category && <span className="text-xs text-blue-600">{r.category}</span>}
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mt-1">{r.title}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      <div className="text-center mt-12">
        <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:text-gray-400 dark:text-gray-500 transition-colors"
        >↑ 返回顶部</button>
      </div>
    </article>
  );
}
