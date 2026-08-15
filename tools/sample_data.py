"""生成示例简历与示例 JD（.txt / .docx），供演示与离线验证。

运行：python tools/sample_data.py
输出到 data/samples/：
- 示例简历_张三.txt / .docx（2 年 Java 后端，做过一个智能工单小项目）
- 示例JD_AI应用开发.txt（1 年以上、Python/Agent 方向 → 张三匹配较好）
- 示例JD_Java后端.txt（要求 3 年以上 → 张三硬性条件不满足，演示一票否决）

两个 JD 一正一反，恰好演示“推荐面试”与“建议淘汰”两种结果。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402

SAMPLE_RESUME = """张三
求职意向：Java 后端开发 / AI 应用开发
电话：13812345678    邮箱：zhangsan@example.com

教育背景
2021.09 - 2025.06  某大学  计算机科学与技术  本科
主修课程：数据结构、操作系统、数据库原理、计算机网络、机器学习导论

工作/实习经历
2024.07 - 至今  某某科技有限公司  Java 开发实习生
- 参与订单中心微服务开发（SpringBoot + MyBatis + MySQL），负责订单查询接口与缓存优化（Redis）
- 编写单元测试与接口文档，使用 Git 协作、Docker 本地部署环境
- 业余学习大模型与 Agent：了解 Prompt 工程、工具调用、RAG 基本概念，用 Python + FastAPI 做过智能工单处理小项目（调用 DeepSeek API，基于 DeepSeek Harness 编排）

专业技能
- 语言：Java、Python、SQL
- 后端：SpringBoot、Spring、MyBatis、MySQL、Redis、Linux、Docker、Git
- 前端：Vue、JavaScript、HTML、CSS
- AI 方向：了解大模型 API 调用、Prompt 工程、Agent 工具调用与 RAG 基础

自我评价
学习能力强，对 AI Agent 应用开发有强烈兴趣，希望从事大模型应用落地方向的工作。
"""

JD_AI = """AI 应用开发工程师（应届生/1 年以上经验）

岗位职责：
1. 负责大模型 Agent 应用的开发与落地，包括 Prompt 设计、工具调用与检索增强（RAG）；
2. 使用 Python 开发后端服务（FastAPI/Django），对接大模型 API；
3. 参与业务需求分析，将重复人工流程改造成 Agent 自动化流程；
4. 撰写技术文档，配合测试保障线上稳定。

任职要求：
1. 本科及以上学历，计算机相关专业；
2. 1 年以上 Python 开发经验（应届生有实际项目亦可）；
3. 熟悉 Python，了解 LLM、Agent、Prompt、RAG、工具调用等概念；
4. 了解 MySQL、Redis、Docker、Git 等常用工具；
5. 有 AI 应用项目实践经验者优先。

加分项：
- 有 Agent 框架（如 DeepSeek Harness）使用经验者优先；
- 有完整可演示的 AI 项目作品集者优先。
"""

JD_JAVA = """Java 后端开发工程师（3 年以上经验）

岗位职责：
1. 负责核心交易系统的设计与开发（SpringBoot 微服务架构）；
2. 参与 MySQL 分库分表、Redis 缓存与 Kafka 消息队列的优化；
3. 排查线上问题，保障系统高可用。

任职要求：
1. 本科及以上学历，计算机相关专业；
2. 3 年以上 Java 后端开发经验；
3. 精通 SpringBoot、MySQL、Redis，熟悉 Kafka、微服务架构；
4. 有高并发系统实战经验者优先。
"""


def _write_samples() -> dict:
    config.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    created = []

    resume_txt = config.SAMPLES_DIR / "示例简历_张三.txt"
    resume_txt.write_text(SAMPLE_RESUME, encoding="utf-8")
    created.append(str(resume_txt.name))

    # 同步生成一份 docx 版本，演示 python-docx 解析路径
    import docx  # 局部导入
    document = docx.Document()
    for line in SAMPLE_RESUME.splitlines():
        document.add_paragraph(line)
    resume_docx = config.SAMPLES_DIR / "示例简历_张三.docx"
    document.save(str(resume_docx))
    created.append(str(resume_docx.name))

    jd_ai = config.SAMPLES_DIR / "示例JD_AI应用开发.txt"
    jd_ai.write_text(JD_AI, encoding="utf-8")
    created.append(str(jd_ai.name))

    jd_java = config.SAMPLES_DIR / "示例JD_Java后端.txt"
    jd_java.write_text(JD_JAVA, encoding="utf-8")
    created.append(str(jd_java.name))

    return {"samples_dir": str(config.SAMPLES_DIR), "created": created}


if __name__ == "__main__":
    print(json.dumps(_write_samples(), ensure_ascii=False, indent=2))
