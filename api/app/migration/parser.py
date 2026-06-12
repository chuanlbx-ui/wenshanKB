"""Markdown 解析器 — frontmatter + wikilink"""

import re
import yaml
from pathlib import Path
from typing import Tuple, Optional


def parse_frontmatter(filepath: Path) -> Tuple[dict, str]:
    """解析 Markdown 文件的 YAML frontmatter 和正文"""
    content = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            metadata = {}
        body = match.group(2)
    else:
        metadata = {}
        body = content
    return metadata, body


def extract_wikilinks(text: str) -> list[tuple[str, str]]:
    """提取 [[目标|别名]] 或 [[目标]] 格式的 wikilink"""
    pattern = r"\[\[([^\]|#]+)(?:[#|]([^\]]+))?\]\]"
    return re.findall(pattern, text)


def extract_all_wikilinks(metadata: dict, body: str) -> list[tuple[str, str]]:
    """提取 frontmatter related 字段 + 正文中所有的 wikilink"""
    links = set()

    # 正文中的 wikilink
    for target, alias in extract_wikilinks(body):
        links.add((target.strip(), alias.strip() if alias else ""))

    # frontmatter related 字段中的 wikilink
    related = metadata.get("related", [])
    if isinstance(related, list):
        for item in related:
            if isinstance(item, str):
                for target, alias in extract_wikilinks(item):
                    links.add((target.strip(), alias.strip() if alias else ""))

    return list(links)


def extract_tags(metadata: dict) -> list[str]:
    """从 frontmatter 提取标签"""
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if t]
    return []


def slugify(text: str) -> str:
    """生成 URL 友好的 slug"""
    # 保留中文字符，替换特殊字符
    slug = text.strip()
    slug = slug.replace("/", "-").replace("\\", "-")
    slug = slug.replace(" ", "-").replace("_", "-")
    # 去掉多余连字符
    slug = re.sub(r"-+", "-", slug)
    return slug


def extract_plain_text(body: str) -> str:
    """从 Markdown 提取纯文本（去 wikilink 语法、去 Markdown 标记）"""
    text = body
    # wikilink → 仅保留目标名
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    # 去掉 Markdown 标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 去掉粗体/斜体
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # 去掉链接
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 去掉表格分隔行
    text = re.sub(r"^\|[-:| ]+\|$", "", text, flags=re.MULTILINE)
    # 去掉引用标记
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # 压缩空白
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_created_date(metadata: dict) -> Optional[str]:
    """解析 frontmatter 中的 created 字段"""
    created = metadata.get("created")
    if not created:
        return None
    if isinstance(created, str):
        # 可能格式：2026-05-24 或 2026-05-24T...
        return created[:19]  # 截取到秒
    return str(created)
