"""规则打分引擎：硬性条件一票否决 + 三维加权评分。

评分公式（满分 100）：
    技能分（60）：JD 要求技能中简历命中比例 × 60
    学历分（20）：博士 20 / 硕士 17 / 本科 14 / 大专及以下 10 / 未知 8
    经验分（20）：简历年限 / JD 要求年限 × 20（封顶 20；JD 未要求时按 3 年经验为满分的比例折算）

结论规则：
    任一硬性条件不满足 → 建议淘汰（一票否决，不因总分放行）
    总分 >= 75 → 推荐面试；50-74 → 待定；< 50 → 建议淘汰

纯 Python 实现，不依赖大模型：结果可复现、可解释、零幻觉，
是“规则打底、LLM 复核”架构中的底座。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from tools import jd_parser, resume_parser  # noqa: E402

EDUCATION_RANK = {"博士": 5, "硕士": 4, "研究生": 4, "本科": 3, "大专": 2, "专科": 2}
EDUCATION_POINTS = {"博士": 20, "硕士": 17, "研究生": 17, "本科": 14, "大专": 10, "专科": 10}

# 专业相关性兜底词：简历文本命中任一即视为“相关专业”
MAJOR_HINTS = ("计算机", "软件", "电子信息", "通信", "自动化", "人工智能", "数据科学", "信息管理")


def _rank(level: str | None) -> int:
    return EDUCATION_RANK.get(level or "", 0)


def _skill_in_text(skill: str, text: str) -> bool:
    """技能命中判断：大小写不敏感 + 别名兼容（如 SpringBoot ↔ spring boot）。"""
    lower_text = text.lower()
    candidates = [skill.lower(), *jd_parser.ALIASES.get(skill, ())]
    return any(c in lower_text for c in candidates)


def _check_hard(hard_requirements: list[dict], basics: dict, resume_text: str) -> list[dict]:
    """硬性条件检查（每条输出 要求/实际/是否通过/备注）。"""
    checks = []
    for req in hard_requirements:
        if req["type"] == "education":
            required = req["value"]
            actual = basics.get("education")
            passed = _rank(actual) >= _rank(required)
            checks.append({"type": "education", "required": required,
                           "actual": actual or "未识别", "passed": passed,
                           "note": f"学历：要求{required}及以上，实际{actual or '未识别'}"})
        elif req["type"] == "years":
            required = int(req["value"])
            actual = basics.get("years")
            passed = actual is not None and float(actual) >= required
            checks.append({"type": "years", "required": required,
                           "actual": actual if actual is not None else "未识别",
                           "passed": passed,
                           "note": f"经验：要求{required}年以上，实际{actual if actual is not None else '未识别'}年"})
        elif req["type"] == "major":
            actual = basics.get("major")
            passed = bool(actual) or any(h in resume_text for h in MAJOR_HINTS)
            checks.append({"type": "major", "required": req["value"],
                           "actual": actual or "未识别", "passed": passed,
                           "note": f"专业：要求{req['value']}相关，实际{actual or '未识别'}"})
    return checks


def score(resume_path: str | Path, jd_path: str | Path) -> dict:
    """对一份简历 + 一份 JD 打分，返回完整可解释结果。"""
    resume = resume_parser.parse_resume(resume_path)
    jd = jd_parser.parse_jd_file(jd_path)
    resume_text = resume["text"]
    basics = resume["basics"]

    hard_checks = _check_hard(jd["hard_requirements"], basics, resume_text)
    hard_failed = [c for c in hard_checks if not c["passed"]]

    # 技能分（60 分制）
    if jd["skills"]:
        matched = [s for s in jd["skills"] if _skill_in_text(s, resume_text)]
        skill_points = round(len(matched) / len(jd["skills"]) * 60, 1)
    else:
        matched, skill_points = [], 36.0  # JD 未列技能时给中性分，交由 LLM 复核
    missing = [s for s in jd["skills"] if s not in matched]

    # 学历分（20 分制）
    edu_points = EDUCATION_POINTS.get(basics.get("education") or "", 8)

    # 经验分（20 分制）
    years_req = next((int(r["value"]) for r in jd["hard_requirements"] if r["type"] == "years"), None)
    actual_years = basics.get("years")
    if years_req:
        exp_points = round(min((actual_years or 0) / years_req, 1.0) * 20, 1)
    else:
        exp_points = round(min((actual_years or 0) / 3, 1.0) * 20, 1)

    total = round(skill_points + edu_points + exp_points, 1)

    if hard_failed:
        verdict = "建议淘汰"
        reasons = [f"硬性条件不满足：{', '.join(c['note'] for c in hard_failed)}"]
    elif total >= config.SCORE_RECOMMEND:
        verdict, reasons = "推荐面试", []
    elif total >= config.SCORE_PENDING:
        verdict, reasons = "待定", []
    else:
        verdict, reasons = "建议淘汰", [f"总分 {total} 低于待定线 {config.SCORE_PENDING}"]

    return {
        "resume_file": str(Path(resume_path).resolve()),
        "jd_file": str(Path(jd_path).resolve()),
        "basics": basics,
        "hard_checks": hard_checks,
        "total": total,
        "breakdown": {"skills": skill_points, "education": edu_points, "experience": exp_points},
        "matched_skills": matched,
        "missing_skills": missing,
        "jd_skills": jd["skills"],
        "jd_bonus": jd["bonus"],
        "verdict": verdict,
        "reasons": reasons,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="规则引擎打分（简历 + JD）")
    parser.add_argument("--resume", required=True, help="简历文件路径")
    parser.add_argument("--jd", required=True, help="JD 文件路径")
    args = parser.parse_args()
    try:
        print(json.dumps(score(args.resume, args.jd), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
