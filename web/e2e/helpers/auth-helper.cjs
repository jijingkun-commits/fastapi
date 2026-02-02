const { expect } = require('@playwright/test');

async function loginIfNeeded(page, options = {}) {
    const { username = 'admin', password = '123456' } = options;

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const isAuthPage = page.url().includes('/auth');
    const identifierInput = page.locator('input#identifier');

    if (isAuthPage || await identifierInput.isVisible().catch(() => false)) {
        await expect(identifierInput).toBeVisible({ timeout: 5000 });
        await identifierInput.fill(username);

        const passwordInput = page.locator('input#password');
        if (password && await passwordInput.isVisible().catch(() => false)) {
            await passwordInput.fill(password);
        }

        await page.getByRole('button', { name: '登录' }).click();

        await page.waitForURL('**/chat**', { timeout: 30000 }).catch(async () => {
            await page.waitForURL('**/', { timeout: 30000 }).catch(() => {});
        });
    }
}

async function ensureChatReady(page) {
    await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
}

module.exports = {
    loginIfNeeded,
    ensureChatReady,
};
