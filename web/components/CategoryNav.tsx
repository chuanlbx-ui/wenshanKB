"use client";

import Link from "next/link";

const categories = [
  { name: "00-总览", label: "总览", slug: "00-总览" },
  { name: "01-地理与自然环境", label: "地理", slug: "01-地理与自然环境" },
  { name: "02-历史沿革", label: "历史", slug: "02-历史沿革" },
  { name: "03-行政区划", label: "区划", slug: "03-行政区划" },
  { name: "04-人口与民族", label: "民族", slug: "04-人口与民族" },
  { name: "05-经济发展", label: "经济", slug: "05-经济发展" },
  { name: "06-文化旅游", label: "文旅", slug: "06-文化旅游" },
  { name: "07-特产与资源", label: "特产", slug: "07-特产与资源" },
  { name: "08-交通与基础设施", label: "交通", slug: "08-交通与基础设施" },
  { name: "09-政策与治理", label: "政策", slug: "09-政策与治理" },
  { name: "10-社会民生", label: "民生", slug: "10-社会民生" },
];

export default function CategoryNav() {
  return (
    <nav className="flex flex-wrap gap-2 py-4">
      {categories.map((cat) => (
        <Link
          key={cat.slug}
          href={`/notes?category=${cat.slug}`}
          className="px-3 py-1.5 rounded-full text-sm bg-gray-100 hover:bg-primary hover:text-white transition-colors"
        >
          {cat.label}
        </Link>
      ))}
    </nav>
  );
}
