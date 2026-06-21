/**
 * wikilink 预处理
 * 将 Markdown 中的 [[目标]] 和 [[目标|别名]] 转为站内链接
 */

/**
 * wikilink 预处理
 * 将 Markdown 中的 [[目标]] 和 [[目标|别名]] 转为站内链接
 *
 * slugify 规范：
 *   - 文件名/路径中的 _（下划线） → -（短横）统一（和数据库 slugify 逻辑一致）
 *   - 去掉 .md 后缀
 *   - 取路径最后一段
 */
export function renderWikilinks(markdown: string): string {
  return markdown.replace(
    /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g,
    (_match: string, target: string, alias?: string) => {
      const text = alias || target;
      // 清理路径：../xxx/笔记名 → 笔记名，去掉 .md 后缀和 # 锚点
      let slug = target
        .replace(/^(\.\.\/)+/g, "")
        .replace(/\.md$/i, "")
        .split("#")[0]
        .split("|")[0]
        .split("/").pop()!  // 取最后一段，去掉目录前缀
        .trim();
      // 统一：下划线 → 短横（和数据库 slugify 逻辑一致）
      slug = slug.replace(/_/g, "-");
      return `[${text}](/notes/${encodeURIComponent(slug)})`;
    },
  );
}
