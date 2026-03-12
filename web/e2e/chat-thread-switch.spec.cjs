// @ts-check
/**
 * 会话切换稳定性回归测试
 *
 * @test-case TC-CHAT-THREAD-01 首次点击新建会话直接进入空会话
 * @test-case TC-CHAT-THREAD-02 历史条目左侧点击可直接切换会话
 */
const { test, expect } = require('@playwright/test');
const { setupMockChatApi } = require('./helpers/mock-chat-api');

async function setupMockApi(page) {
  const threadA = {
    thread_id: 'thread-A',
    title: '历史会话A',
    created_at: '2026-03-07T00:00:00Z',
    updated_at: '2026-03-07T00:10:00Z',
  };

  const threadB = {
    thread_id: 'thread-B',
    title: '历史会话B',
    created_at: '2026-03-07T00:20:00Z',
    updated_at: '2026-03-07T00:30:00Z',
  };

  const messagesByThread = {
    'thread-A': [
      {
        id: 101,
        thread_id: 'thread-A',
        role: 'human',
        content: '会话A-问题',
        created_at: '2026-03-07T00:01:00Z',
      },
      {
        id: 102,
        thread_id: 'thread-A',
        role: 'ai',
        content: '会话A-回答',
        created_at: '2026-03-07T00:01:10Z',
      },
    ],
    'thread-B': [
      {
        id: 201,
        thread_id: 'thread-B',
        role: 'human',
        content: '会话B-问题',
        created_at: '2026-03-07T00:21:00Z',
      },
      {
        id: 202,
        thread_id: 'thread-B',
        role: 'ai',
        content: '会话B-回答',
        created_at: '2026-03-07T00:21:10Z',
      },
    ],
  };

  await setupMockChatApi(page, {
    threadA,
    threadB,
    latestThread: threadA,
    messagesByThread,
  });
}

function getThreadIdFromUrl(url) {
  return new URL(url).searchParams.get('threadId');
}

test.describe('会话切换稳定性回归', () => {
  test('TC-CHAT-THREAD-01: 首次点击新建会话应直接清空 threadId', async ({ page }) => {
    await setupMockApi(page);

    await page.goto('/chat?threadId=thread-A', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 15000 });

    const newThreadButton = page.getByRole('button', { name: '新会话' }).first();
    await expect(newThreadButton).toBeVisible({ timeout: 10000 });

    await expect
      .poll(() => getThreadIdFromUrl(page.url()), { timeout: 10000 })
      .toBe('thread-A');

    await newThreadButton.click();

    await expect
      .poll(() => getThreadIdFromUrl(page.url()), { timeout: 10000 })
      .toBeNull();
  });

  test('TC-CHAT-THREAD-02: 点击历史条目左侧区域可直接切换会话', async ({ page }) => {
    await setupMockApi(page);

    await page.goto('/chat?threadId=thread-A&chatHistoryOpen=true', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 15000 });

    const threadRowB = page
      .locator('div.app-sidebar-item.group', { hasText: '历史会话B' })
      .first();
    await expect(threadRowB).toBeVisible({ timeout: 10000 });

    // 点击靠左位置，覆盖“图标区域点击”场景。
    await threadRowB.click({ position: { x: 12, y: 14 }, force: true });

    await expect
      .poll(() => getThreadIdFromUrl(page.url()), { timeout: 10000 })
      .toBe('thread-B');
  });
});
