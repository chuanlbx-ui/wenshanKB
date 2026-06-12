import Link from "next/link";

export default function Navbar() {
  return (
    <header className="border-b bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-primary">
          文山州知识库
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/notes" className="hover:text-primary">
            全部笔记
          </Link>
          <Link href="/search" className="hover:text-primary">
            搜索
          </Link>
        </nav>
      </div>
    </header>
  );
}
