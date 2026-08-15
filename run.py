"""一键启动 Web 服务。

用法：
    python run.py
然后浏览器打开 http://127.0.0.1:8000

启动前请确认：
1. python tools/sample_data.py  已生成示例简历与 JD（可选，也可以直接上传自己的文件）；
2. .env 已配置 DEEPSEEK_API_KEY（未配置也能打开页面，但提交初筛会提示先配密钥，
   此时可用 python demo_tools.py 体验规则引擎全链路）。
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000)
