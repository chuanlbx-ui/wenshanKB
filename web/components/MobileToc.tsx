"use client";

import { useState } from "react";
import { extractToc } from "@/components/TocSidebar";

export default function MobileToc({ content }: { content: string }) {
  const toc = extractToc(content);
  const [open, setOpen] = useState(false);

  if (toc.length < 3) return null;

  return (
    <>
      {/* 浮动按钮 — 仅移动端显示 */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-4 xl:hidden z-40 w-12 h-12 rounded-full bg-primary text-white shadow-lg flex items-center justify-center text-lg"
      >
        ☰
      </button>

      {/* 目录弹窗 */}
      {open && (
        <div className="fixed inset-0 z-50 xl:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <div className="absolute bottom-0 left-0 right-0 bg-white dark:bg-gray-800 rounded-t-2xl max-h-[70vh] overflow-y-auto p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">📑 目录</h3>
              <button onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-lg">✕</button>
            </div>
            <ul className="space-y-2">
              {toc.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    onClick={() => setOpen(false)}
                    style={{ paddingLeft: `${(item.level - 2) * 12}px` }}
                    className="block text-sm text-gray-600 dark:text-gray-400 hover:text-primary dark:hover:text-primary py-1"
                  >
                    {item.text}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </>
  );
}
