"""全局配置：读取 .env，集中管理环境变量与路径。

设计说明：与项目一（ticket-agent）保持同一套配置风格——
密钥、模型、阈值、路径全部收敛在此，业务代码不散落魔法值。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"                    # 示例简历 / JD
UPLOAD_DIR = DATA_DIR / "uploads"                     # Web 上传的简历与 JD（按批次目录存放）
REPORT_DIR = DATA_DIR / "reports"                     # 导出的筛选报告（CSV/JSON）
AGENT_WORKSPACE = DATA_DIR / "agent_workspace"        # Agent 隔离工作目录（Harness 的 cwd）
SESSION_ROOT = DATA_DIR / "sessions"                  # Harness 会话 JSONL 日志（审计用）
CORDIS_CONFIG = PROJECT_ROOT / "agent" / "cordis.yml"

# ---------------------------------------------------------------------------
# 模型相关（与 DeepSeek Harness Python SDK 对齐）
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "")   # 留空 = 官方公开端点
DSH_MODEL = os.getenv("DSH_MODEL", "deepseek-chat")
DSH_MAX_TOKENS = int(os.getenv("DSH_MAX_TOKENS", "8192"))

# ---------------------------------------------------------------------------
# 评分阈值（规则引擎 + Agent 复核共用）
# ---------------------------------------------------------------------------
SCORE_RECOMMEND = int(os.getenv("SCORE_RECOMMEND", "75"))   # >= 该分：推荐面试
SCORE_PENDING = int(os.getenv("SCORE_PENDING", "50"))       # 50-74：待定；<50：建议淘汰
MAX_SEMANTIC_ADJUST = int(os.getenv("MAX_SEMANTIC_ADJUST", "10"))  # Agent 语义复核最多调整的分值

# 简历/报告相关
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))        # 上传文件大小上限（MB）
