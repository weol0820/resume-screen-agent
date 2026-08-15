"""离线演示：不调用大模型，跑通「解析 → 打分」规则引擎全链路。

运行：python demo_tools.py

说明：
- 规则引擎（resume_parser / jd_parser / score_match）是纯 Python 实现，
  无 API Key 也能完整运行——这也是本项目「规则打底、LLM 复核」架构的好处；
- 示例数据里两个 JD 一正一反：AI 应用开发岗（张三匹配较好）与
  Java 后端岗（要求 3 年以上，张三 2 年 → 硬性条件一票否决），
  恰好演示两种筛选结论。
"""

from __future__ import annotations

import json

from tools import jd_parser, resume_parser, score_match
from tools.sample_data import _write_samples


def main() -> None:
    print("=" * 62)
    print("步骤 1/3：生成示例数据（简历 txt/docx + 两个 JD）")
    print("=" * 62)
    print(json.dumps(_write_samples(), ensure_ascii=False, indent=2))

    from config import SAMPLES_DIR
    resume_path = SAMPLES_DIR / "示例简历_张三.docx"
    jd_ai = SAMPLES_DIR / "示例JD_AI应用开发.txt"
    jd_java = SAMPLES_DIR / "示例JD_Java后端.txt"

    print("\n" + "=" * 62)
    print("步骤 2/3：解析简历与 JD（Agent 的 resume_parser / jd_parser 同款逻辑）")
    print("=" * 62)
    basics = resume_parser.extract_basics(resume_parser.extract_text(resume_path))
    print("简历基础信息：", json.dumps(basics, ensure_ascii=False))
    for jd_file in (jd_ai, jd_java):
        parsed = jd_parser.parse_jd_file(jd_file)
        print(f"\n{jd_file.name} → 硬性条件：{json.dumps(parsed['hard_requirements'], ensure_ascii=False)}")
        print(f"  技能清单：{parsed['skills']}")

    print("\n" + "=" * 62)
    print("步骤 3/3：规则引擎打分（Agent 的 score_match 同款逻辑）")
    print("=" * 62)
    for jd_file, tag in ((jd_ai, "正向案例"), (jd_java, "反向案例（一票否决）")):
        result = score_match.score(resume_path, jd_file)
        print(f"\n[{tag}] {jd_file.name}")
        print(f"  总分 {result['total']} = 技能 {result['breakdown']['skills']} "
              f"+ 学历 {result['breakdown']['education']} + 经验 {result['breakdown']['experience']}")
        print(f"  命中技能：{result['matched_skills']}")
        print(f"  缺失技能：{result['missing_skills']}")
        for check in result["hard_checks"]:
            print(f"  硬性检查：{check['note']} → {'通过' if check['passed'] else '不通过'}")
        print(f"  结论：{result['verdict']}   理由：{result['reasons'] or '无'}")

    print("\n规则引擎验证完成 —— 配置 .env 后运行 python run.py，体验 Agent 语义复核与面试问题生成。")


if __name__ == "__main__":
    main()
