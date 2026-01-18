---
description: 启动开发服务器
---

# 启动开发服务器

// turbo
1. 设置环境为开发模式：
```bash
export ENV=dev
```

// turbo
2. 启动 uvicorn 服务器：
```bash
cd /Users/jijingkun/bojxAI/fastapi && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. 访问 API 文档：http://localhost:8000/docs
