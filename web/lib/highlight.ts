/** 关键词高亮 — 将一段文本中的匹配词包裹 <mark> 标签 */

export function highlightText(text: string, query: string): string {
  if (!query || !text) return text;

  // 拆分查询为单个词，去重
  const words = [...new Set(query.split(/[\s,，、]+/).filter(Boolean))];
  if (words.length === 0) return text;

  // 对所有词做正则匹配（转义特殊字符）
  const pattern = words
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|");

  const regex = new RegExp(`(${pattern})`, "gi");
  return text.replace(regex, "<mark class='bg-yellow-200 px-0.5 rounded'>$1</mark>");
}
