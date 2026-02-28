# oh-my-codex (OMX) 日本語README

> 完全な原文は [English README](./README.md) を参照してください。

OMX は OpenAI Codex CLI 向けのマルチエージェント・オーケストレーションレイヤーです。

## クイックスタート

```bash
npm install -g oh-my-codex
omx setup
omx doctor
```

## 主な機能

- ロールプロンプト（`/prompts:name`）による専門エージェント実行
- ワークフロースキル（`$name`）による反復作業の自動化
- tmux ベースのチーム実行（`omx team`, `$team`）
- MCP サーバーによる状態・メモリの永続化

## 主なコマンド

```bash
omx
omx setup
omx doctor
omx team <args>
omx status
omx cancel
```

## 詳細情報

- メインドキュメント: [README.md](./README.md)
- ウェブサイト: https://yeachan-heo.github.io/oh-my-codex-website/
