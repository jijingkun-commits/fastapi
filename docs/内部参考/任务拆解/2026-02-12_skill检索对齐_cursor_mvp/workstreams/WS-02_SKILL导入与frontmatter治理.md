# 工作包说明

> WS 编号: WS-02  
> 名称: SKILL导入与frontmatter治理  
> 类型: Backend（可并行）

---

## 0. 关联文档

1. `docs/内部参考/迭代需求/requirements.md`
2. `docs/内部参考/迭代需求/implementation_plan.md`
3. `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md`

---

## 1. 目标与完成定义

### 1.1 目标

1. 完成 `SKILL.md` frontmatter 到元数据字段的解析与映射。
2. 建立导入校验与幂等更新机制。
3. 保证启动同步失败可观测、可降级。

### 1.2 DoD

1. 解析链路支持合法/缺失/非法三类输入。
2. 重复导入结果一致且无重复写入。
3. 导入日志可定位到 skill_id 与字段级错误。

---

## 2. 文件边界

### 2.1 可修改（白名单）

- `app/services/skill_service.py`
- `app/main.py`
- `tests/unit/test_*skill*`

### 2.2 禁止修改（黑名单）

- `app/models/*`
- `app/ai/workflow/*`
- `web/src/*`

---

## 3. 状态字段单写入权

- WS-02 可写：frontmatter 解析规则、默认值回退逻辑。
- WS-02 只读：检索排序与 runtime 注入策略。

---

## 4. 实施步骤

1. 扩展 `_parse_skill_file` 支持新增字段解析。
2. 增加字段校验、默认值回退与 warning 记录。
3. 完善 `import_skill/import_all_skills` 幂等与错误分级。

---

## 5. 局部验收与最小验证命令

- `venv/bin/python -m pytest -q tests/unit -k "skill and ingest"`

验收标准：

1. frontmatter 合法样本可正确入库。
2. 非法样本不阻断批量导入。

---

## 5.1 浏览器测试触发评估

- 是否触发浏览器测试：否
- 触发依据：本 WS 聚焦导入与服务层逻辑，不涉及前端交互。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：未改 `web/src/**`。

---

## 6. 风险与回滚

- 风险：frontmatter 自由格式导致解析歧义。
- 回滚：保留旧解析策略开关并可快速回退。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## card_export

```yaml
card_export:
  id: WS-02
  card_key: PP-20260213-SKILL-RETRIEVAL-MVP::WS-02
  title: SKILL导入与frontmatter治理
  type: parallel
  lane: lane-backend-ingest
  hard_depends_on:
    - WS-00
    - WS-01
  soft_depends_on: []
  depends_on:
    - WS-00
    - WS-01
  file_whitelist:
    - app/services/skill_service.py
    - app/main.py
  readonly_scope:
    - app/models/
    - app/ai/workflow/
  owner_fields:
    - frontmatter_parse
    - file_hash
    - scope_normalize
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit -k "skill and ingest"
  handoff_artifacts:
    - app/services/skill_service.py
  dod:
    - frontmatter 解析、校验、幂等导入通过
```
