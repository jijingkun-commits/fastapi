# FastAPI AI Assistant

> 基于 FastAPI + LangGraph + Next.js 的智能对话助手，支持多智能体协作、待办管理、知识库检索等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI 0.115 · LangGraph 1.0 · LangChain 1.0 · SQLAlchemy 2.0 |
| **前端** | Next.js 15 · React 19 · TypeScript · TailwindCSS |
| **数据库** | PostgreSQL 16+（pgvector）· MinIO |
| **AI** | Qwen · DeepSeek · OpenAI Compatible |

## 快速开始

```bash
# 启动基础设施
docker compose up -d

# 配置环境
cp .env.example .env.dev
# 编辑 .env.dev 配置 MODEL_API_KEY

# 启动后端
pip install -e ".[dev]"
uvicorn app.main:app --reload

# 启动前端
cd web && pnpm install && pnpm dev
```

访问 `http://localhost:3000` 开始使用。

## 文档

详细文档请查看 [`docs/`](docs/) 目录：

- **[快速入门](docs/开发文档/快速入门/快速开始.md)** - 5 分钟上手
- **[安装部署](docs/开发文档/快速入门/安装部署.md)** - 完整部署指南
- **[架构设计](docs/开发文档/架构设计/系统总览.md)** - 系统架构总览
- **[接口文档](docs/API文档/接口文档.md)** - 接口说明

## 项目结构

```
├── app/                    # 后端核心
│   ├── ai/                 # AI 模块（LangGraph、Agents、Tools）
│   ├── api/                # HTTP API 端点
│   ├── services/           # 业务逻辑层
│   └── repositories/       # 数据访问层
├── web/                    # Next.js 前端
│   ├── src/app/            # App Router 页面
│   └── src/components/     # React 组件
└── docs/                   # 项目文档
```

## License

MIT
