# Review 是否应该集成到 CardRun 分析

## 问题

是否应该把 `/jjk-review` 集成到 `/jjk-cardrun` 中，在 verify 不通过时自动触发重写？

---

## 当前架构

### 现状流程

```
/jjk-cardrun
  ↓
  选卡 (wt-flow.sh next)
  ↓
  执行实现 (/jjk-imp-ws)
  ↓
  验收门禁 (wt-flow.sh verify)
    ├─ 执行 acceptance_checks
    ├─ 全部通过 → verified
    └─ 有失败 → CARDRUN_DONE_GATE_FAILED (阻断)
  ↓
  合并 (wt-flow.sh merge)
  ↓
  done
```

### wt-flow.sh verify 的职责

**当前实现**（scripts/coder4/wt-flow.sh）：
1. 读取 `vk_cards.json` 中的 `acceptance_checks`
2. 在 worktree 内执行每条检查命令
3. 收集执行结果（pass/fail/blocked）
4. 全部通过 → 标记 `verified`
5. 有失败 → 输出错误并 exit 1

**特点**：
- ✅ 轻量级：只执行命令，不做代码审查
- ✅ 自动化：完全机器可验证
- ✅ 快速反馈：秒级完成
- ❌ 无人工审查：不检查代码质量、安全性、架构合理性

### /jjk-review 的职责

**当前定位**（.cursor/commands/jjk-review.md）：
1. **四维审查**：功能正确性、代码质量、安全稳定性、测试文档一致性
2. **证据校验**：核验 `acceptance_cmds` 执行结果
3. **发现分级**：P0（阻断）、P1（高优先）、P2（中优先）、P3（优化建议）
4. **结论输出**：PASS / CONDITIONAL_PASS / BLOCKED
5. **产物回填**：`review_report_<topic>.md`

**特点**：
- ✅ 深度审查：代码质量、架构、安全
- ✅ 人工智能：AI 辅助发现潜在问题
- ✅ 可追溯：生成审查报告
- ❌ 耗时较长：需要读取代码、分析、生成报告

---

## 核心问题分析

### 问题 1：verify 和 review 的本质区别

| 维度 | wt-flow.sh verify | /jjk-review |
|------|-------------------|-------------|
| **目标** | 验收门禁（功能是否达标） | 代码审查（质量是否合格） |
| **输入** | `acceptance_checks` 命令 | PR diff / manifest |
| **执行方式** | 机器自动执行命令 | AI 分析代码 |
| **输出** | pass/fail（二元） | PASS/CONDITIONAL_PASS/BLOCKED（三元） |
| **耗时** | 秒级 | 分钟级 |
| **可自动化** | 100% | 部分（需人工确认） |
| **职责** | 功能验收 | 质量把关 |

**结论**：**verify 和 review 是两个不同层次的门禁**
- verify = 功能验收（Does it work?）
- review = 质量审查（Is it good?）

### 问题 2：是否应该在 verify 失败时自动触发 review？

**答案：不应该**

**理由**：
1. **逻辑倒置**：verify 失败说明功能未达标，此时做 review 没有意义
2. **浪费资源**：review 耗时较长，在功能未通过时执行是浪费
3. **职责混淆**：verify 是"功能门禁"，review 是"质量门禁"，不应混为一谈

**正确流程**：
```
verify 失败 → 修复功能 → 重新 verify → verify 通过 → review
```

### 问题 3：是否应该在 verify 通过后自动触发 review？

**答案：可选，但不强制**

**支持自动触发的场景**：
- ✅ 高风险改动（涉及 API/DB/权限/跨端协议）
- ✅ 大范围改动（>= 20 文件或 >= 4 模块）
- ✅ 团队协作场景（需要正式审查记录）

**不需要自动触发的场景**：
- ❌ 小改动（1-3 文件，< 100 行）
- ❌ 紧急修复（hotfix）
- ❌ 个人实验性开发

---

## 方案对比

### 方案 A：强制集成（不推荐）

```
/jjk-cardrun
  ↓
  执行实现
  ↓
  verify (acceptance_checks)
    ├─ 失败 → 阻断
    └─ 通过 ↓
  review (强制)
    ├─ BLOCKED → 触发重写 → 回到执行实现
    ├─ CONDITIONAL_PASS → 记录后续工单 → merge
    └─ PASS → merge
```

**优点**：
- ✅ 质量保证：每张卡都经过审查

**缺点**：
- ❌ 效率低下：小改动也要走完整审查
- ❌ 灵活性差：无法跳过审查
- ❌ 成本高：AI 调用次数大幅增加
- ❌ 职责混淆：cardrun 变成"执行+审查"混合体

### 方案 B：可选集成（推荐）

```
/jjk-cardrun [--with-review]
  ↓
  执行实现
  ↓
  verify (acceptance_checks)
    ├─ 失败 → 阻断
    └─ 通过 ↓
  [可选] review (仅当 --with-review 或满足触发条件)
    ├─ BLOCKED → 触发重写 → 回到执行实现
    ├─ CONDITIONAL_PASS → 记录后续工单 → merge
    └─ PASS → merge
  ↓
  merge
```

**触发条件**（自动判定）：
1. 显式参数：`/jjk-cardrun --with-review`
2. 高风险改动：涉及 `app/ai/state.py`、`*_graph.py`、`app/api/**`
3. 大范围改动：`>= 20` 文件或 `>= 4` 模块
4. 配置开关：`vk_cards.json.cards[].require_review: true`

**优点**：
- ✅ 灵活可控：小改动快速通过，大改动强制审查
- ✅ 职责清晰：verify 负责功能，review 负责质量
- ✅ 成本可控：只在必要时触发审查
- ✅ 向后兼容：不影响现有流程

**缺点**：
- ⚠️ 需要维护触发规则

### 方案 C：完全分离（当前状态）

```
/jjk-cardrun
  ↓
  执行实现
  ↓
  verify
  ↓
  merge

（人工决策是否需要 review）
/jjk-review
```

**优点**：
- ✅ 职责最清晰：cardrun 只管执行，review 独立调用
- ✅ 最灵活：完全由人工决策

**缺点**：
- ❌ 容易遗漏：可能忘记执行 review
- ❌ 无自动化：需要人工判断何时需要 review

---

## 推荐方案

### 采用方案 B（可选集成）+ 智能触发

#### 实现要点

**1. 在 vk_cards.json 中增加 review 配置**

```json
{
  "cards": [
    {
      "card_id": "C01",
      "require_review": true,  // 新增字段
      "review_trigger": "auto", // auto | manual | skip
      "acceptance_checks": [...]
    }
  ]
}
```

**2. 在 cardrun 中增加 review 触发逻辑**

```bash
# jjk-cardrun 伪代码
after_verify_pass() {
  local card_id="$1"
  local require_review=$(jq -r ".cards[] | select(.card_id==\"$card_id\") | .require_review // false" vk_cards.json)

  # 判断是否需要 review
  if [[ "$require_review" == "true" ]] || should_auto_trigger_review "$card_id"; then
    echo "触发 review..."
    /jjk-review --card-id="$card_id"

    local review_result=$(cat review_report_*.md | grep "^结论:" | awk '{print $2}')
    case "$review_result" in
      BLOCKED)
        echo "CARDRUN_REVIEW_BLOCKED: 需要修复后重新执行"
        return 1
        ;;
      CONDITIONAL_PASS)
        echo "CARDRUN_REVIEW_CONDITIONAL_PASS: 记录后续工单"
        # 继续 merge
        ;;
      PASS)
        echo "CARDRUN_REVIEW_PASS"
        # 继续 merge
        ;;
    esac
  fi
}

should_auto_trigger_review() {
  local card_id="$1"
  local changed_files=$(git diff --name-only origin/master)
  local file_count=$(echo "$changed_files" | wc -l)

  # 规则 1: 大范围改动
  if [[ "$file_count" -ge 20 ]]; then
    return 0
  fi

  # 规则 2: 高风险文件
  if echo "$changed_files" | grep -qE "app/ai/state.py|_graph.py|app/api/"; then
    return 0
  fi

  # 规则 3: 显式参数
  if [[ "$CARDRUN_WITH_REVIEW" == "true" ]]; then
    return 0
  fi

  return 1
}
```

**3. review 失败时的重写流程**

```bash
# 当 review 返回 BLOCKED 时
if [[ "$review_result" == "BLOCKED" ]]; then
  # 1. 输出阻断原因
  cat review_report_*.md | grep -A 10 "^## 发现清单"

  # 2. 提示修复命令
  echo "建议执行: /jjk-debug 或 /jjk-imp-ws @<ws_file>"

  # 3. 保持 worktree 和分支，不自动清理
  # 4. 状态回退到 in_progress
  wt-flow.sh update-status "$card_id" "in_progress"

  # 5. 等待人工修复后重新执行 cardrun
  exit 1
fi
```

#### 使用示例

```bash
# 默认模式（自动判断是否需要 review）
/jjk-cardrun 2026-03-01_用户记忆 once

# 强制 review 模式
CARDRUN_WITH_REVIEW=true /jjk-cardrun 2026-03-01_用户记忆 once

# 跳过 review 模式（紧急修复）
CARDRUN_SKIP_REVIEW=true /jjk-cardrun 2026-03-01_hotfix once
```

---

## 总结

### 核心观点

1. **verify 和 review 是两个不同层次的门禁**
   - verify = 功能验收（必须）
   - review = 质量审查（可选）

2. **不应该在 verify 失败时触发 review**
   - 功能未达标时做质量审查没有意义

3. **应该在 verify 通过后可选触发 review**
   - 高风险/大范围改动自动触发
   - 小改动可跳过

### 推荐实现

✅ **采用方案 B（可选集成）**

**关键改动**：
1. `vk_cards.json` 增加 `require_review` 字段
2. `jjk-cardrun` 增加 review 触发逻辑（智能判断）
3. review BLOCKED 时保持 worktree，回退状态到 `in_progress`
4. 支持环境变量控制：`CARDRUN_WITH_REVIEW` / `CARDRUN_SKIP_REVIEW`

**优势**：
- 灵活可控
- 职责清晰
- 成本可控
- 向后兼容

---

**日期**：2026-03-05
**分析者**：Claude Opus 4.6
