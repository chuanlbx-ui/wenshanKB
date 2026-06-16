"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

const API = "http://localhost:8000";

interface GraphNode {
  id: string;
  title: string;
  category: string;
  views: number;
  links: number;
}
interface GraphEdge {
  source: string;
  target: string;
}

export default function KnowledgeGraphPage() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [data, setData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/admin/graph`)
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const svg = svgRef.current;
    svg.innerHTML = "";
    const w = svg.clientWidth || 900;
    const h = 600;

    // 简单力导向布局（手动实现，无外部依赖）
    const nodes = data.nodes.map((n) => ({
      ...n,
      x: Math.random() * w,
      y: Math.random() * h,
      vx: 0,
      vy: 0,
    }));
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const edges = data.edges
      .map((e) => ({ source: nodeMap.get(e.source), target: nodeMap.get(e.target) }))
      .filter((e) => e.source && e.target);

    // 类别颜色
    const catColors: Record<string, string> = {
      "经济发展": "#2563eb", "文化旅游": "#059669", "人口与民族": "#7c3aed",
      "地理与自然环境": "#0891b2", "特产与资源": "#d97706", "交通与基础设施": "#dc2626",
      "政策与治理": "#4f46e5", "社会民生": "#db2777", "历史沿革": "#9333ea",
      "行政区划": "#0d9488", "总览": "#6b7280",
    };

    // 模拟力导向迭代
    for (let iter = 0; iter < 80; iter++) {
      // 斥力
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const d = Math.max(1, Math.sqrt(dx * dx + dy * dy));
          const f = 500 / (d * d);
          nodes[i].vx -= (dx / d) * f;
          nodes[i].vy -= (dy / d) * f;
          nodes[j].vx += (dx / d) * f;
          nodes[j].vy += (dy / d) * f;
        }
      }
      // 引力（边）
      for (const e of edges) {
        if (!e.source || !e.target) continue;
        const dx = e.target.x - e.source.x;
        const dy = e.target.y - e.source.y;
        const d = Math.max(1, Math.sqrt(dx * dx + dy * dy));
        const f = (d - 120) * 0.01;
        e.source.vx += (dx / d) * f;
        e.source.vy += (dy / d) * f;
        e.target.vx -= (dx / d) * f;
        e.target.vy -= (dy / d) * f;
      }
      // 中心引力
      for (const n of nodes) {
        n.vx += (w / 2 - n.x) * 0.001;
        n.vy += (h / 2 - n.y) * 0.001;
        n.vx *= 0.85;
        n.vy *= 0.85;
        n.x += n.vx;
        n.y += n.vy;
      }
    }

    // 绘制边
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    for (const e of edges) {
      if (!e.source || !e.target) continue;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", String(e.source.x));
      line.setAttribute("y1", String(e.source.y));
      line.setAttribute("x2", String(e.target.x));
      line.setAttribute("y2", String(e.target.y));
      line.setAttribute("stroke", "#e5e7eb");
      line.setAttribute("stroke-width", "0.5");
      g.appendChild(line);
    }

    // 绘制节点
    for (const n of nodes) {
      const r = Math.max(4, Math.min(15, n.links * 2 + 4));
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", String(n.x));
      circle.setAttribute("cy", String(n.y));
      circle.setAttribute("r", String(r));
      circle.setAttribute("fill", catColors[n.category] || "#9ca3af");
      circle.setAttribute("opacity", "0.8");
      circle.setAttribute("cursor", "pointer");

      circle.addEventListener("mouseenter", (ev) => {
        setTooltip({ x: n.x, y: n.y - r - 10, node: n });
      });
      circle.addEventListener("mouseleave", () => setTooltip(null));
      circle.addEventListener("click", () => {
        window.open(`/notes/${encodeURIComponent(n.id)}`, "_blank");
      });

      g.appendChild(circle);
    }

    svg.appendChild(g);
  }, [data]);

  if (loading) return <div className="text-center py-20 text-gray-400">加载中...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">🕸️ 知识图谱</h1>
        <Link href="/" className="text-sm text-gray-500 hover:text-primary">← 返回首页</Link>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        {data?.node_count} 个节点 · {data?.edge_count} 条边 — 节点越大引用越多，颜色代表分类
      </p>
      <div className="relative border dark:border-gray-700 rounded-xl overflow-hidden bg-white dark:bg-gray-800">
        <svg ref={svgRef} className="w-full" viewBox="0 0 900 600" preserveAspectRatio="xMidYMid meet" />
        {tooltip && (
          <div
            className="absolute z-10 px-3 py-2 rounded-lg bg-gray-900 text-white text-xs shadow-lg pointer-events-none whitespace-nowrap"
            style={{ left: tooltip.x + 12, top: tooltip.y }}
          >
            <div className="font-medium">{tooltip.node.title}</div>
            <div className="text-gray-400">{tooltip.node.category} · {tooltip.node.links} 引用</div>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-3 mt-4 justify-center">
        {Object.entries(
          { "经济发展": "#2563eb", "文化旅游": "#059669", "人口与民族": "#7c3aed",
            "地理与自然环境": "#0891b2", "特产与资源": "#d97706", "交通与基础设施": "#dc2626",
            "政策与治理": "#4f46e5", "社会民生": "#db2777", "历史沿革": "#9333ea",
            "行政区划": "#0d9488", "总览": "#6b7280", "未分类": "#9ca3af" }
        ).map(([cat, color]) => (
          <span key={cat} className="flex items-center gap-1.5 text-xs text-gray-500">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            {cat}
          </span>
        ))}
      </div>
    </div>
  );
}
