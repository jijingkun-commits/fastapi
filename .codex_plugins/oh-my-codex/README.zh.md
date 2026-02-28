# oh-my-codex (OMX) — 简体中文

> 英文原版 README： [README.md](./README.md)

`oh-my-codex (OMX)` 是 [OpenAI Codex CLI](https://github.com/openai/codex) 的多智能体编排层。

## 快速开始

```bash
npm install -g oh-my-codex
omx setup
omx doctor
```

推荐启动参数：

```bash
omx --xhigh --madmax
```

## OMX 提供的能力

- 角色提示词（`/prompts:name`）
- 工作流技能（`$name`）
- 基于 tmux 的团队编排（`omx team`, `$team`）
- 基于 `.omx/` 的状态与记忆持久化

## 常用命令

```bash
omx
omx setup
omx doctor
omx team <args>
omx status
omx cancel
```

更多细节请参考英文文档 [README.md](./README.md)。
