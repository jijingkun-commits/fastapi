const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, waitForChatReady, waitForAIResponse } = require('./helpers/auth-helper');

test.describe('Chat Feedback and Stop', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await loginAndOpenThread(page, testInfo.title);
    });

    test('should stop generation', async ({ page }) => {
        test.setTimeout(120000);

        await page.fill('[data-testid="chat-input"]', '写一篇关于人工智能发展的长文，至少500字');
        await page.keyboard.press('Enter');

        await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming', {
            timeout: 15000,
        });

        const stopButton = page.locator('button:has(.animate-spin)').first();
        await expect(stopButton).toBeVisible({ timeout: 10000 });
        await stopButton.click();

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
        await aiMessages.last().hover();

        const likeButton = page.getByRole('button', { name: 'Good response' }).last();
        const dislikeButton = page.getByRole('button', { name: 'Bad response' }).last();

        if (!await likeButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await aiMessages.first().hover();
        }

        await expect(likeButton).toBeVisible({ timeout: 10000 });
        await likeButton.click();
        await expect(dislikeButton).toBeVisible({ timeout: 10000 });
        await dislikeButton.click();
    });
});
