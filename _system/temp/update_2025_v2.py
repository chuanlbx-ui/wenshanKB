#!/usr/bin/env python3
"""
文山知识库2025年数据批量更新脚本 v2
更智能的内容分析和数据替换
"""

import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path

# 配置
KB_PATH = r"D:\WenShanKB"
DATA_FILE = os.path.join(KB_PATH, "_system", "wenshan_data.json")
OUTPUT_REPORT = os.path.join(KB_PATH, "_system", "update_report_2025_v2.md")
BACKUP_DIR = os.path.join(KB_PATH, "_system", "backup_2025_v2")

# 创建目录
os.makedirs(BACKUP_DIR, exist_ok=True)

# 读取主数据表
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 提取2025年数据
ind_2025 = {k: v["2025"] for k, v in data["core_indicators"].items() if "2025" in v}

# 数据替换映射
data_mapping = {
    # GDP相关
    r"(\d+\.?\d*)\s*亿元\s*\(GDP\)": f"{ind_2025['gdp']['value']} 亿元（GDP）",
    r"GDP\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"GDP：{ind_2025['gdp']['value']} 亿元",
    r"地区生产总值\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"地区生产总值：{ind_2025['gdp']['value']} 亿元",
    
    # 三大产业
    r"第一产业\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"第一产业：{ind_2025['primary_industry']['value']} 亿元",
    r"第二产业\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"第二产业：{ind_2025['secondary_industry']['value']} 亿元", 
    r"第三产业\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"第三产业：{ind_2025['tertiary_industry']['value']} 亿元",
    
    # 重点产业
    r"绿色铝产值\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"绿色铝产值：{ind_2025['green_aluminum']['value']} 亿元",
    r"三七中药材综合产值\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"三七中药材综合产值：{ind_2025['panax_notoginseng']['value']} 亿元",
    r"三七\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"三七：{ind_2025['panax_notoginseng']['value']} 亿元",
    
    # 旅游
    r"旅游接待\s*[：:]\s*(\d+\.?\d*)\s*万人次": f"旅游接待：{ind_2025['tourism']['visitors']} 万人次",
    r"旅游花费\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"旅游花费：{ind_2025['tourism']['revenue']} 亿元",
    
    # 消费
    r"社会消费品零售总额\s*[：:]\s*(\d+\.?\d*)\s*亿元": f"社会消费品零售总额：{ind_2025['retail_sales']['total']} 亿元",
    
    # 人口
    r"常住人口\s*[：:]\s*(\d+\.?\d*)\s*万人": f"常住人口：{ind_2025['population']['total']} 万人",
    
    # 人均GDP
    r"人均GDP\s*[：:]\s*(\d+\.?\d*)\s*元": f"人均GDP：{ind_2025['gdp_per_capita']['value']} 元",
    
    # 年份更新
    r"2024\s*年\s*统计公报": "2025年统计公报",
    r"2024\s*年\s*数据": "2025年数据",
    r"2024\s*年\s*GDP": "2025年GDP",
    r"2024\s*年\s*国民经济和社会发展": "2025年国民经济和社会发展",
}

# 获取所有笔记
def get_notes():
    notes = []
    for root, dirs, files in os.walk(KB_PATH):
        if "_system" in root:
            continue
        for f in files:
            if f.endswith(".md") and not f.startswith("_"):
                notes.append(os.path.join(root, f))
    return notes

def update_note(file_path):
    """更新单个笔记文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    updates = []
    
    # 应用所有替换规则
    for pattern, replacement in data_mapping.items():
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            old_text = match.group(0)
            new_text = re.sub(pattern, replacement, old_text, flags=re.IGNORECASE)
            content = content.replace(old_text, new_text)
            
            # 记录更新
            if old_text != new_text:
                updates.append({
                    "old": old_text,
                    "new": new_text,
                    "pattern": pattern
                })
    
    # 更新frontmatter中的年份
    if "tags:" in content:
        # 查找tags中的年份
        tags_match = re.search(r"tags:\s*\[(.*?)\]", content, re.DOTALL)
        if tags_match:
            tags_text = tags_match.group(1)
            if "2024" in tags_text:
                new_tags = tags_text.replace("2024", "2025")
                content = content.replace(tags_text, new_tags)
                updates.append({
                    "old": tags_text,
                    "new": new_tags,
                    "pattern": "tags更新"
                })
    
    # 更新标题中的年份
    title_match = re.search(r"#\s+(.*?)\s*（\s*(\d{4})\s*年", content)
    if title_match:
        title_text = title_match.group(0)
        if "2024" in title_text:
            new_title = title_text.replace("2024", "2025")
            content = content.replace(title_text, new_title)
            updates.append({
                "old": title_text,
                "new": new_title,
                "pattern": "标题年份更新"
            })
    
    return content, updates, original != content

def main():
    notes = get_notes()
    print(f"找到 {len(notes)} 个笔记文件")
    
    total_updated = 0
    update_details = []
    
    for note_path in notes:
        # 备份
        rel_path = os.path.relpath(note_path, KB_PATH)
        backup_path = os.path.join(BACKUP_DIR, rel_path.replace("\\", "_"))
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(note_path, backup_path)
        
        # 更新
        new_content, updates, changed = update_note(note_path)
        
        if changed:
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            total_updated += 1
            update_details.append({
                "file": rel_path,
                "updates": updates,
                "count": len(updates)
            })
            
            print(f"✓ {os.path.basename(note_path)}: {len(updates)} 处更新")
        else:
            print(f"  {os.path.basename(note_path)}: 无更新")
    
    # 生成报告
    report = f"""# 文山知识库2025年数据更新报告 (v2)

**更新日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**主数据表**: `_system/wenshan_data.json`
**备份目录**: `_system/backup_2025_v2/`

## 统计摘要

- **总笔记数**: {len(notes)} 篇
- **已更新笔记**: {total_updated} 篇
- **总更新次数**: {sum(d['count'] for d in update_details)} 处

## 更新详情

"""
    
    for detail in update_details:
        report += f"### {detail['file']} ({detail['count']} 处更新)\n\n"
        for i, update in enumerate(detail['updates'], 1):
            report += f"{i}. **{update.get('pattern', '内容更新')}**\n"
            report += f"   - 原内容: `{update['old'][:80]}`\n"
            report += f"   - 新内容: `{update['new'][:80]}`\n\n"
    
    # 写入报告
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n{'='*60}")
    print(f"更新完成! 共更新 {total_updated}/{len(notes)} 篇笔记")
    print(f"更新报告: {OUTPUT_REPORT}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()