"use client";

import Link from "next/link";
import { NoteSummary } from "@/lib/api";

export default function NoteCard({ note }: { note: NoteSummary }) {
  return (
    <Link href={`/notes/${note.slug}`} className="block">
      <article className="border rounded-lg p-5 hover:shadow-md transition-shadow bg-white">
        <div className="flex items-center gap-2 mb-2">
          {note.category && (
            <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700">
              {note.category}
            </span>
          )}
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-1 line-clamp-2">
          {note.title}
        </h3>
        {note.excerpt && (
          <p className="text-sm text-gray-600 line-clamp-3">{note.excerpt}</p>
        )}
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
          <span>👁 {note.view_count}</span>
          {note.updated_at && (
            <span>{new Date(note.updated_at).toLocaleDateString("zh-CN")}</span>
          )}
        </div>
      </article>
    </Link>
  );
}
