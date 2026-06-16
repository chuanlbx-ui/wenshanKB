/**
 * wikilink 预处理
 * 将 Markdown 中的 [[目标]] 和 [[目标|别名]] 转为站内链接
 */

export function renderWikilinks(markdown: string): string {
  return markdown.replace(
    /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g,
    (_match: string, target: string, alias?: string) => {
      const text = alias || target;
      // 清理路径：../xxx/笔记名 → 笔记名，去掉 .md 后缀和 # 锚点
      // 也处理 06-文化旅游/砚山康养 → 砚山康养
      const slug = target
        .replace(/^(\.\.\/)+/g, "")
        .replace(/\.md$/, "")
        .split("#")[0]
        .split("|")[0]
        .split("/").pop()!  // 取最后一段，去掉目录前缀
        .trim();
      return `[${text}](/notes/${encodeURIComponent(slug)})`;
    },
  );
}
