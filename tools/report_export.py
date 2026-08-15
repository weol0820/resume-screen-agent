"""筛选报告导出：CSV（Excel 可直接打开）+ JSON。

CSV 使用 utf-8-sig 编码，解决 Excel 打开中文乱码问题。
Web 层在 Agent 完成初筛后调用本模块落盘报告，供 HR 批量归档。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CSV_COLUMNS = ["姓名", "邮箱", "学历", "工作年限", "规则分", "总分", "结论",
               "命中技能", "缺失技能", "优点", "疑虑", "面试问题", "摘要"]


def _csv_row(record: dict) -> list:
    """把一条评估记录压平成 CSV 行（列表类字段用顿号连接）。"""
    basics = record.get("basics") or {}
    agent_json = record.get("agent_json") or {}

    def join_list(value):
        return "、".join(str(v) for v in value) if isinstance(value, list) else (value or "")

    return [
        basics.get("name") or "", basics.get("email") or "",
        basics.get("education") or "", basics.get("years") or "",
        (record.get("rule_score") or {}).get("total", ""),
        agent_json.get("total_score", ""),
        agent_json.get("verdict", ""),
        join_list(agent_json.get("matched_skills")),
        join_list(agent_json.get("missing_skills")),
        join_list(agent_json.get("strengths")),
        join_list(agent_json.get("concerns")),
        join_list(agent_json.get("interview_questions")),
        agent_json.get("summary", ""),
    ]


def export_csv(records: list[dict], out_path: str | Path) -> Path:
    """批量导出筛选记录为 CSV。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for record in records:
            writer.writerow(_csv_row(record))
    return out_path


def export_json(payload: dict, out_path: str | Path) -> Path:
    """导出完整评估 JSON（含规则分与 Agent 结论，便于程序化处理）。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出筛选报告")
    parser.add_argument("--data", required=True, help="评估记录 JSON 字符串（数组或对象）")
    parser.add_argument("--out", required=True, help="输出文件路径（.csv 或 .json）")
    args = parser.parse_args()
    try:
        data = json.loads(args.data)
        records = data if isinstance(data, list) else [data]
        if str(args.out).endswith(".csv"):
            path = export_csv(records, args.out)
        else:
            path = export_json(data, args.out)
        print(json.dumps({"exported": str(path.resolve())}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
