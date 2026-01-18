const { test, expect } = require('@playwright/test');

test.describe('Chat Functionality', () => {
    test('should load chat interface', async ({ page }) => {
        await page.goto('/');
        // Check for title or key element
        await expect(page).toHaveTitle(/嘉银助手|Chat/i);
        await expect(page.locator('textarea')).toBeVisible({ timeout: 10000 });
    });

    test('should send a message', async ({ page }) => {
        await page.goto('/');

        // Type message
        const message = 'Hello E2E Test';
        await page.fill('textarea', message);

        // Click send (assuming button exists)
        // We try to find button by exact text or type
        const sendButton = page.locator('button[type="submit"]');
        await expect(sendButton).toBeVisible();
        await sendButton.click();

        // Check if input is cleared (simple verify)
        await expect(page.locator('textarea')).toHaveValue('');
    });
});
