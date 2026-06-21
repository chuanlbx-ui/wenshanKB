"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/admin", label: "📊 总览", icon: "📊" },
  { href: "/admin/review", label: "📋 审核草稿", icon: "📋" },
  { href: "/admin/links", label: "🔗 失效链接", icon: "🔗" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex gap-6 min-h-[calc(100vh-4rem)]">
      {/* 侧边栏 */}
      <aside className="hidden sm:flex flex-col w-52 shrink-0 border-r dark:border-gray-700 pr-4">
        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 mt-2">
          管理后台
        </h2>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                pathname === item.href
                  ? "bg-primary/10 text-primary font-semibold"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* 移动端顶部导航 */}
      <nav className="sm:hidden flex gap-2 overflow-x-auto pb-2 mb-4 scrollbar-hide">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`shrink-0 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              pathname === item.href
                ? "bg-primary text-white"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {/* 内容区 */}
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
