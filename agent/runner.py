"""Agent 运行器：封装 DeepSeek Harness Python SDK（简历初筛场景）。

设计要点：
1. DeepSeekHarness 实例常驻复用（官方 SDK 用法），应用关闭时 close() 回收；
2. 每份简历一个独立 session_id，JSONL 审计日志按简历归档在 data/sessions/；
3. 系统提示词经 DSH_SYSTEM_PROMPT 注入（cordis.yml persona），
   任务提示词携带简历/JD/工具的绝对路径；
4. 双保险结果：模型输出的 JSON（语义复核结论）与 score_match 的规则分
   同时返回，前端并排展示，方便面试时讲清“规则 + 模型”的分工。
"""

from __future__ import annotations

import json
import re
import sys
import uuid

try:
    from deepseek_harness import DeepSeekHarness
    HARNESS_AVAILABLE = True
except ImportError:  # 未安装 SDK，或当前平台没有官方运行时 wheel（如原生 Windows）
    DeepSeekHarness = None  # type: ignore[assignment]
    HARNESS_AVAILABLE = False

import config
from agent.prompts import SYSTEM_PROMPT, build_task_prompt

TOOLS_DIR = str((config.PROJECT_ROOT / "tools").resolve())
PYTHON_BIN = sys.executable

HARNESS_UNAVAILABLE_MSG = (
    "DeepSeek Harness Python SDK 运行时不可用：官方运行时 wheel 支持 Linux x64/arm64 与 macOS 14+ arm64，"
    "Windows 用户请在 WSL2 中运行（安装方式见 README「环境准备」）。"
    "页面与离线规则引擎不受影响，可先运行 python demo_tools.py 体验解析与打分流程。")


def _extract_json(text: str) -> dict | None:
    """从模型最终输出中容错提取 JSON 对象（兼容代码块包裹/前后杂质）。"""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


class ResumeAgent:
    """简历初筛 Agent 门面。"""

    def __init__(self) -> None:
        self._harness: DeepSeekHarness | None = None

    def _ensure(self) -> DeepSeekHarness:
        if not HARNESS_AVAILABLE:
            raise RuntimeError(HARNESS_UNAVAILABLE_MSG)
        if self._harness is None:
            config.AGENT_WORKSPACE.mkdir(parents=True, exist_ok=True)
            config.SESSION_ROOT.mkdir(parents=True, exist_ok=True)

            env_extra: dict[str, str] = {"DSH_SYSTEM_PROMPT": SYSTEM_PROMPT}
            if config.DEEPSEEK_API_KEY:
                env_extra["DEEPSEEK_API_KEY"] = config.DEEPSEEK_API_KEY
            if config.DEEPSEEK_BASE_URL:
                env_extra["DEEPSEEK_BASE_URL"] = config.DEEPSEEK_BASE_URL

            self._harness = DeepSeekHarness(
                provider="deepseek-official",
                model=config.DSH_MODEL,
                max_tokens=config.DSH_MAX_TOKENS,
                cwd=str(config.AGENT_WORKSPACE),
                session_root=str(config.SESSION_ROOT),
                cordis=str(config.CORDIS_CONFIG),
                env=env_extra,
            )
        return self._harness

    def evaluate(self, resume_path: str, jd_path: str) -> dict:
        """对一份简历 + 一份 JD 完成初筛，返回结构化结果。

        返回：
            {
              "ok": bool, "message": str,
              "agent_json": dict|None,      # 模型输出的最终结论
              "agent_text": str,            # 模型最终原文
              "rule_score": dict|None,      # 规则引擎打分（score_match 结果）
              "resume_basics": dict|None,   # 规则提取的简历基础信息
              "session_id": str, "finish_reason": str|None,
            }
        """
        if not HARNESS_AVAILABLE:
            return {"ok": False, "message": HARNESS_UNAVAILABLE_MSG}
        if not config.DEEPSEEK_API_KEY:
            return {"ok": False,
                    "message": "未配置 DEEPSEEK_API_KEY：请复制 .env.example 为 .env 并填写密钥。"
                               "（只想看规则引擎打分可运行 python demo_tools.py）"}

        session_id = f"resume-{uuid.uuid4().hex[:8]}"
        prompt = build_task_prompt(resume_path, jd_path, TOOLS_DIR, PYTHON_BIN)
        try:
            result = self._ensure().run(prompt, session_id=session_id)
        except Exception as exc:
            return {"ok": False, "message": f"Agent 运行失败：{exc}", "session_id": session_id}

        agent_json = _extract_json(result.final_response)

        # 规则分与简历基础信息由本地规则引擎独立给出（不依赖模型，保证可复现）
        from tools import resume_parser, score_match  # 局部导入，保持依赖清晰
        rule_score = None
        resume_basics = None
        try:
            resume_basics = resume_parser.extract_basics(resume_parser.extract_text(resume_path))
            rule_score = score_match.score(resume_path, jd_path)
        except Exception:
            pass  # 规则层异常不阻断主流程，前端会看到 agent_json

        if agent_json is None:
            return {"ok": False, "message": f"Agent 未输出合法 JSON（finish_reason={result.finish_reason}），"
                                            f"请查看会话日志 data/sessions/{session_id}.jsonl",
                    "agent_text": result.final_response, "rule_score": rule_score,
                    "resume_basics": resume_basics, "session_id": session_id,
                    "finish_reason": result.finish_reason}

        return {"ok": True, "message": "初筛完成。", "agent_json": agent_json,
                "agent_text": result.final_response, "rule_score": rule_score,
                "resume_basics": resume_basics, "session_id": session_id,
                "finish_reason": result.finish_reason}

    def close(self) -> None:
        if self._harness is not None:
            self._harness.close()
            self._harness = None


agent = ResumeAgent()
