"""合规检查端点"""

import re
import time
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.compliance import ComplianceRequest, ComplianceResponse, ComplianceIssue

router = APIRouter()

# 内置合规规则（后续从数据库加载）
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


@router.post("/compliance/check", response_model=ComplianceResponse)
async def check_compliance(
    body: ComplianceRequest,
    auth: dict = Depends(get_current_user),
):
    """合规检查"""
    t0 = time.perf_counter()
    issues = []
    warnings = []
    checked = set()

    for pattern, category, severity, description, suggestion in COMPLIANCE_RULES:
        if body.check_categories != ["all"] and category not in body.check_categories:
            continue
        checked.add(category)

        for match in pattern.finditer(body.content):
            start = max(0, match.start() - 20)
            end = min(len(body.content), match.end() + 20)
            issue = ComplianceIssue(
                category=category, severity=severity,
                location=f"位置 {match.start()}: ...{body.content[start:end]}...",
                issue=description, suggestion=suggestion,
                rule_ref="[[合规指南]]"
            )
            if severity == "high":
                issues.append(issue)
            else:
                warnings.append(issue)

    score = max(0, 100 - len(issues) * 15 - len(warnings) * 5)
    elapsed = int((time.perf_counter() - t0) * 1000)

    return ComplianceResponse(
        passed=len(issues) == 0,
        overall_score=score,
        issues=issues,
        warnings=warnings,
        passed_checks=list(checked),
        check_time_ms=elapsed,
    )
