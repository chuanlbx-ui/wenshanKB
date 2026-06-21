#!/usr/bin/env python3
"""
文山知识库自动维护脚本
功能：扫描变更、更新统计、检测数据矛盾、追加日志
由 Marvis 定时任务每60分钟触发执行
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

KB_ROOT = Path(r"D:\WenShanKB")
SYSTEM_DIR = KB_ROOT / "_system"
LOG_FILE = SYSTEM_DIR / "auto_maintain_log.md"
STATS_FILE = SYSTEM_DIR / "auto_stats.json"

# 十大分类目录
CATEGORIES = {
    "00-总览": "总览",
    "01-地理与自然环境": "地理与自然环境",
    "02-历史沿革": "历史沿革",
    "03-行政区划": "行政区划",
    "04-人口与民族": "人口与民族",
    "05-经济发展": "经济发展",
    "06-文化旅游": "文化旅游",
    "07-特产与资源": "特产与资源",
    "08-交通与基础设施": "交通与基础设施",
    "09-政策与治理": "政策与治理",
    "10-社会民生": "社会民生",
}

# 关键数据锚点及正则（用于一致性校验）
DATA_ANCHORS = {
    "gdp": {"pattern": r"GDP.*?(\d+\.?\d*)\s*亿", "expected": "1632.64", "label": "GDP(亿元)"},
    "population": {"pattern": r"常住人口.*?(\d+\.?\d*)\s*万", "expected": "335.4", "label": "常住人口(万)"},
    "urbanization": {"pattern": r"城镇化率.*?(\d+\.?\d*)%", "expected": "41.19", "label": "城镇化率(%)"},
    "green_aluminum": {"pattern": r"绿色铝.*?(\d+\.?\d*)\s*亿", "expected": "1000", "label": "绿色铝产值(亿)"},
    "sanqi": {"pattern": r"三七.*?综合产值[^总].*?(\d+\.?\d*)\s*亿", "expected": "456", "label": "三七综合产值(亿)"},
    "chinese_herbal": {"pattern": r"中药材.*?综合.*?(\d+\.?\d*)\s*亿", "expected": "456", "label": "中药材综合产值(亿)"},
}


def load_previous_stats():
    """加载上次统计快照"""
    if STATS_FILE.exists():
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_stats(stats):
    """保存当前统计快照"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=str)


def scan_kb():
    """扫描知识库，返回统计信息"""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "categories": {},
        "total_md": 0,
        "total_size_kb": 0,
        "issues": [],
    }

    for cat_dir, cat_name in CATEGORIES.items():
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            stats["issues"].append(f"目录不存在: {cat_dir}")
            continue

        md_files = list(cat_path.glob("*.md"))
        cat_stats = {
            "name": cat_name,
            "md_count": len(md_files),
            "total_size": sum(f.stat().st_size for f in md_files),
            "files": {},
        }

        for f in md_files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            cat_stats["files"][f.name] = {
                "size": f.stat().st_size,
                "modified": mtime,
            }

        stats["categories"][cat_dir] = cat_stats
        stats["total_md"] += len(md_files)
        stats["total_size_kb"] += cat_stats["total_size"]

    stats["total_size_kb"] = round(stats["total_size_kb"] / 1024, 2)

    # 扫描 wiki 目录
    wiki_path = KB_ROOT / "wiki"
    if wiki_path.exists():
        wiki_md = list(wiki_path.rglob("*.md"))
        stats["wiki_md_count"] = len(wiki_md)

    # 扫描 ai-hub
    aihub_path = KB_ROOT / "ai-hub"
    if aihub_path.exists():
        stats["aihub_md_count"] = len(list(aihub_path.glob("*.md")))

    return stats


def detect_changes(prev_stats, curr_stats):
    """对比统计快照，检测变更"""
    changes = {"new_files": [], "modified_files": [], "deleted_files": [], "count_changes": []}

    if not prev_stats:
        return changes

    for cat_dir, curr_cat in curr_stats.get("categories", {}).items():
        prev_cat = prev_stats.get("categories", {}).get(cat_dir, {})
        prev_files = prev_cat.get("files", {})
        curr_files = curr_cat.get("files", {})

        for fname in curr_files:
            if fname not in prev_files:
                changes["new_files"].append(f"{cat_dir}/{fname}")
            elif curr_files[fname]["size"] != prev_files[fname]["size"]:
                changes["modified_files"].append(f"{cat_dir}/{fname}")

        for fname in prev_files:
            if fname not in curr_files:
                changes["deleted_files"].append(f"{cat_dir}/{fname}")

        if "md_count" in curr_cat and "md_count" in prev_cat:
            if curr_cat["md_count"] != prev_cat["md_count"]:
                changes["count_changes"].append(
                    f"{cat_dir}: {prev_cat['md_count']} → {curr_cat['md_count']}"
                )

    return changes


def check_frontmatter():
    """检查笔记 frontmatter 完整性"""
    issues = []
    for cat_dir in CATEGORIES:
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.md"):
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(3000)  # 读前3000字符（覆盖AIGC长Base64行）
            missing = []
            if "created:" not in content.lower():
                missing.append("created")
            if "tags:" not in content.lower():
                missing.append("tags")
            if "sources:" not in content.lower() and "source:" not in content.lower():
                missing.append("sources")
            if missing:
                issues.append(f"{cat_dir}/{md_file.name}: 缺少 {', '.join(missing)}")
    return issues


def check_data_consistency():
    """检查关键数据锚点一致性"""
    issues = []
    # 用于跳过目标值行和锚点标注行的关键词
    TARGET_KEYWORDS = ["目标", "2030年", "十五五末", "锚点", "口径", "进出口", "非绿色铝产值", "突破千亿", "千亿级", "仅三七", "品种", "中药材全口径", "中药材产业综合", "三七产业综合"]
    for cat_dir in CATEGORIES:
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.md"):
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for anchor_key, anchor_cfg in DATA_ANCHORS.items():
                for match_obj in re.finditer(anchor_cfg["pattern"], content):
                    raw_value = match_obj.group(1)
                    # 过滤目标值行
                    line_start = content.rfind("\n", 0, match_obj.start()) + 1
                    line_end = content.find("\n", match_obj.end())
                    if line_end == -1:
                        line_end = len(content)
                    match_line = content[line_start:line_end]
                    if any(kw in match_line for kw in TARGET_KEYWORDS):
                        continue
                    # 跳过 wikilink 引用行（[[...]]）
                    if "[[" in match_line:
                        continue
                    # 归一化：处理 1,000 格式 → 1000
                    normalized = raw_value.replace(",", "")
                    try:
                        if float(normalized) != float(anchor_cfg["expected"]):
                            issues.append(
                                f"{cat_dir}/{md_file.name}: {anchor_cfg['label']} 为 {raw_value}，期望 {anchor_cfg['expected']}"
                            )
                    except ValueError:
                        continue
    return issues


def write_log(changes, fm_issues, data_issues, stats):
    """追加维护日志"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n---\n## {now} 自动维护\n\n"

    # 变更摘要
    total_changes = (
        len(changes.get("new_files", []))
        + len(changes.get("modified_files", []))
        + len(changes.get("deleted_files", []))
    )
    if total_changes > 0:
        log_entry += f"### 变更 ({total_changes}项)\n"
        for f in changes.get("new_files", []):
            log_entry += f"- **[新增]** {f}\n"
        for f in changes.get("modified_files", []):
            log_entry += f"- **[修改]** {f}\n"
        for f in changes.get("deleted_files", []):
            log_entry += f"- **[删除]** {f}\n"
        for c in changes.get("count_changes", []):
            log_entry += f"- **[计数更新]** {c}\n"
    else:
        log_entry += "### 变更\n- 无变更\n"

    # 统计快照
    log_entry += f"\n### 统计\n"
    log_entry += f"- 分类笔记总数: {stats['total_md']}\n"
    log_entry += f"- 总大小: {stats['total_size_kb']} KB\n"
    if "wiki_md_count" in stats:
        log_entry += f"- Wiki 笔记: {stats['wiki_md_count']}\n"
    if "aihub_md_count" in stats:
        log_entry += f"- AI Hub 笔记: {stats['aihub_md_count']}\n"

    # 各分类明细
    log_entry += "\n| 分类 | 笔记数 |\n|------|--------|\n"
    for cat_dir, cat_stats in stats.get("categories", {}).items():
        log_entry += f"| {cat_dir} | {cat_stats['md_count']} |\n"

    # Frontmatter 问题
    if fm_issues:
        log_entry += f"\n### Frontmatter 缺失 ({len(fm_issues)}项)\n"
        for issue in fm_issues[:10]:  # 最多列10条
            log_entry += f"- {issue}\n"
        if len(fm_issues) > 10:
            log_entry += f"- ... 及其他 {len(fm_issues) - 10} 项\n"

    # 数据矛盾
    if data_issues:
        log_entry += f"\n### 数据矛盾 ({len(data_issues)}项)\n"
        for issue in data_issues[:10]:
            log_entry += f"- {issue}\n"
        if len(data_issues) > 10:
            log_entry += f"- ... 及其他 {len(data_issues) - 10} 项\n"

    log_entry += "\n"

    # 追加到日志文件
    if LOG_FILE.exists():
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    else:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 文山知识库自动维护日志\n\n> 启动于 {now}\n{log_entry}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始自动维护...")

    prev_stats = load_previous_stats()
    curr_stats = scan_kb()

    changes = detect_changes(prev_stats, curr_stats)
    fm_issues = check_frontmatter()
    data_issues = check_data_consistency()

    save_stats(curr_stats)
    write_log(changes, fm_issues, data_issues, curr_stats)

    # 输出摘要
    total_issues = len(fm_issues) + len(data_issues)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 完成。")
    print(f"  笔记: {curr_stats['total_md']} 篇 | 变更: {len(changes.get('new_files',[])) + len(changes.get('modified_files',[]))} 项")
    print(f"  Frontmatter 缺失: {len(fm_issues)} | 数据矛盾: {len(data_issues)}")
    print(f"  日志: {LOG_FILE}")

    return {
        "total_md": curr_stats["total_md"],
        "changes": len(changes.get("new_files", [])) + len(changes.get("modified_files", [])),
        "fm_missing": len(fm_issues),
        "data_issues": len(data_issues),
    }


if __name__ == "__main__":
    main()
