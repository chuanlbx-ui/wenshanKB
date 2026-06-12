"""合规检查服务"""

import re
from typing import Optional


COMPLIANCE_RULES = [
    (re.compile(r"治疗|治愈|药到病除|包治"), "advertising", "high",
     "不得使用医疗治疗效果表述", "改为'辅助调理''传统用于'等表述"),
    (re.compile(r"最好|第一|唯一|最.*的"), "advertising", "high",
     "不得使用绝对化用语", "移除或替换为'知名''优质'等"),
    (re.compile(r"争议领土|未定国界|争议地区"), "border", "high",
     "不得质疑已划定边界", "使用'中越边境'官方表述"),
    (re.compile(r"落后.*(壮族|苗族|彝族|瑶族|民族)|原始.*民族"), "ethnic", "high",
     "不得使用歧视性描述", "改为'传统文化''独特习俗'"),
    (re.compile(r"部队番号|军事部署|兵力|驻军"), "military", "high",
     "不得泄露军事信息", "删除相关信息"),
    (re.compile(r"来源于网络|图片来自网络"), "copyright", "medium",
     "网络素材版权存疑", "使用自有或已授权素材"),
]


def check_text(content: str, categories: Optional[list[str]] = None) -> dict:
    """对文本执行合规检查"""
    if categories is None:
        categories = ["all"]

    issues = []
    warnings = []
    checked = set()

    for pattern, category, severity, description, suggestion in COMPLIANCE_RULES:
        if categories != ["all"] and category not in categories:
            continue
        checked.add(category)

        for match in pattern.finditer(content):
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            item = {
                "category": category, "severity": severity,
                "location": f"位置 {match.start()}: ...{content[start:end]}...",
                "issue": description, "suggestion": suggestion,
            }
            if severity == "high":
                issues.append(item)
            else:
                warnings.append(item)

    score = max(0, 100 - len(issues) * 15 - len(warnings) * 5)
    return {
        "passed": len(issues) == 0,
        "overall_score": score,
        "issues": issues,
        "warnings": warnings,
        "passed_checks": list(checked),
    }
