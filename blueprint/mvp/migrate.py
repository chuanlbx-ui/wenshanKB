#!/usr/bin/env python3
"""
WenShanKB 数据迁移工具
将 D:\WenShanKB Obsidian 知识库迁移到 PostgreSQL + pgvector

用法:
    python migrate.py --full          # 全量迁移（清空重建）
    python migrate.py --incremental   # 增量同步
    python migrate.py --dry-run       # 预览模式，不写入数据库

环境变量:
    DATABASE_URL=postgresql://user:pass@localhost:5432/wenshan_kb
"""

import json
import os
import re
import sys
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import yaml

# ── 数据库 ──────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "postgresql://kb_user:kb_pass@localhost:5432/wenshan_kb")

def get_db():
    """懒加载数据库连接"""
    try:
        import psycopg2
        import psycopg2.extras
        psycopg2.extras.register_uuid()
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        return conn
    except ImportError:
        print("[FATAL] psycopg2 未安装。运行: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] 数据库连接失败: {e}")
        sys.exit(1)

# ── 向量嵌入 ────────────────────────────────────────
EMBEDDING_DIM = 1536
_embedding_client = None

def get_embedding_client():
    global _embedding_client
    if _embedding_client is not None:
        return _embedding_client

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("[WARN] OPENAI_API_KEY 未设置，将使用零向量占位。"
              "设置后重新运行 --incremental 可补充嵌入。")
        return None

    try:
        from openai import OpenAI
        _embedding_client = OpenAI(api_key=api_key)
        return _embedding_client
    except ImportError:
        print("[WARN] openai 库未安装。运行: pip install openai")
        return None


def generate_embedding(text: str) -> Optional[list[float]]:
    client = get_embedding_client()
    if client is None:
        return None

    try:
        truncated = text[:20000]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=truncated,
            dimensions=EMBEDDING_DIM
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  [WARN] 向量嵌入失败: {e}")
        return None


# ── Frontmatter 解析 ────────────────────────────────
def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (元数据, 正文)"""
    content = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            metadata = {}
        body = match.group(2).strip()
    else:
        metadata = {}
        body = content.strip()
    return metadata, body


# ── Wikilink 提取 ───────────────────────────────────
def extract_wikilinks(content: str) -> list[dict]:
    """提取 [[目标|别名]] 格式的 wikilink"""
    pattern = r"\[\[([^\]|#]+?)(?:[|#]([^\]]+?))?\]\]"
    links = []
    for m in re.finditer(pattern, content):
        target = m.group(1).strip()
        alias = m.group(2).strip() if m.group(2) else target
        links.append({"target": target, "alias": alias})
    return links


# ── 纯文本提取 ──────────────────────────────────────
def extract_plain_text(content: str) -> str:
    """从 Markdown 中提取纯文本，去除格式标记"""
    # 移除代码块
    text = re.sub(r"```[\s\S]*?```", " ", content)
    # 移除行内代码
    text = re.sub(r"`[^`]+`", " ", text)
    # 移除 wikilink
    text = re.sub(r"\[\[([^\]|#]+?)(?:[|#][^\]]+?)?\]\]", r"\1", text)
    # 移除 Markdown 链接
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # 移除图片
    text = re.sub(r"!\[.*?\]\([^)]+\)", " ", text)
    # 移除标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除列表标记
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
    # 移除加粗/斜体
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # 移除块引用标记
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # 合并多余空白
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── 分类推断 ────────────────────────────────────────
def infer_category(relative_path: Path) -> tuple[str, str]:
    """从路径推断分类名和显示名"""
    if len(relative_path.parts) >= 2:
        cat_name = relative_path.parts[0]
    else:
        cat_name = "未分类"

    # 分类名映射
    cat_map = {
        "00-总览": ("00-总览", "总览与核心数据"),
        "01-地理与自然环境": ("01-地理与自然环境", "地理与自然环境"),
        "02-历史沿革": ("02-历史沿革", "历史沿革"),
        "03-行政区划": ("03-行政区划", "行政区划"),
        "04-人口与民族": ("04-人口与民族", "人口与民族"),
        "05-经济发展": ("05-经济发展", "经济发展"),
        "06-文化旅游": ("06-文化旅游", "文化旅游"),
        "07-特产与资源": ("07-特产与资源", "特产与资源"),
        "08-交通与基础设施": ("08-交通与基础设施", "交通与基础设施"),
        "09-政策与治理": ("09-政策与治理", "政策与治理"),
        "10-社会民生": ("10-社会民生", "社会民生"),
        "synthesis": ("synthesis", "跨分类合成笔记"),
        "blueprint": ("blueprint", "系统蓝图"),
    }
    return cat_map.get(cat_name, (cat_name, cat_name))


def generate_slug(filepath: Path, title: str) -> str:
    if title:
        # 简化标题为 slug
        slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-").lower()
        if slug:
            return slug
    # 回退到文件名
    return filepath.stem


# ── 主迁移逻辑 ──────────────────────────────────────
class ObsidianMigrator:
    def __init__(self, source_dir: str, dry_run: bool = False):
        self.source_dir = Path(source_dir)
        self.dry_run = dry_run
        self.db = None if dry_run else get_db()
        self.stats = {
            "total": 0, "created": 0, "updated": 0, "skipped": 0,
            "links_created": 0, "embeddings_generated": 0, "errors": 0,
        }

    def run(self, incremental: bool = False):
        """执行迁移"""
        print(f"\n{'='*60}")
        print(f"  WenShanKB 数据迁移工具")
        print(f"  源目录: {self.source_dir}")
        print(f"  模式: {'增量同步' if incremental else '全量迁移'}")
        print(f"  预览: {'是 (不写入数据库)' if self.dry_run else '否'}")
        print(f"{'='*60}\n")

        # 1. 扫描全部 Markdown 文件
        md_files = self.scan_markdown_files()
        self.stats["total"] = len(md_files)
        print(f"[1/5] 扫描到 {len(md_files)} 个 Markdown 文件")

        # 2. 解析并入库
        print(f"[2/5] 解析笔记...")
        note_ids = {}
        for i, filepath in enumerate(md_files, 1):
            relative = filepath.relative_to(self.source_dir)
            print(f"  [{i}/{len(md_files)}] {relative}")
            try:
                note_id = self.process_note(filepath, incremental)
                if note_id:
                    note_ids[str(relative)] = note_id
                    self.stats["created" if not incremental else "updated"] += 1
            except Exception as e:
                print(f"    [ERROR] {e}")
                self.stats["errors"] += 1

        # 3. 建立 wikilink 关系
        print(f"\n[3/5] 建立 wikilink 关系...")
        self.build_links(note_ids)

        if not self.dry_run:
            self.generate_embeddings()
        else:
            print(f"\n[4/5] 预览模式 — 跳过向量嵌入")

        # 5. 完成
        print(f"\n[5/5] 迁移完成")
        self.print_stats()

        if not self.dry_run and self.db:
            self.db.close()

    def scan_markdown_files(self) -> list[Path]:
        """扫描所有 .md 文件，排除特定目录"""
        exclude_dirs = {".git", ".obsidian", "node_modules", "__pycache__",
                        "output", "assets", "temp"}
        files = []
        for md in self.source_dir.rglob("*.md"):
            # 过滤排除目录
            parts = set(md.relative_to(self.source_dir).parts)
            if parts & exclude_dirs:
                continue
            files.append(md)
        return sorted(files)

    def process_note(self, filepath: Path, incremental: bool) -> Optional[str]:
        """处理单个笔记：解析 → 写入数据库"""
        relative = filepath.relative_to(self.source_dir)

        # 解析 frontmatter
        metadata, content = parse_frontmatter(filepath)

        # 提取字段
        title = metadata.get("title") or filepath.stem
        slug = generate_slug(filepath, title)
        plain_text = extract_plain_text(content)
        cat_name, cat_display = infer_category(relative)
        created_str = metadata.get("created")
        tags_list = metadata.get("tags", [])
        if isinstance(tags_list, str):
            tags_list = [t.strip() for t in tags_list.split(",")]

        # 计算文件哈希（用于增量检测）
        file_hash = hashlib.md5(
            filepath.read_bytes()
        ).hexdigest()

        if self.dry_run:
            print(f"    [{cat_display}] {title}  (slug={slug}, tags={tags_list})")
            return str(relative)

        # 检查是否已存在
        cur = self.db.cursor()
        cur.execute("SELECT id, content_hash FROM notes WHERE slug = %s", (slug,))
        existing = cur.fetchone()

        if existing:
            if incremental and existing[1] == file_hash:
                self.stats["skipped"] += 1
                cur.close()
                return str(existing[0])

            # 更新
            cur.execute("""
                UPDATE notes SET
                    title = %s, content = %s, plain_text = %s,
                    frontmatter = %s, category_path = %s,
                    content_hash = %s, updated_at = NOW()
                WHERE slug = %s
                RETURNING id
            """, (title, content, plain_text, json.dumps(metadata, ensure_ascii=False),
                  str(relative), file_hash, slug))
        else:
            # 创建
            cur.execute("""
                INSERT INTO notes (title, slug, content, plain_text,
                    frontmatter, category_id, category_path, status,
                    source_path, source_type, content_hash)
                VALUES (%s, %s, %s, %s, %s,
                    (SELECT id FROM categories WHERE name = %s),
                    %s, 'published', %s, 'obsidian', %s)
                RETURNING id
            """, (title, slug, content, plain_text,
                  json.dumps(metadata, ensure_ascii=False),
                  cat_name, str(relative), str(filepath), file_hash))

        note_id = cur.fetchone()[0]

        # 处理标签
        for tag_name in tags_list:
            cur.execute("""
                INSERT INTO tags (name) VALUES (%s)
                ON CONFLICT (name) DO NOTHING
            """, (tag_name,))
            cur.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
            tag_id = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO note_tags (note_id, tag_id) VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (note_id, tag_id))

        self.db.commit()
        cur.close()
        return str(note_id)

    def build_links(self, note_ids: dict[str, str]):
        """建立 wikilink 关系"""
        if self.dry_run:
            print("  预览模式 — 跳过链接建立")
            return

        cur = self.db.cursor()

        # 清空旧链接（全量模式）
        cur.execute("DELETE FROM note_links")

        # 遍历所有笔记，提取 wikilink
        cur.execute("SELECT id, content, slug FROM notes")
        for note_id, content, slug in cur.fetchall():
            wikilinks = extract_wikilinks(content)
            for wl in wikilinks:
                target_slug = wl["target"]

                # 尝试匹配已有的笔记
                cur.execute("SELECT id FROM notes WHERE slug = %s OR title = %s",
                            (target_slug, target_slug))
                target = cur.fetchone()

                cur.execute("""
                    INSERT INTO note_links (source_note_id, target_note_slug,
                        target_note_id, link_text)
                    VALUES (%s, %s, %s, %s)
                """, (note_id, target_slug,
                      target[0] if target else None,
                      wl["alias"]))

                self.stats["links_created"] += 1

        self.db.commit()
        cur.close()
        print(f"  建立了 {self.stats['links_created']} 条 wikilink 关系")

    def generate_embeddings(self):
        cur = self.db.cursor()

        cur.execute("""
            SELECT id, plain_text FROM notes
            WHERE embedding IS NULL
        """)
        rows = cur.fetchall()

        if not rows:
            print("  所有笔记已有向量嵌入，跳过")
            cur.close()
            return

        print(f"  为 {len(rows)} 篇笔记生成向量嵌入...")
        for i, (note_id, plain_text) in enumerate(rows, 1):
            if not plain_text:
                continue

            emb = generate_embedding(plain_text)
            if emb:
                # pgvector 格式：'[0.1, 0.2, ...]'
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                cur.execute(
                    "UPDATE notes SET embedding = %s::vector WHERE id = %s",
                    (emb_str, note_id)
                )
                self.stats["embeddings_generated"] += 1

            if i % 10 == 0:
                print(f"    {i}/{len(rows)}")
                self.db.commit()

        self.db.commit()
        cur.close()

    def print_stats(self):
        print(f"\n{'─'*40}")
        print("  迁移统计:")
        print(f"    扫描文件:       {self.stats['total']}")
        print(f"    新建/更新:      {self.stats['created'] + self.stats['updated']}")
        print(f"    跳过(未变更):    {self.stats['skipped']}")
        print(f"    Wikilink 关系:  {self.stats['links_created']}")
        print(f"    向量嵌入:       {self.stats['embeddings_generated']}")
        print(f"    错误:           {self.stats['errors']}")
        print(f"{'─'*40}")


# ── CLI ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="WenShanKB Obsidian → PostgreSQL 迁移工具"
    )
    parser.add_argument(
        "--source", default=r"D:\WenShanKB",
        help="Obsidian 知识库根目录"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="全量迁移（清空数据库后重新导入）"
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="增量同步（仅更新变更文件）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预览模式：解析但不写入数据库"
    )

    args = parser.parse_args()

    if not args.full and not args.incremental and not args.dry_run:
        parser.print_help()
        print("\n请指定运行模式：--full / --incremental / --dry-run")
        sys.exit(1)

    migrator = ObsidianMigrator(args.source, dry_run=args.dry_run)
    migrator.run(incremental=args.incremental)


