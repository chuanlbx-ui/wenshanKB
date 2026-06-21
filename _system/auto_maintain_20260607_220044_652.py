#!/usr/bin/env python3
"""
文山知识库自动维护脚本 v2.0
四维升级：防守型维护 + 知识补充 + 时效刷新 + 深化扩展
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
TASK_QUEUE_FILE = SYSTEM_DIR / "task_queue.json"

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

DATA_ANCHORS = {
    "gdp": {"pattern": r"GDP.*?(\d+\.?\d*)\s*亿", "expected": "1632.64", "label": "GDP(亿元)"},
    "population": {"pattern": r"常住人口.*?(\d+\.?\d*)\s*万", "expected": "335.4", "label": "常住人口(万)"},
    "urbanization": {"pattern": r"城镇化率.*?(\d+\.?\d*)%", "expected": "41.19", "label": "城镇化率(%)"},
    "green_aluminum": {"pattern": r"绿色铝.*?(\d+\.?\d*)\s*亿", "expected": "1000", "label": "绿色铝产值(亿)"},
    "sanqi": {"pattern": r"三七.*?综合.*?(\d+\.?\d*)\s*亿", "expected": "456", "label": "三七综合产值(亿)"},
}

ROTATION_ORDER = {
    "county_deepening": ["砚山县", "西畴县", "丘北县", "广南县", "富宁县"],
    "entities": ["天保口岸", "田蓬口岸", "都龙口岸", "文砚同城化", "普者黑景区", "坝美景区", "老山", "文山三七产业园区", "富宁港", "广南八宝米产业"],
    "creative_toolkit": ["选题日历补充", "金句语录扩充", "场景描写库扩充", "人物故事集扩充"],
}


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ====== 维度零：基础扫描 ======

def scan_kb():
    stats = {"timestamp": datetime.now().isoformat(), "categories": {}, "total_md": 0, "total_size_kb": 0, "issues": []}
    for cat_dir, cat_name in CATEGORIES.items():
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            stats["issues"].append(f"目录不存在: {cat_dir}")
            continue
        md_files = list(cat_path.glob("*.md"))
        cat_stats = {"name": cat_name, "md_count": len(md_files), "total_size": sum(f.stat().st_size for f in md_files), "files": {}}
        for f in md_files:
            cat_stats["files"][f.name] = {"size": f.stat().st_size, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
        stats["categories"][cat_dir] = cat_stats
        stats["total_md"] += len(md_files)
        stats["total_size_kb"] += cat_stats["total_size"]
    stats["total_size_kb"] = round(stats["total_size_kb"] / 1024, 2)
    wiki_path = KB_ROOT / "wiki"
    if wiki_path.exists():
        stats["wiki_md_count"] = len(list(wiki_path.rglob("*.md")))
    aihub_path = KB_ROOT / "ai-hub"
    if aihub_path.exists():
        stats["aihub_md_count"] = len(list(aihub_path.glob("*.md")))
    return stats


def detect_changes(prev_stats, curr_stats):
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
                changes["count_changes"].append(f"{cat_dir}: {prev_cat['md_count']} → {curr_cat['md_count']}")
    return changes


def check_frontmatter():
    issues = []
    for cat_dir in CATEGORIES:
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.md"):
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(500)
            missing = []
            if "created:" not in content.lower():
                missing.append("created")
            if "tags:" not in content.lower():
                missing.append("tags")
            if "sources:" not in content.lower() and "source:" not in content.lower():
                missing.append("sources")
            if missing:
                issues.append({"file": f"{cat_dir}/{md_file.name}", "missing": missing})
    return issues


def check_data_consistency():
    issues = []
    for cat_dir in CATEGORIES:
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.md"):
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for anchor_key, anchor_cfg in DATA_ANCHORS.items():
                for m in re.findall(anchor_cfg["pattern"], content):
                    if m != anchor_cfg["expected"]:
                        issues.append({"file": f"{cat_dir}/{md_file.name}", "anchor": anchor_key, "found": m, "expected": anchor_cfg["expected"], "label": anchor_cfg["label"]})
    return issues


# ====== 维度一：缺口分析 ======

def analyze_gaps(stats):
    """分析知识缺口，返回本轮待补充任务"""
    tasks = []
    task_queue = load_json(TASK_QUEUE_FILE)

    # 1. 县深度档案缺口
    county_dir = KB_ROOT / "03-行政区划"
    if county_dir.exists():
        county_files = list(county_dir.glob("*.md"))
        county_sizes = {}
        for f in county_files:
            county_sizes[f.stem] = f.stat().st_size
        shallow_counties = [
            name for name in ROTATION_ORDER["county_deepening"]
            if county_sizes.get(name.replace("县", "县深度"), 0) < 3000
        ]
        if shallow_counties:
            last_idx = task_queue.get("county_index", -1)
            next_idx = (last_idx + 1) % len(shallow_counties)
            target = shallow_counties[next_idx]
            tasks.append({
                "type": "county_deepening",
                "priority": "P1",
                "target": target,
                "file": f"03-行政区划/{target}深度.md",
                "action": f"深化 {target} 的深度档案，补充地理、经济、人口、文化、特色产业等维度的详细内容，目标3000字以上。使用 web_search 搜索 {target} 最新数据后写入。",
            })
            task_queue["county_index"] = next_idx

    # 2. wiki/entities 实体页缺口
    wiki_entities_dir = KB_ROOT / "wiki" / "entities"
    existing_entities = set()
    if wiki_entities_dir.exists():
        existing_entities = {f.stem for f in wiki_entities_dir.glob("*.md")}
    missing_entities = [e for e in ROTATION_ORDER["entities"] if e not in existing_entities]
    if missing_entities:
        last_idx = task_queue.get("entity_index", -1)
        next_idx = (last_idx + 1) % len(missing_entities)
        target = missing_entities[next_idx]
        tasks.append({
            "type": "entity_page",
            "priority": "P1",
            "target": target,
            "file": f"wiki/entities/{target}.md",
            "action": f"新建 wiki/entities/{target}.md 实体页，包含定义、关键数据、产业链位置、与其他实体的关联。使用 web_search 搜索 {target} 文山 最新信息后写入。",
        })
        task_queue["entity_index"] = next_idx

    # 3. sources 缺失补充
    fm_issues = check_frontmatter()
    sources_missing = [i for i in fm_issues if "sources" in i["missing"]]
    if sources_missing:
        batch = sources_missing[:5]
        targets = [i["file"] for i in batch]
        tasks.append({
            "type": "add_sources",
            "priority": "P1",
            "target": ", ".join(targets),
            "file_list": targets,
            "action": f"为以下笔记补充 sources 来源标注（政府公报/年鉴/官网URL）：{targets}。读取每篇内容，搜索确认数据来源后补充 frontmatter 中的 sources 字段。",
        })

    # 4. 创作工具包扩充
    ai_hub_dir = KB_ROOT / "ai-hub"
    if ai_hub_dir.exists():
        last_idx = task_queue.get("toolkit_index", -1)
        next_idx = (last_idx + 1) % len(ROTATION_ORDER["creative_toolkit"])
        toolkit_target = ROTATION_ORDER["creative_toolkit"][next_idx]
        tasks.append({
            "type": "creative_toolkit",
            "priority": "P2",
            "target": toolkit_target,
            "action": f"扩充 ai-hub 创作工具包：{toolkit_target}。基于知识库现有内容，结合 web_search 搜索补充素材。",
        })
        task_queue["toolkit_index"] = next_idx

    save_json(TASK_QUEUE_FILE, task_queue)
    return tasks


# ====== 维度二：时效性检查 ======

def check_timeliness():
    """检查关键数据的时效性，返回需要刷新的指标"""
    refresh_list = []
    one_week_ago = datetime(2026, 6, 1)  # 7天前

    # 检查是否有笔记超过7天未更新且包含关键经济指标
    for cat_dir in CATEGORIES:
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.md"):
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime < one_week_ago:
                with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(3000)
                for anchor_key, anchor_cfg in DATA_ANCHORS.items():
                    if re.search(anchor_cfg["pattern"], content):
                        refresh_list.append({
                            "file": f"{cat_dir}/{md_file.name}",
                            "anchor": anchor_key,
                            "label": anchor_cfg["label"],
                            "last_updated": mtime.strftime("%Y-%m-%d"),
                        })
                        break
    return refresh_list[:3]  # 每轮最多3个


# ====== 维度三：浅层笔记检测 ======

def find_shallow_notes(stats, min_bytes=2000):
    """找到内容偏浅的笔记"""
    shallow = []
    for cat_dir, cat_stats in stats.get("categories", {}).items():
        for fname, finfo in cat_stats.get("files", {}).items():
            if finfo["size"] < min_bytes and fname not in ["README.md", "index.md"]:
                shallow.append({
                    "file": f"{cat_dir}/{fname}",
                    "size": finfo["size"],
                })
    shallow.sort(key=lambda x: x["size"])
    return shallow[:3]


# ====== 维度四：交叉引用检测 ======

def check_wikilinks():
    """检测缺少内联链接的笔记"""
    missing = []
    for cat_dir in CATEGORIES:
        cat_path = KB_ROOT / cat_dir
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.md"):
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "[[" not in content:
                missing.append(f"{cat_dir}/{md_file.name}")
    return missing[:5]


# ====== 写日志 ======

def write_log(changes, fm_issues, data_issues, stats, gap_tasks, timeliness_tasks, shallow_notes, wikilink_missing):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n---\n## {now} 自动维护 v2.0\n"

    total_changes = len(changes.get("new_files", [])) + len(changes.get("modified_files", [])) + len(changes.get("deleted_files", []))
    log_entry += f"### 变更 ({'有' if total_changes else '无'})\n"
    if total_changes:
        for f in changes.get("new_files", []):
            log_entry += f"- **[新增]** {f}\n"
        for f in changes.get("modified_files", []):
            log_entry += f"- **[修改]** {f}\n"
        for f in changes.get("deleted_files", []):
            log_entry += f"- **[删除]** {f}\n"
        for c in changes.get("count_changes", []):
            log_entry += f"- **[计数更新]** {c}\n"

    log_entry += f"\n### 统计\n- 笔记: {stats['total_md']} 篇 | 大小: {stats['total_size_kb']} KB\n"
    if stats.get("wiki_md_count"):
        log_entry += f"- Wiki: {stats['wiki_md_count']} 篇\n"
    if stats.get("aihub_md_count"):
        log_entry += f"- AI Hub: {stats['aihub_md_count']} 篇\n"

    log_entry += "\n| 分类 | 笔记数 |\n|------|--------|\n"
    for cat_dir, cat_stats in stats.get("categories", {}).items():
        log_entry += f"| {cat_dir} | {cat_stats['md_count']} |\n"

    if fm_issues:
        log_entry += f"\n### Frontmatter 缺失 ({len(fm_issues)}项)\n"
        for issue in fm_issues[:5]:
            log_entry += f"- {issue['file']}: 缺少 {', '.join(issue['missing'])}\n"
    if data_issues:
        log_entry += f"\n### 数据矛盾 ({len(data_issues)}项)\n"
        for issue in data_issues[:5]:
            log_entry += f"- {issue['file']}: {issue['label']}={issue['found']} (期望 {issue['expected']})\n"

    log_entry += f"\n### 本轮任务 ({len(gap_tasks)}个补充 + {len(timeliness_tasks)}个刷新 + {len(shallow_notes)}个深化 + {len(wikilink_missing)}个引用)\n"
    for t in gap_tasks:
        log_entry += f"- [{t['priority']}] {t['type']}: {t['target']}\n"
    for t in timeliness_tasks:
        log_entry += f"- [时效] {t['file']}: {t['label']}\n"
    for s in shallow_notes:
        log_entry += f"- [深化] {s['file']} ({s['size']}B)\n"
    log_entry += "\n"

    if LOG_FILE.exists():
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    else:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 文山知识库自动维护日志 v2.0\n\n> 启动于 {now}\n{log_entry}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 文山KB自动维护 v2.0 开始...")

    prev_stats = load_json(STATS_FILE)
    curr_stats = scan_kb()
    changes = detect_changes(prev_stats, curr_stats)
    fm_issues = check_frontmatter()
    data_issues = check_data_consistency()

    # 四维分析
    gap_tasks = analyze_gaps(curr_stats)
    timeliness_tasks = check_timeliness()
    shallow_notes = find_shallow_notes(curr_stats)
    wikilink_missing = check_wikilinks()

    save_json(STATS_FILE, curr_stats)
    write_log(changes, fm_issues, data_issues, curr_stats, gap_tasks, timeliness_tasks, shallow_notes, wikilink_missing)

    # 输出结构化结果供 Agent 消费
    result = {
        "stats": {"total_md": curr_stats["total_md"], "wiki_md": curr_stats.get("wiki_md_count", 0), "aihub_md": curr_stats.get("aihub_md_count", 0)},
        "changes": {"new": len(changes.get("new_files", [])), "modified": len(changes.get("modified_files", [])), "deleted": len(changes.get("deleted_files", [])), "count_updates": changes.get("count_changes", [])},
        "defensive": {"fm_missing": len(fm_issues), "data_conflicts": len(data_issues)},
        "offensive": {
            "gap_tasks": gap_tasks,
            "timeliness": timeliness_tasks,
            "shallow_notes": shallow_notes,
            "wikilink_missing": len(wikilink_missing),
        },
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 基础扫描完成。")

    return result


if __name__ == "__main__":
    main()
