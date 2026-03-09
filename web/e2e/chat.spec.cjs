const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, waitForAIResponse } = require('./helpers/auth-helper');

test.describe('Chat Functionality', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await loginAndOpenThread(page, testInfo.title);
    });

    test('should load chat interface', async ({ page }) => {
        await expect(page).toHaveTitle(/嘉银助手|Chat/i);
        await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 10000 });
    });

    test('should send a message', async ({ page }) => {
        const message = 'Hello E2E Test';
        await page.fill('[data-testid="chat-input"]', message);
        await page.keyboard.press('Enter');
        await waitForAIResponse(page, 90000, true);
        await expect(page.locator('[data-testid="chat-input"]')).toHaveValue('');
        await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible();
    });
});
