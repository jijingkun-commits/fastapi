# Debug Report：聊天会话切换首击失效与历史点击不稳定（2026-03-07）

## 1. 问题现象与影响范围

- 现象 A：在已有会话里点击“新建会话”，第一次会回到当前会话（或刷新当前会话），需要第二次才进入空会话。
- 现象 B：点击左侧历史会话时，部分点击区域（尤其左侧图标区域）无响应，导致“看起来点了但没切换”。
- 影响范围：`web/src/hooks/useSSEStream.ts`（会话初始化策略）与 `web/src/components/chat/history/index.tsx`（历史条目交互命中区）。

## 2. 根因证据链（含排除假设）

### 2.1 根因一：自动回填“最近会话”的触发条件过宽

证据：`useSSEStream` 在 `threadId` 为空时统一执行 `resolveLatestThread()`，且仅用 `latestThreadResolvedRef` 控制“只执行一次”。

- 当页面初始 URL 已经带 `threadId` 时，`latestThreadResolvedRef` 仍为 `false`。
- 用户首次手动点“新建会话”会把 `threadId` 置空；此时逻辑误判为“初始空会话”，触发 `resolveLatestThread()` 并把 `threadId` 设置回最近会话。
- 结果表现为“第一次点新建会话无效”。

### 2.2 根因二：历史条目只绑定标题文本点击，非整行点击

证据：历史条目中 `handleClick` 绑定在标题 `button`，未绑定在整行容器；左侧图标区域点击不会触发 `onSelect`。

- 结果表现为“有时点历史会话没反应”（取决于用户点击位置）。

### 2.3 被排除假设

- 后端 `getLatestThread` 返回异常：排除（接口数据结构正常，且问题触发依赖前端状态时序）。
- `nuqs` 本身 URL 同步失败：排除（`threadId` 可正常更新，问题出在更新后被前端策略回写覆盖）。

## 3. 修复内容（最小修复）

### 3.1 文件：`web/src/hooks/useSSEStream.ts`

- 增加 `initialThreadIdExistsRef`：仅在“首次进入页面且初始无 `threadId`”时允许自动回填最近会话。
- 增加 `threadIdRef`：异步 `resolveLatestThread()` 回来前再次检查当前 `threadId`，避免覆盖用户刚刚手动切换。
- `setThreadId(latestThreadId)` 改为 `await`，降低竞态窗口。

### 3.2 文件：`web/src/components/chat/history/index.tsx`

- 将历史条目整行容器设为可点击（含键盘 Enter/Space）。
- 对编辑态输入框、按钮、复选框补 `stopPropagation`，避免整行点击副作用。
- 标题从独立按钮改为文本容器，防止重复点击路径。

### 3.3 新增回归测试

- 新增文件：`web/e2e/chat-thread-switch.spec.cjs`
  - `TC-CHAT-THREAD-01`：首次点击新建会话后，`threadId` 立即清空。
  - `TC-CHAT-THREAD-02`：点击历史条目左侧区域可直接切换到目标会话。

### 3.4 文档同步

- 更新：`docs/开发文档/测试管理/聊天系统测试案例.md`
  - 补充 `TC-SYNC-07/08` 与自动化映射关系。

## 4. 验证命令与结果（失败->通过）

### 4.1 上下文校验（jjk-verify）

```bash
pwd
git branch --show-current
git worktree list
git rev-parse --show-toplevel
git rev-parse HEAD
```

结果：`VERIFY_CONTEXT_OK`（目标 worktree 与实际一致）。

### 4.2 回归测试

```bash
cd web
npx playwright test e2e/chat-thread-switch.spec.cjs --project=chromium --no-deps
```

结果：`2 passed`。

### 4.3 代码静态检查

```bash
cd web
npx eslint src/hooks/useSSEStream.ts src/components/chat/history/index.tsx e2e/chat-thread-switch.spec.cjs
```

结果：通过（exit code 0）。

## 5. 风险、回滚点与后续建议

- 已知非阻断告警：Next dev 期间仍有 `vega-canvas` 缺少 `canvas` 的构建告警（与本次会话切换修复无直接关系）。
- 回滚点：
  1. 回滚 `web/src/hooks/useSSEStream.ts` 中 `initialThreadIdExistsRef/threadIdRef` 逻辑。
  2. 回滚 `web/src/components/chat/history/index.tsx` 整行点击改动。
  3. 回滚 `web/e2e/chat-thread-switch.spec.cjs` 与文档新增条目。
- 后续建议：将“自动加载最近会话”与“用户手动新建会话”拆成显式状态机（`bootstrap` vs `user_action`），减少类似竞态回归。
