// @ts-check
const { test, expect } = require('@playwright/test');

function iso(seconds) {
  return new Date(Date.UTC(2026, 2, 8, 12, 0, seconds)).toISOString();
}

async function setupMockBackend(page, scenario) {
  await page.addInitScript((scenarioName) => {
    window.sessionStorage.setItem('auth:token', 'e2e-mock-token');

    const encoder = new TextEncoder();
    const threads = [
      {
        thread_id: 'thread-A',
        title: '并发会话A',
        created_at: '2026-03-08T12:00:00Z',
        updated_at: '2026-03-08T12:10:00Z',
      },
      {
        thread_id: 'thread-B',
        title: '并发会话B',
        created_at: '2026-03-08T12:01:00Z',
        updated_at: '2026-03-08T12:11:00Z',
      },
      {
        thread_id: 'thread-C',
        title: '并发会话C',
        created_at: '2026-03-08T12:02:00Z',
        updated_at: '2026-03-08T12:12:00Z',
      },
      {
        thread_id: 'thread-D',
        title: '第4个会话',
        created_at: '2026-03-08T12:03:00Z',
        updated_at: '2026-03-08T12:13:00Z',
      },
    ];
    let dynamicThreadCount = 0;

    const messagesByThread = {
      'thread-A': [],
      'thread-B': [],
      'thread-C': [],
      'thread-D': [],
    };

    const activeRuns = scenarioName === 'MSC-CL-005'
      ? {
          'thread-A': {
            run_id: 'run-thread-A',
            thread_id: 'thread-A',
            status: 'running',
            updated_at: new Date().toISOString(),
            last_activity_at: new Date().toISOString(),
          },
          'thread-B': {
            run_id: 'run-thread-B',
            thread_id: 'thread-B',
            status: 'running',
            updated_at: new Date().toISOString(),
            last_activity_at: new Date().toISOString(),
          },
          'thread-C': {
            run_id: 'run-thread-C',
            thread_id: 'thread-C',
            status: 'running',
            updated_at: new Date().toISOString(),
            last_activity_at: new Date().toISOString(),
          },
        }
      : {};
    const cancelledRuns = new Set();
    const hiddenActivePollsByThread = {};
    let activeRunsCallCount = 0;

    const jsonResponse = (payload, status = 200) => new Response(JSON.stringify(payload), {
      status,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });

    const ensureThread = (threadId, prompt) => {
      if (!messagesByThread[threadId]) {
        messagesByThread[threadId] = [];
      }
      const existingIndex = threads.findIndex((thread) => thread.thread_id === threadId);
      const title = prompt.slice(0, 24) || '新对话';
      const snapshot = {
        thread_id: threadId,
        title,
        created_at: '2026-03-08T12:05:00Z',
        updated_at: new Date().toISOString(),
      };
      if (existingIndex === -1) {
        threads.unshift(snapshot);
        return;
      }
      threads.splice(existingIndex, 1);
      threads.unshift({ ...threads[existingIndex], ...snapshot });
    };

    const sseResponse = (incomingThreadId, prompt) => {
      const threadId = incomingThreadId || `thread-dynamic-${++dynamicThreadCount}`;
      ensureThread(threadId, prompt);
      const runId = `run-${threadId}`;
      activeRuns[threadId] = {
        run_id: runId,
        thread_id: threadId,
        status: 'running',
        updated_at: new Date().toISOString(),
        last_activity_at: new Date().toISOString(),
      };

      const scriptMap = {
        'thread-A': {
          answer: scenarioName === 'MSC-CL-002' ? 'A-继续完成' : 'A-回答完成',
          firstDelay: 80,
          doneDelay: 520,
        },
        'thread-B': {
          answer: scenarioName === 'MSC-CL-002' ? 'B-第二段不应出现' : 'B-回答完成',
          firstDelay: 60,
          doneDelay: scenarioName === 'MSC-CL-002' ? 3000 : 420,
        },
        'thread-C': {
          answer: 'C-回答完成',
          firstDelay: 70,
          doneDelay: 620,
        },
        'thread-D': {
          answer: 'D-回答完成',
          firstDelay: 90,
          doneDelay: 700,
        },
      };
      const script = { initDelay: 0, ...(scriptMap[threadId] || { answer: `${threadId}-完成`, firstDelay: 50, doneDelay: 220 }) };
      if (scenarioName === 'MSC-CL-010') {
        hiddenActivePollsByThread[threadId] = 2;
        if (threadId === 'thread-A') {
          script.doneDelay = 2200;
        }
      }
      if (scenarioName === 'MSC-CL-011' && incomingThreadId == null) {
        script.doneDelay = 2200;
      }
      if (scenarioName === 'MSC-CL-012' || scenarioName === 'MSC-CL-014') {
        script.initDelay = 450;
        script.doneDelay = scenarioName === 'MSC-CL-014' ? 5000 : 2200;
      }
      if (scenarioName === 'MSC-CL-013' && threadId === 'thread-B') {
        script.doneDelay = 2200;
      }

      return new Response(new ReadableStream({
        start(controller) {
          const send = (event, data) => {
            controller.enqueue(encoder.encode(`event: ${event}
data: ${JSON.stringify(data)}

`));
          };
          const close = () => {
            controller.close();
          };

          setTimeout(() => {
            send('init', { thread_id: threadId, run_id: runId });
          }, script.initDelay);
          setTimeout(() => {
            if (cancelledRuns.has(runId)) {
              send('stopped', { thread_id: threadId, run_id: runId, reason: 'user_cancelled' });
              send('done', { thread_id: threadId, run_id: runId, meta: { status: 'stopped' } });
              delete activeRuns[threadId];
              close();
              return;
            }
            send('token', { content: `${prompt} -> ${threadId === 'thread-A' ? 'A-首段' : 'B-首段'}` });
          }, script.initDelay + script.firstDelay);

          setTimeout(() => {
            if (cancelledRuns.has(runId)) {
              send('stopped', { thread_id: threadId, run_id: runId, reason: 'user_cancelled' });
              send('done', { thread_id: threadId, run_id: runId, meta: { status: 'stopped' } });
              delete activeRuns[threadId];
              close();
              return;
            }
            send('token', { content: ` ${script.answer}` });
            send('done', { thread_id: threadId, run_id: runId, message_id: threadId === 'thread-A' ? 1001 : 1002 });
            messagesByThread[threadId] = [
              { id: `${threadId}-human`, thread_id: threadId, role: 'human', content: prompt, created_at: '2026-03-08T12:00:00Z' },
              { id: `${threadId}-ai`, thread_id: threadId, role: 'ai', content: `${prompt} -> ${threadId === 'thread-A' ? 'A-首段' : 'B-首段'} ${script.answer}`, created_at: '2026-03-08T12:00:01Z' },
            ];
            delete activeRuns[threadId];
            close();
          }, script.initDelay + script.doneDelay);
        },
      }), {
        status: 200,
        headers: { 'content-type': 'text/event-stream; charset=utf-8' },
      });
    };

    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const requestUrl = typeof input === 'string' ? input : input.url;
      const url = new URL(requestUrl, window.location.origin);
      const { pathname } = url;
      const method = (init?.method || 'GET').toUpperCase();

      if (!pathname.startsWith('/api/v1/')) {
        return originalFetch(input, init);
      }

      if (method === 'GET' && pathname === '/api/v1/me') {
        return jsonResponse({
          id: 1,
          username: 'e2e',
          mobile: null,
          data_role: null,
          data_role_label: null,
        });
      }

      if (method === 'GET' && pathname === '/api/v1/llm/models') {
        return jsonResponse([
          {
            model_code: 'mock-chat',
            model_name: 'Mock Chat',
            model_type: 'chat',
            provider: 'mock',
            supports_thinking: false,
            is_default: true,
          },
        ]);
      }

      if (method === 'GET' && pathname === '/api/v1/chat/threads') {
        return jsonResponse(threads);
      }

      if (method === 'GET' && pathname === '/api/v1/chat/threads/latest') {
        return jsonResponse(threads[0]);
      }

      const messageMatch = pathname.match(/^\/api\/v1\/chat\/threads\/([^/]+)\/messages$/);
      if (method === 'GET' && messageMatch) {
        const tid = decodeURIComponent(messageMatch[1]);
        return jsonResponse(messagesByThread[tid] || []);
      }

      if (method === 'GET' && pathname === '/api/v1/chat/runs/active') {
        activeRunsCallCount += 1;
        if (scenarioName === 'MSC-CL-003') {
          return jsonResponse({
            items: [
              {
                run_id: 'run-thread-B',
                thread_id: 'thread-B',
                status: 'running',
                updated_at: '${ISO_1}',
                last_activity_at: '${ISO_2}',
              },
            ],
            active_count: 1,
            poll_hint_seconds: 2,
            server_time: '${ISO_3}',
          });
        }
        if (scenarioName === 'MSC-CL-008') {
          if (activeRunsCallCount <= 2) {
            return jsonResponse({
              items: [
                {
                  run_id: 'run-thread-B',
                  thread_id: 'thread-B',
                  status: 'running',
                  updated_at: '${ISO_1}',
                  last_activity_at: '${ISO_2}',
                },
              ],
              active_count: 1,
              poll_hint_seconds: 1,
              server_time: '${ISO_3}',
            });
          }
          return jsonResponse({ items: [], active_count: 0, poll_hint_seconds: 2, server_time: '${ISO_4}' });
        }
        if (scenarioName === 'MSC-CL-010') {
          const items = Object.values(activeRuns).filter((item) => {
            const remaining = hiddenActivePollsByThread[item.thread_id] || 0;
            if (remaining <= 0) {
              return true;
            }
            hiddenActivePollsByThread[item.thread_id] = remaining - 1;
            return false;
          });
          return jsonResponse({
            items,
            active_count: items.length,
            poll_hint_seconds: 1,
            server_time: new Date().toISOString(),
          });
        }

        const items = Object.values(activeRuns);
        return jsonResponse({
          items,
          active_count: items.length,
          poll_hint_seconds: 1,
          server_time: new Date().toISOString(),
        });
      }

      if (method === 'POST' && pathname === '/api/v1/chat/stream') {
        const payload = JSON.parse(init?.body ? String(init.body) : '{}');
        if (scenarioName === 'MSC-CL-005' && payload.thread_id === 'thread-D') {
          return jsonResponse({
            code: 429,
            message: '当前运行会话数已达上限（3/3）',
            data: {
              error_code: 'parallel_limit_exceeded',
              active_count: 3,
              limit: 3,
            },
          }, 429);
        }
        return sseResponse(payload.thread_id, payload.prompt || 'prompt');
      }

      const cancelMatch = pathname.match(/^\/api\/v1\/chat\/runs\/([^/]+)\/cancel$/);
      if (method === 'POST' && cancelMatch) {
        const runId = decodeURIComponent(cancelMatch[1]);
        cancelledRuns.add(runId);
        const threadId = runId.replace('run-', '');
        delete activeRuns[threadId];
        return jsonResponse({
          accepted: true,
          idempotent: false,
          run_id: runId,
          thread_id: threadId,
          status: 'stopped',
          reason: 'user_cancelled',
        });
      }

      return jsonResponse({});
    };
  }, scenario);
}

const ISO_1 = iso(10);
const ISO_2 = iso(12);
const ISO_3 = iso(13);
const ISO_4 = iso(20);

async function openChat(page, scenario, threadId = 'thread-A') {
  await setupMockBackend(page, scenario);
  const targetUrl = threadId ? `/chat?threadId=${threadId}&chatHistoryOpen=true` : '/chat?chatHistoryOpen=true';
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 15000 });
}

async function switchThread(page, threadId) {
  await page.locator(`[data-thread-id="${threadId}"]`).click();
  await page.waitForFunction((targetThreadId) => {
    return new URL(window.location.href).searchParams.get('threadId') === targetThreadId;
  }, threadId);
}

test.describe('Chat Multi Session Concurrency', () => {
  test('MSC-CL-001: A/B 会话并发提交后消息不串写', async ({ page }) => {
    await openChat(page, 'MSC-CL-001');

    const threadAIndicator = page.locator('[data-thread-id="thread-A"] [data-testid="thread-reply-status"]');
    const threadBIndicator = page.locator('[data-thread-id="thread-B"] [data-testid="thread-reply-status"]');

    await page.fill('[data-testid="chat-input"]', '问题-A');
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming');
    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'running');

    await switchThread(page, 'thread-B');
    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'idle');
    await page.fill('[data-testid="chat-input"]', '问题-B');
    await page.keyboard.press('Enter');
    await expect(threadBIndicator).toHaveAttribute('data-reply-status', 'running');

    await expect.poll(async () => page.locator('[data-testid="ai-message"]', { hasText: 'B-回答完成' }).count(), { timeout: 10000 }).toBeGreaterThan(0);
    await expect(threadBIndicator).toHaveAttribute('data-reply-status', 'none');
    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'unread', { timeout: 10000 });

    await switchThread(page, 'thread-A');
    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'none');
    await expect.poll(async () => page.locator('[data-testid="ai-message"]', { hasText: 'A-回答完成' }).count(), { timeout: 10000 }).toBeGreaterThan(0);
    await expect(page.locator('[data-testid="ai-message"]', { hasText: 'B-回答完成' })).toHaveCount(0);

    await switchThread(page, 'thread-B');
    await expect(page.locator('[data-testid="ai-message"]', { hasText: 'B-回答完成' })).toHaveCount(1);
    await expect(page.locator('[data-testid="ai-message"]', { hasText: 'A-回答完成' })).toHaveCount(0);
    await expect(threadBIndicator).toHaveAttribute('data-reply-status', 'none');
  });

  test('MSC-CL-002: 停止 B 不影响 A', async ({ page }) => {
    await openChat(page, 'MSC-CL-002');

    await page.fill('[data-testid="chat-input"]', '任务-A');
    await page.keyboard.press('Enter');
    await switchThread(page, 'thread-B');
    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'idle');
    await page.fill('[data-testid="chat-input"]', '任务-B');
    await page.keyboard.press('Enter');

    const stopButton = page.getByTestId('chat-stop-button');
    const threadBIndicator = page.locator('[data-thread-id="thread-B"] [data-testid="thread-reply-status"]');
    await expect(stopButton).toBeVisible({ timeout: 10000 });
    await stopButton.click();
    await expect(threadBIndicator).toHaveAttribute('data-reply-status', 'none', { timeout: 1500 });

    await page.waitForTimeout(800);
    await switchThread(page, 'thread-A');
    await expect(page.locator('[data-testid="ai-message"]', { hasText: 'A-继续完成' })).toHaveCount(1);

    await switchThread(page, 'thread-B');
    await expect(page.locator('[data-testid="ai-message"]', { hasText: 'B-第二段不应出现' })).toHaveCount(0);
    await expect(threadBIndicator).toHaveAttribute('data-reply-status', 'none', { timeout: 5000 });
  });

  test('MSC-CL-003: 刷新后恢复运行态', async ({ page }) => {
    await openChat(page, 'MSC-CL-003');

    const indicator = page.locator('[data-thread-id="thread-B"] [data-testid="thread-reply-status"]');
    await expect(indicator).toHaveAttribute('data-reply-status', 'running', { timeout: 10000 });

    await switchThread(page, 'thread-B');
    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming');
  });

  test('MSC-CL-005: 用户并发超限时保留已有 3 个运行态并提示 429', async ({ page }) => {
    await openChat(page, 'MSC-CL-005', 'thread-D');

    for (const threadId of ['thread-A', 'thread-B', 'thread-C']) {
      await expect(page.locator(`[data-thread-id="${threadId}"] [data-testid="thread-reply-status"]`)).toHaveAttribute('data-reply-status', 'running');
    }

    await page.fill('[data-testid="chat-input"]', '这是第4个并发请求，应被上限 3 拦截');
    await page.keyboard.press('Enter');

    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'idle');
    const limitToast = page.getByRole('listitem').filter({ hasText: '请求失败' });
    await expect(limitToast).toBeVisible({ timeout: 10000 });
    await expect(limitToast.getByText('当前运行会话数已达上限（3/3）', { exact: true })).toBeVisible({ timeout: 10000 });

    for (const threadId of ['thread-A', 'thread-B', 'thread-C']) {
      await expect(page.locator(`[data-thread-id="${threadId}"] [data-testid="thread-reply-status"]`)).toHaveAttribute('data-reply-status', 'running');
    }
    await expect(page.locator('[data-thread-id="thread-D"] [data-testid="thread-reply-status"]')).toHaveAttribute('data-reply-status', 'none');
  });

  test('MSC-CL-008: active_count>0 时侧边栏状态自动更新', async ({ page }) => {
    await openChat(page, 'MSC-CL-008');

    const indicator = page.locator('[data-thread-id="thread-B"] [data-testid="thread-reply-status"]');
    await expect(indicator).toHaveAttribute('data-reply-status', 'running', { timeout: 10000 });
    await expect(indicator).toHaveAttribute('data-reply-status', 'unread', { timeout: 12000 });

    await switchThread(page, 'thread-B');
    await expect(indicator).toHaveAttribute('data-reply-status', 'none');
  });

  test('MSC-CL-010: active 接口短暂空窗时本地 running 图标不丢失', async ({ page }) => {
    await openChat(page, 'MSC-CL-010');

    const indicator = page.locator('[data-thread-id="thread-A"] [data-testid="thread-reply-status"]');
    await page.fill('[data-testid="chat-input"]', '问题-A');
    await page.keyboard.press('Enter');

    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming');
    await expect(indicator).toHaveAttribute('data-reply-status', 'running');

    await page.waitForTimeout(1400);
    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming');
    await expect(indicator).toHaveAttribute('data-reply-status', 'running');

    await expect.poll(async () => page.locator('[data-testid="ai-message"]', { hasText: 'A-回答完成' }).count(), { timeout: 10000 }).toBeGreaterThan(0);
    await expect(indicator).toHaveAttribute('data-reply-status', 'none');
  });

  test('MSC-CL-011: 新线程分配后侧边栏立即显示 running', async ({ page }) => {
    await openChat(page, 'MSC-CL-011');

    await page.getByRole('button', { name: '新建对话' }).first().click();
    await page.waitForFunction(() => new URL(window.location.href).searchParams.get('threadId') === null);

    await page.fill('[data-testid="chat-input"]', '新线程问题');
    await page.keyboard.press('Enter');

    await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming');
    await page.waitForFunction(() => Boolean(new URL(window.location.href).searchParams.get('threadId')));
    const threadId = await page.evaluate(() => new URL(window.location.href).searchParams.get('threadId'));
    const indicator = page.locator(`[data-thread-id="${threadId}"] [data-testid="thread-reply-status"]`);

    await expect(indicator).toHaveAttribute('data-reply-status', 'running', { timeout: 5000 });
  });

  test('MSC-CL-012: 点新建后，晚到 init 不得把页面抢回旧会话', async ({ page }) => {
    await openChat(page, 'MSC-CL-012');

    await page.fill('[data-testid="chat-input"]', '晚到-init-问题');
    await page.keyboard.press('Enter');
    await page.getByRole('button', { name: '新建对话' }).first().click();

    await expect.poll(() => new URL(page.url()).searchParams.get('threadId'), { timeout: 10000 }).toBeNull();

    const threadAIndicator = page.locator('[data-thread-id="thread-A"] [data-testid="thread-reply-status"]');
    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'running', { timeout: 1000 });

    await page.waitForTimeout(900);
    await expect.poll(() => new URL(page.url()).searchParams.get('threadId'), { timeout: 10000 }).toBeNull();
  });

  test('MSC-CL-013: 新后台会话完成时，不得把旧的已读会话重新打成蓝点', async ({ page }) => {
    await openChat(page, 'MSC-CL-013');

    const threadAIndicator = page.locator('[data-thread-id="thread-A"] [data-testid="thread-reply-status"]');
    const threadBIndicator = page.locator('[data-thread-id="thread-B"] [data-testid="thread-reply-status"]');

    await page.fill('[data-testid="chat-input"]', '问题-A');
    await page.keyboard.press('Enter');
    await expect.poll(async () => page.locator('[data-testid="ai-message"]', { hasText: 'A-回答完成' }).count(), { timeout: 10000 }).toBeGreaterThan(0);
    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'none');

    await switchThread(page, 'thread-B');
    await page.fill('[data-testid="chat-input"]', '问题-B');
    await page.keyboard.press('Enter');
    await switchThread(page, 'thread-C');

    await expect(threadBIndicator).toHaveAttribute('data-reply-status', 'unread', { timeout: 12000 });
    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'none');
  });

  test('MSC-CL-014: 切走当前会话后，后台运行态要立刻显示 spinner', async ({ page }) => {
    await openChat(page, 'MSC-CL-014');

    const threadAIndicator = page.locator('[data-thread-id="thread-A"] [data-testid="thread-reply-status"]');
    await page.fill('[data-testid="chat-input"]', '问题-A');
    await page.keyboard.press('Enter');
    await switchThread(page, 'thread-B');

    await expect(threadAIndicator).toHaveAttribute('data-reply-status', 'running', { timeout: 1000 });
  });
});
