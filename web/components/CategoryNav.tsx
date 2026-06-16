"use client";

import Link from "next/link";

const categories = [
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

export default function CategoryNav() {
  return (
    <nav className="flex gap-2 py-3 overflow-x-auto scrollbar-hide -mx-4 px-4 sm:flex-wrap sm:overflow-visible sm:mx-0 sm:px-0">
      {categories.map((cat) => (
        <Link
          key={cat.name}
          href={`/notes?category=${cat.name}`}
          className="px-3 py-1.5 rounded-full text-sm bg-gray-100 dark:bg-gray-700 dark:text-gray-300 hover:bg-primary hover:text-white dark:hover:bg-primary dark:hover:text-white transition-colors whitespace-nowrap shrink-0"
        >
          {cat.label}
        </Link>
      ))}
    </nav>
  );
}
