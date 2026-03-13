# debug_report_exam_generation_dataset_label_and_rerank

## 1. 问题现象与影响范围
- AI 出题页的知识库选择区和历史记录区显示的是知识库 ID，不是名称。
- 点击生成后任务失败，历史记录报错 `_merge_and_rerank_candidates() missing 1 required keyword-only argument: 'enable_rerank'`。
- 影响范围：`/admin/exam-generation` 后台页、`/api/v1/exam-admin/*` 出题链路。

## 2. 根因证据链（含被排除假设）
- 根因一：`app/services/exam_template_service.py` 原实现直接把 `label=item` 返回，所以前端天然只能显示 ID。
- 根因二：`app/ai/tools/ragflow_tool.py` 的 `_merge_and_rerank_candidates(...)` 已升级为要求 `enable_rerank`，但 `app/ai/workflow/exam_generation_workflow.py` 调用方未同步。
- 已排除：
  - 前后端未启动；
  - 管理员鉴权失败；
  - 数据集未配置；
  - 数据库表缺失（上一轮已修复迁移）。

## 3. 修复内容（文件 / 符号 / 摘要）
- `app/services/exam_template_service.py`
  - 新增 RAGFlow `GET /datasets` 元信息解析；
  - 新增 `get_dataset_label_map(...)` / `resolve_dataset_labels(...)`；
  - `list_available_datasets()` 改为优先返回知识库名称。
- `app/services/exam_generation_service.py`
  - `ExamGenerationJobSummary` 输出新增 `dataset_labels`；
  - 历史记录列表先批量取 label map，再按 job 复用，避免 N 次重复请求。
- `app/ai/workflow/exam_generation_workflow.py`
  - 调用 `_merge_and_rerank_candidates(...)` 时补 `enable_rerank=True`，恢复多数据集优先级语义。
- `web/src/components/admin/ExamGenerationPanel.tsx`
  - 历史记录区优先显示 `dataset_labels`，拿不到再回退 `dataset_ids`。

## 4. 验证命令与结果（失败 -> 通过）
- `bash scripts/pytest_targeted.sh tests/unit/test_exam_template_service.py tests/unit/test_exam_generation_workflow.py tests/unit/test_exam_generation_service.py tests/api/test_exam_admin_api.py -q`
  - 结果：`12 passed`
- `python3 scripts/docs_guard.py --strict`
  - 结果：`errors=0`，仅历史 allowlist warning
- `pnpm --dir web exec tsc --noEmit`
  - 结果：通过
- `pnpm --dir web exec playwright test e2e/features/admin-exam-generation.feature.cjs --project=chromium`
  - 结果：`1 passed`
- `pnpm --dir web exec eslint ...`
  - 结果：受主目录现有依赖环境影响失败：`@next/eslint-plugin-next` 缺失；非本次变更新增问题

## 5. 风险、回滚点与后续建议
- 风险：RAGFlow 元信息接口异常时，页面会回退显示 ID，但不会阻断出题链路。
- 回滚点：撤回 `exam_template_service` 的数据集名称解析与 `dataset_labels` 字段即可恢复旧口径。
- 建议：
  - 若管理后台数据集较多，可后续增加短 TTL 缓存；
  - 若你现在要立即在浏览器里验证，请重启主目录后端/前端或等待热重载生效后刷新页面。
