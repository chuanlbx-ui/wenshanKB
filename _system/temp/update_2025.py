#!/usr/bin/env python3
"""
文山知识库2025年数据批量更新脚本
从主数据表读取2025年最新数据，更新所有笔记中的相关指标
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set

# 配置
KB_PATH = r"D:\WenShanKB"
DATA_FILE = os.path.join(KB_PATH, "_system", "wenshan_data.json")
OUTPUT_REPORT = os.path.join(KB_PATH, "_system", "update_report_2025.md")
BACKUP_DIR = os.path.join(KB_PATH, "_system", "backup_2025")

# 创建备份目录
os.makedirs(BACKUP_DIR, exist_ok=True)

# 读取主数据表
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 提取2025年数据
indicators_2025 = {}
for key, value in data["core_indicators"].items():
    if "2025" in value:
        indicators_2025[key] = value["2025"]

print(f"主数据表2025年指标数量: {len(indicators_2025)}")

# 数据映射：指标名 -> 中文描述和更新规则
indicator_mapping = {
    "gdp": {
        "name": "GDP/地区生产总值",
        "patterns": [
            r"GDP\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"(地区生产总值|生产总值)\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"(\d+\.?\d*)\s*亿元\s*\(GDP\)"
        ],
        "value": indicators_2025["gdp"]["value"],
        "unit": indicators_2025["gdp"]["unit"]
    },
    "primary_industry": {
        "name": "第一产业",
        "patterns": [
            r"第一产业\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"第一产业增加值\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "value": indicators_2025["primary_industry"]["value"],
        "unit": indicators_2025["primary_industry"]["unit"]
    },
    "secondary_industry": {
        "name": "第二产业",
        "patterns": [
            r"第二产业\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"第二产业增加值\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "value": indicators_2025["secondary_industry"]["value"],
        "unit": indicators_2025["secondary_industry"]["unit"]
    },
    "tertiary_industry": {
        "name": "第三产业",
        "patterns": [
            r"第三产业\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"第三产业增加值\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "value": indicators_2025["tertiary_industry"]["value"],
        "unit": indicators_2025["tertiary_industry"]["unit"]
    },
    "green_aluminum": {
        "name": "绿色铝产业",
        "patterns": [
            r"绿色铝\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"绿色铝产业\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"绿色铝产值\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "value": indicators_2025["green_aluminum"]["value"],
        "unit": indicators_2025["green_aluminum"]["unit"]
    },
    "panax_notoginseng": {
        "name": "三七中药材",
        "patterns": [
            r"三七\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"三七中药材\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"三七产业\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "value": indicators_2025["panax_notoginseng"]["value"],
        "unit": indicators_2025["panax_notoginseng"]["unit"]
    },
    "tourism": {
        "name": "旅游接待",
        "patterns": [
            r"旅游接待\s*[：:]\s*(\d+\.?\d*)\s*万人次",
            r"旅游人次\s*[：:]\s*(\d+\.?\d*)\s*万人次",
            r"旅游花费\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "visitors": indicators_2025["tourism"]["visitors"],
        "revenue": indicators_2025["tourism"]["revenue"]
    },
    "retail_sales": {
        "name": "社会消费品零售总额",
        "patterns": [
            r"社会消费品零售总额\s*[：:]\s*(\d+\.?\d*)\s*亿元",
            r"零售总额\s*[：:]\s*(\d+\.?\d*)\s*亿元"
        ],
        "value": indicators_2025["retail_sales"]["total"],
        "unit": indicators_2025["retail_sales"]["total_unit"]
    },
    "population": {
        "name": "常住人口",
        "patterns": [
            r"常住人口\s*[：:]\s*(\d+\.?\d*)\s*万人",
            r"人口\s*[：:]\s*(\d+\.?\d*)\s*万人"
        ],
        "value": indicators_2025["population"]["total"],
        "unit": indicators_2025["population"]["total_unit"]
    },
    "gdp_per_capita": {
        "name": "人均GDP",
        "patterns": [
            r"人均GDP\s*[：:]\s*(\d+\.?\d*)\s*元",
            r"人均\s*GDP\s*[：:]\s*(\d+\.?\d*)\s*元"
        ],
        "value": indicators_2025["gdp_per_capita"]["value"],
        "unit": indicators_2025["gdp_per_capita"]["unit"]
    }
}

# 获取所有笔记文件
def get_all_notes() -> List[str]:
    """获取所有笔记文件路径"""
    notes = []
    for root, dirs, files in os.walk(KB_PATH):
        # 跳过_system目录
        if "_system" in root:
            continue
        for file in files:
            if file.endswith(".md") and not file.startswith("_"):
                notes.append(os.path.join(root, file))
    return notes

def backup_file(file_path: str) -> str:
    """备份文件到备份目录"""
    rel_path = os.path.relpath(file_path, KB_PATH)
    backup_path = os.path.join(BACKUP_DIR, rel_path.replace("\\", "_"))
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(file_path, backup_path)
    return backup_path

def update_note_content(content: str, file_path: str) -> Tuple[str, List[Dict]]:
    """
    更新笔记内容中的2025年数据
    返回：(更新后的内容, 更新记录列表)
    """
    updates = []
    new_content = content
    
    # 1. 更新年份标记
    # 将"2024年统计公报"等更新为"2025年统计公报"
    year_patterns = [
        (r"2024\s*年\s*统计公报", "2025年统计公报"),
        (r"2024\s*年\s*数据", "2025年数据"),
        (r"2024\s*年\s*GDP", "2025年GDP"),
        (r"2024\s*年\s*国民经济和社会发展", "2025年国民经济和社会发展"),
    ]
    
    for pattern, replacement in year_patterns:
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, replacement, new_content)
            updates.append({
                "type": "年份更新",
                "old": pattern,
                "new": replacement,
                "note": "更新年份标记"
            })
    
    # 2. 更新具体指标
    for ind_key, ind_info in indicator_mapping.items():
        for pattern in ind_info["patterns"]:
            matches = list(re.finditer(pattern, new_content, re.IGNORECASE))
            for match in matches:
                old_value = match.group(1) if match.groups() else match.group(0)
                
                # 根据指标类型构建新值
                if ind_key == "tourism":
                    if "万人次" in match.group(0):
                        new_value = f"{ind_info['visitors']} 万人次"
                    elif "亿元" in match.group(0):
                        new_value = f"{ind_info['revenue']} 亿元"
                    else:
                        continue
                else:
                    new_value = f"{ind_info['value']} {ind_info['unit']}"
                
                # 替换匹配项
                old_text = match.group(0)
                new_text = old_text.replace(old_value, new_value)
                new_content = new_content.replace(old_text, new_text)
                
                updates.append({
                    "type": "指标更新",
                    "indicator": ind_info["name"],
                    "old": old_text,
                    "new": new_text,
                    "note": f"更新{ind_info['name']}到2025年数据"
                })
    
    # 3. 更新表格中的数据
    # 查找Markdown表格中的数值并更新
    table_pattern = r"(\|.*?\|\n)+"
    tables = re.findall(table_pattern, new_content, re.MULTILINE)
    
    for table in tables:
        updated_table = table
        for ind_key, ind_info in indicator_mapping.items():
            # 在表格行中查找指标
            for line in table.split('\n'):
                if '|' in line and any(keyword in line for keyword in [ind_info["name"], ind_key]):
                    # 查找数值并替换
                    num_pattern = r"(\d+\.?\d*)\s*(亿元|万人|元|%)"
                    matches = list(re.finditer(num_pattern, line))
                    for match in matches:
                        old_num = match.group(1)
                        unit = match.group(2)
                        
                        # 根据单位确定要更新的值
                        if unit == "亿元" and ind_key in ["gdp", "primary_industry", "secondary_industry", "tertiary_industry", "green_aluminum", "panax_notoginseng", "retail_sales"]:
                            new_num = str(ind_info.get("value", old_num))
                            new_line = line.replace(f"{old_num} {unit}", f"{new_num} {unit}")
                            updated_table = updated_table.replace(line, new_line)
                            updates.append({
                                "type": "表格更新",
                                "indicator": ind_info["name"],
                                "old": f"{old_num} {unit}",
                                "new": f"{new_num} {unit}",
                                "note": f"更新表格中的{ind_info['name']}"
                            })
        
        if updated_table != table:
            new_content = new_content.replace(table, updated_table)
    
    return new_content, updates

def main():
    """主函数"""
    notes = get_all_notes()
    print(f"找到 {len(notes)} 个笔记文件")
    
    total_updates = 0
    updated_files = []
    update_details = []
    
    for note_path in notes:
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 备份原文件
            backup_path = backup_file(note_path)
            
            # 更新内容
            new_content, updates = update_note_content(content, note_path)
            
            if updates:  # 有更新才写入
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                total_updates += len(updates)
                updated_files.append(note_path)
                update_details.append({
                    "file": os.path.relpath(note_path, KB_PATH),
                    "updates": updates,
                    "count": len(updates)
                })
                
                print(f"✓ {os.path.basename(note_path)}: {len(updates)} 处更新")
            else:
                print(f"  {os.path.basename(note_path)}: 无更新")
                
        except Exception as e:
            print(f"✗ {os.path.basename(note_path)}: 错误 - {str(e)}")
    
    # 生成报告
    report_content = f"""# 文山知识库2025年数据更新报告

**更新日期**: 2026-05-24
**主数据表**: `_system/wenshan_data.json`
**备份目录**: `_system/backup_2025/`

## 统计摘要

- **总笔记数**: {len(notes)} 篇
- **已更新笔记**: {len(updated_files)} 篇
- **总更新次数**: {total_updates} 处
- **备份文件**: {len(updated_files)} 个

## 更新详情

"""
    
    for detail in update_details:
        report_content += f"### {detail['file']} ({detail['count']} 处更新)\n\n"
        for update in detail["updates"]:
            report_content += f"- **{update['type']}**: {update.get('indicator', '年份')}\n"
            report_content += f"  - 原内容: `{update['old'][:50]}...`\n"
            report_content += f"  - 新内容: `{update['new'][:50]}...`\n"
            report_content += f"  - 说明: {update['note']}\n\n"
    
    report_content += f"""
## 未更新笔记 ({len(notes) - len(updated_files)} 篇)

"""
    
    updated_set = set(updated_files)
    for note in notes:
        if note not in updated_set:
            rel_path = os.path.relpath(note, KB_PATH)
            report_content += f"- {rel_path}\n"
    
    # 写入报告
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n{'='*50}")
    print(f"更新完成!")
    print(f"更新报告: {OUTPUT_REPORT}")
    print(f"备份文件: {BACKUP_DIR}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()