"""FastAPI Web 层：简历/JD 上传 + Agent 初筛 + 报告导出。

流程：
    上传简历（.pdf/.docx/.txt）与 JD（文件或文本） → 存到 data/uploads/<批次>/
    → 交给 Agent 初筛（规则引擎 + LLM 复核） → 结果展示
    → 报告落盘 data/reports/<批次>/（JSON + CSV，CSV 用 Excel 打开不乱码）
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from agent.runner import agent
from tools import report_export

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for d in (config.UPLOAD_DIR, config.REPORT_DIR, config.SAMPLES_DIR):
        d.mkdir(parents=True, exist_ok=True)
    yield
    agent.close()


app = FastAPI(title="智能简历初筛 Agent", version="0.1.0", lifespan=lifespan)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/api/evaluate")
async def evaluate(resume: UploadFile = File(...),
                   jd_file: UploadFile | None = File(default=None),
                   jd_text: str = Form(default="")):
    """上传简历与 JD，交给 Agent 完成初筛并导出报告。

    JD 支持两种输入：上传文件（jd_file）或直接粘贴文本（jd_text），二选一即可。
    """
    batch = uuid.uuid4().hex[:10]
    batch_dir = config.UPLOAD_DIR / batch
    batch_dir.mkdir(parents=True, exist_ok=True)

    # 1. 保存简历（限制大小，扩展名用原始后缀）
    content = await resume.read()
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        return {"ok": False, "message": f"简历文件超过 {config.MAX_UPLOAD_MB}MB 上限"}
    resume_path = batch_dir / f"resume_{resume.filename or 'upload.txt'}"
    resume_path.write_bytes(content)

    # 2. 保存 JD（文件优先，其次文本）
    if jd_file is not None:
        jd_bytes = await jd_file.read()
        jd_path = batch_dir / f"jd_{jd_file.filename or 'jd.txt'}"
        jd_path.write_bytes(jd_bytes)
    elif jd_text.strip():
        jd_path = batch_dir / "jd.txt"
        jd_path.write_text(jd_text.strip(), encoding="utf-8")
    else:
        return {"ok": False, "message": "请上传 JD 文件或粘贴 JD 文本"}

    # 3. Agent 初筛
    result = agent.evaluate(str(resume_path), str(jd_path))
    if not result.get("ok"):
        return result

    # 4. 导出报告（JSON 供程序处理；CSV 供 HR 归档）
    record = {"resume_file": resume.filename, "jd_file": jd_file.filename if jd_file else "jd.txt",
              **result}
    report_dir = config.REPORT_DIR / batch
    report_dir.mkdir(parents=True, exist_ok=True)
    report_export.export_json(record, report_dir / "report.json")
    report_export.export_csv([record], report_dir / "report.csv")
    result["report_csv"] = f"/api/reports/{batch}/report.csv"
    result["report_json"] = f"/api/reports/{batch}/report.json"
    return result


@app.get("/api/reports/{batch}/{filename}")
def download_report(batch: str, filename: str) -> FileResponse:
    """下载筛选报告（batch 来自评估接口返回的链接）。"""
    path = config.REPORT_DIR / batch / filename
    if not path.exists():
        return FileResponse(STATIC_DIR / "index.html", status_code=404)
    return FileResponse(str(path), filename=filename)


@app.get("/api/health")
def health():
    return {"status": "ok"}
