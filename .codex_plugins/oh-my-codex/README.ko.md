# oh-my-codex (OMX) 한국어 README

> 전체 원문 문서는 [English README](./README.md)를 참고하세요.

OMX는 OpenAI Codex CLI를 위한 멀티 에이전트 오케스트레이션 레이어입니다.

## 빠른 시작

```bash
npm install -g oh-my-codex
omx setup
omx doctor
```

## 핵심 기능

- 역할 프롬프트(`/prompts:name`) 기반 전문 에이전트 실행
- 워크플로우 스킬(`$name`) 기반 반복 작업 자동화
- tmux 팀 오케스트레이션(`omx team`, `$team`)
- MCP 서버를 통한 상태/메모리 지속성

## 주요 명령어

```bash
omx
omx setup
omx doctor
omx team <args>
omx status
omx cancel
```

## 더 알아보기

- 메인 문서: [README.md](./README.md)
- 웹사이트: https://yeachan-heo.github.io/oh-my-codex-website/
