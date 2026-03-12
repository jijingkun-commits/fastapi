# `/jjk-clarify` 项目主模板（requirements）

## `requirements.md` 最小骨架

```markdown
# <Topic> Requirements

## Meta
- topic:
- source:
- status: draft|approved
- publish_product_doc: false

## Problem Statement
- 当前问题:
- 为什么现在要做:

## Target Users
- 目标用户:
- 非目标用户:

## Core Scenarios
- 场景 1:
- 场景 2:

## In Scope
- 本次必须做:

## Out Of Scope
- 本次明确不做:

## Functional Requirements
- FR-001:
- FR-002:

## Non-Functional Requirements
- NFR-001:
- NFR-002:

## Business Acceptance Criteria
- BAC-001:
- BAC-002:

## Constraints And Assumptions
- 约束:
- 假设:

## Approval
- requirements_approved: true|false
- approved_at:
- approval_evidence:
```

## `--doc` 发布提示

```markdown
- publish_product_doc: true|false
- true  -> 需要把本次需求收敛到正式产品/需求文档对应章节
- false -> 只保留内部 requirements 真理源
```
