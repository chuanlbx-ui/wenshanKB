"use client";

import { useState, useEffect } from "react";

interface TocItem {
  id: string;
  text: string;
  level: number;
}

/** 从 Markdown 内容提取标题生成目录 */
export function extractToc(markdown: string): TocItem[] {
  const items: TocItem[] = [];
  const headingRegex = /^(#{2,4})\s+(.+)$/gm;
  let match;
  while ((match = headingRegex.exec(markdown)) !== null) {
    const level = match[1].length;
    const text = match[2].trim();
    const id = text
      .replace(/[^\u4e00-\u9fa5a-zA-Z0-9]+/g, "-")
      .replace(/-+$/, "")
      .toLowerCase();
    items.push({ id, text, level });
  }
  return items;
}

export default function TocSidebar({ content }: { content: string }) {
  const toc = extractToc(content);
  const [activeId, setActiveId] = useState("");

  useEffect(() => {
    if (toc.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: "-80px 0px -80% 0px" },
    );

    toc.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [toc]);

  if (toc.length < 3) return null;

  return (
    <nav className="hidden xl:block fixed right-[max(16px,calc((100vw-72rem)/2-240px))] top-24 w-48 max-h-[70vh] overflow-y-auto">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        目录
      </h4>
      <ul className="space-y-1 border-l-2 border-gray-100">
        {toc.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              style={{ paddingLeft: `${(item.level - 2) * 12}px` }}
              className={`block text-xs py-1 border-l-2 -ml-0.5 transition-colors ${
                activeId === item.id
                  ? "border-primary text-primary font-medium"
                  : "border-transparent text-gray-500 hover:text-gray-800"
              }`}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
