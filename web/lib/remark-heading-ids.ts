/** remark 插件：为 Markdown 标题添加 id 属性 */

import { visit } from "unist-util-visit";

export function remarkHeadingIds() {
  return (tree: any) => {
    visit(tree, "heading", (node: any) => {
      if (node.depth >= 2 && node.depth <= 4) {
        const text = node.children
          .filter((c: any) => c.type === "text")
          .map((c: any) => c.value)
          .join("");
        const id = text
          .replace(/[^\u4e00-\u9fa5a-zA-Z0-9]+/g, "-")
          .replace(/-+$/, "")
          .toLowerCase();

        if (!node.data) node.data = {};
        if (!node.data.hProperties) node.data.hProperties = {};
        node.data.hProperties.id = id;
      }
    });
  };
}
