const { test, expect } = require('@playwright/test');
const { installMockChatStream, setupMockChatApi } = require('./helpers/mock-chat-api');

test.describe('聊天运行态状态条布局', () => {
  test('应将 runtime-status 渲染在消息流中，而不是 footer', async ({ page }) => {
    const threadId = 'thread-runtime-status';

    await installMockChatStream(page, {
      events: [
        {
          event: 'init',
          data: { thread_id: threadId, run_id: 'run-runtime-status' },
          delayMs: 0,
        },
        {
          event: 'status',
          data: { message: '正在分析测试状态', phase: 'processing' },
          delayMs: 120,
        },
        {
          event: 'token',
          data: { content: '这是测试回答' },
          delayMs: 950,
        },
        {
          event: 'done',
          data: { thread_id: threadId, message_id: 1 },
          delayMs: 1100,
        },
      ],
    });

    await setupMockChatApi(page, {
      threadA: {
        thread_id: threadId,
        title: '运行态测试会话',
        created_at: '2026-03-12T00:00:00Z',
        updated_at: '2026-03-12T00:00:00Z',
      },
      threads: [
        {
          thread_id: threadId,
          title: '运行态测试会话',
          created_at: '2026-03-12T00:00:00Z',
          updated_at: '2026-03-12T00:00:00Z',
        },
      ],
      latestThread: {
        thread_id: threadId,
        title: '运行态测试会话',
        created_at: '2026-03-12T00:00:00Z',
        updated_at: '2026-03-12T00:00:00Z',
      },
      messagesByThread: {
        [threadId]: [],
      },
    });

    await page.goto(`/chat?threadId=${encodeURIComponent(threadId)}`, {
      waitUntil: 'domcontentloaded',
    });
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({
      timeout: 15000,
    });

    await page.fill('[data-testid="chat-input"]', '测试 runtime-status');
    await page.keyboard.press('Enter');

    const runtimeStatus = page.locator('[data-testid="runtime-status"]');
    await expect(runtimeStatus).toBeVisible({ timeout: 5000 });
    await expect(runtimeStatus).toHaveText('正在分析测试状态');

    const isInsideFooter = await runtimeStatus.evaluate((element) => {
      return Boolean(element.closest('footer'));
    });
    expect(isInsideFooter).toBe(false);

    const parentUsesContentShell = await runtimeStatus.evaluate((element) => {
      return Boolean(element.parentElement?.className.includes('chat-content-shell'));
    });
    expect(parentUsesContentShell).toBe(true);

    const appearsBeforeFooter = await page.locator('footer').evaluate((footer) => {
      const status = document.querySelector('[data-testid="runtime-status"]');
      if (!status) {
        return false;
      }
      return Boolean(status.compareDocumentPosition(footer) & Node.DOCUMENT_POSITION_FOLLOWING);
    });
    expect(appearsBeforeFooter).toBe(true);

    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible({
      timeout: 5000,
    });
    await expect(runtimeStatus).toBeHidden({ timeout: 5000 });
  });
});
