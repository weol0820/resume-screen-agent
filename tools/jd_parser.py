"""JD 解析工具：从岗位 JD 文本中规则提取需求清单。

输出三部分：
- hard_requirements：硬性条件（学历 / 年限 / 专业），用于一票否决检查；
- skills：技能关键词清单（来自内置词典，可自行扩充）；
- bonus：加分项（含“优先/加分”字样的条目）。

说明：词典式提取简单可解释；未收录的技能由 Agent 语义复核兜底。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# 技能词典（按需扩充；alias 用于兼容简历里的不同写法）
# ---------------------------------------------------------------------------
SKILLS = [
    "Python", "Java", "SpringBoot", "Spring", "MyBatis", "MySQL", "Oracle", "Redis",
    "Linux", "Docker", "Git", "Nginx", "Vue", "React", "JavaScript", "HTML", "CSS",
    "SQL", "FastAPI", "Django", "Flask", "Pandas", "NumPy", "PyTorch", "Kafka",
    "微服务", "RESTful", "HTTP", "JSON", "大模型", "Agent", "Prompt",
    "RAG", "向量检索", "工具调用", "机器学习", "深度学习", "NLP", "MCP",
]

ALIASES = {
    "SpringBoot": ("spring boot", "springboot"),
    "JavaScript": ("js",),
    "大模型": ("LLM", "大语言模型"),
    "RAG": ("检索增强",),
}

EDU_LEVEL_RE = re.compile(r"(博士|硕士|研究生|本科|大专|专科)(?:及以上|或以上|以上)?")
YEARS_REQ_RE = re.compile(r"(\d{1,2})\s*年\s*(?:以上)?\s*(?:相关)?(?:工作)?经验")
MAJOR_REQ_RE = re.compile(r"(计算机|软件|电子信息|通信|自动化|人工智能|数学)[^，。；\n]{0,10}(?:相关)?专业")


def parse_jd(text: str) -> dict:
    """解析 JD 文本，返回需求清单。"""
    hard: list[dict] = []

    edu = EDU_LEVEL_RE.search(text)
    if edu:
        hard.append({"type": "education", "value": edu.group(1), "raw": edu.group(0),
                     "note": f"学历要求：{edu.group(0)}"})

    years = YEARS_REQ_RE.search(text)
    if years:
        hard.append({"type": "years", "value": int(years.group(1)), "raw": years.group(0),
                     "note": f"经验要求：{years.group(0)}"})

    major = MAJOR_REQ_RE.search(text)
    if major:
        hard.append({"type": "major", "value": major.group(1), "raw": major.group(0),
                     "note": f"专业要求：{major.group(0)}"})

    lower = text.lower()
    skills = [s for s in SKILLS if s.lower() in lower]

    bonus = [line.strip() for line in re.split(r"[；;\n]", text)
             if ("优先" in line or "加分" in line) and len(line.strip()) <= 60]

    return {"hard_requirements": hard, "skills": skills, "bonus": bonus}


def parse_jd_file(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JD 文件不存在：{path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {"file": str(path.resolve()), "text": text, **parse_jd(text)}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="解析 JD 文件")
    parser.add_argument("--file", required=True, help="JD 文件路径")
    args = parser.parse_args()
    try:
        print(json.dumps(parse_jd_file(args.file), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
