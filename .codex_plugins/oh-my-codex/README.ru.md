# oh-my-codex (OMX) README на русском

> Полная оригинальная документация: [English README](./README.md).

OMX — это слой оркестрации мультиагентной работы для OpenAI Codex CLI.

## Быстрый старт

```bash
npm install -g oh-my-codex
omx setup
omx doctor
```

## Ключевые возможности

- Запуск специализированных агентов через role prompts (`/prompts:name`)
- Автоматизация повторяемых процессов через skills (`$name`)
- Командная оркестрация в tmux (`omx team`, `$team`)
- Постоянное хранение состояния и памяти через MCP-серверы

## Основные команды

```bash
omx
omx setup
omx doctor
omx team <args>
omx status
omx cancel
```

## Подробнее

- Основной документ: [README.md](./README.md)
- Сайт: https://yeachan-heo.github.io/oh-my-codex-website/
