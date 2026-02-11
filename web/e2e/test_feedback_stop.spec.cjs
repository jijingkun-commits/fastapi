const { test, expect } = require('@playwright/test');
const { loginIfNeeded, waitForChatReady, waitForAIResponse } = require('./helpers/auth-helper');

test.describe('Chat Feedback and Stop', () => {
    test.beforeEach(async ({ page }) => {
        await loginIfNeeded(page);
        await waitForChatReady(page, 60000);
    });

    test('should stop generation', async ({ page }) => {
        test.setTimeout(120000);

        // 发送一个较长提示词触发 streaming
        const prompt = '写一篇关于人工智能发展的长文，至少500字';
        await page.fill('[data-testid="chat-input"]', prompt);
        await page.keyboard.press('Enter');

        // 等待进入 streaming 状态
        await page.waitForSelector('[data-testid="chat-input-container"][data-chat-state="streaming"]', {
            timeout: 15000,
        });

        // 停止按钮在 loading 状态下显示 spinner
        const stopButton = page.locator('button:has(.animate-spin)').first();
        await expect(stopButton).toBeVisible({ timeout: 10000 });
        await stopButton.click();

        // 验证回到可输入状态
        await waitForChatReady(page, 30000);
        await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    });

    test('should allow like and dislike', async ({ page }) => {
        test.setTimeout(120000);

        await page.fill('[data-testid="chat-input"]', '你好');
        await page.keyboard.press('Enter');
        await waitForAIResponse(page, 60000, true);

        const aiMessages = page.locator('[data-testid="ai-message"]');
        await expect(aiMessages.last()).toBeVisible({ timeout: 10000 });

        // 操作栏默认透明，先 hover 最后一条 AI 消息触发显示
        await aiMessages.last().hover();

        const likeButton = page.getByRole('button', { name: 'Good response' }).last();
        const dislikeButton = page.getByRole('button', { name: 'Bad response' }).last();

        // 若最后一条消息无反馈按钮，回退到第一条 AI 消息再触发一次
        if (!await likeButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await aiMessages.first().hover();
        }

        await expect(likeButton).toBeVisible({ timeout: 10000 });
        await likeButton.click();
        await expect(likeButton).toBeVisible();

        await expect(dislikeButton).toBeVisible({ timeout: 10000 });
        await dislikeButton.click();
        await expect(dislikeButton).toBeVisible();
    });
});
