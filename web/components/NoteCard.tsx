"use client";

import Link from "next/link";
import { NoteSummary } from "@/lib/api";
import { highlightText } from "@/lib/highlight";

export default function NoteCard({
  note,
  highlight,
}: {
  note: NoteSummary;
  highlight?: string;
}) {
  const noteUrl = highlight
    ? `/notes/${encodeURIComponent(note.slug)}?hl=${encodeURIComponent(highlight)}`
    : `/notes/${encodeURIComponent(note.slug)}`;

  return (
    <Link href={noteUrl} className="block">
      <article className="border rounded-lg p-5 hover:shadow-md transition-shadow bg-white dark:bg-gray-800 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          {note.category && (
            <span className="text-xs px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
              {note.category}
            </span>
          )}
        </div>
        <h3
          className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1 line-clamp-2"
          dangerouslySetInnerHTML={{
            __html: highlight ? highlightText(note.title, highlight) : note.title,
          }}
        />
        {note.excerpt && (
          <p
            className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3"
            dangerouslySetInnerHTML={{
              __html: highlight ? highlightText(note.excerpt, highlight) : note.excerpt,
            }}
          />
        )}
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-400 dark:text-gray-500">
          <span>👁 {note.view_count}</span>
          {note.updated_at && (
            <span>{new Date(note.updated_at).toLocaleDateString("zh-CN")}</span>
          )}
        </div>
      </article>
    </Link>
  );
}
