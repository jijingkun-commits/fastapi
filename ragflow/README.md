# RAGFlow 企业知识库

独立部署的 RAGFlow 知识库服务，复用主项目的 PostgreSQL 和 MinIO。

## 📁 目录结构

```
/Users/jijingkun/bojxAI/
├── fastapi/                    # 主项目
│   ├── docker-compose.yml      # postgres + minio + app + web
│   └── ...
│
└── fastapi/ragflow/            # RAGFlow 独立目录
    ├── docker-compose.yml      # ragflow + es + redis
    ├── .env                    # 配置文件
    └── README.md               # 本文件
```

## 🚀 启动步骤

```bash
# 1. 先启动主项目基础服务（创建共享网络）
cd /Users/jijingkun/bojxAI/fastapi
docker compose up -d

# 2. 启动 RAGFlow
cd ragflow
docker compose up -d

# 3. 查看日志
docker logs -f ragflow-server --tail 100
```

## 📍 访问地址

| 服务 | 地址 |
|------|------|
| RAGFlow Web UI | http://localhost:80 |
| Elasticsearch | http://localhost:19200 |

## ⚙️ 首次配置

1. 访问 http://localhost:80 注册账号
2. 「用户设置」→「模型提供商」→ 添加 LLM API Key
3. 创建知识库 → 上传文档
4. 复制 **API Key** 和 **知识库 ID** 到主项目 `.env.dev`

## 🔗 与主项目的关系

```
┌─────────────────────────────────────────────────────────┐
│           bojx-shared 共享网络                           │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ fastapi-    │  │ fastapi-    │  │ ragflow-server  │ │
│  │ postgres    │  │ minio       │  │ :80             │ │
│  │ :5432       │  │ :9000       │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│        ▲                ▲                ▲             │
│        │                │                │             │
│        └────────────────┴────────────────┘             │
│                通过共享网络互相访问                      │
└─────────────────────────────────────────────────────────┘
```

## 🛑 停止服务

```bash
cd /Users/jijingkun/bojxAI/fastapi/ragflow
docker compose down

# 清理数据（慎用）
docker compose down -v
```
