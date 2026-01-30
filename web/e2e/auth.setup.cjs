/**
 * Playwright Auth Setup
 * 
 * 此脚本用于登录并保存认证状态到 .auth/user.json
 * 后续测试将复用此状态，避免重复登录
 * 
 * 使用方法:
 * npx playwright test e2e/auth.setup.cjs --project=setup
 */

const { test: setup, expect } = require('@playwright/test');

const authFile = '.auth/user.json';

setup('authenticate', async ({ page }) => {
    // 访问登录页面
    await page.goto('/auth');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 检查是否已登录 (如果能访问 /chat 就说明已登录)
    const currentUrl = page.url();
    if (currentUrl.includes('/chat')) {
        // 已登录，直接保存状态
        console.log('用户已登录，保存认证状态...');
        await page.context().storageState({ path: authFile });
        return;
    }

    // 需要登录 - 使用实际的登录表单选择器
    // 账号输入框
    const usernameInput = page.locator('input#identifier, input[placeholder*="用户名"]');
    const passwordInput = page.locator('input#password, input[type="password"]');
    const loginButton = page.getByRole('button', { name: '登录' });

    // 检查登录表单是否存在
    if (await usernameInput.isVisible({ timeout: 5000 }).catch(() => false)) {
        // 填写登录信息 (使用测试账号 jjk，开发环境密码可为空)
        await usernameInput.fill(process.env.TEST_USERNAME || 'jjk');
        // 开发环境密码可选
        if (await passwordInput.isVisible().catch(() => false)) {
            await passwordInput.fill(process.env.TEST_PASSWORD || '');
        }
        await loginButton.click();

        // 等待登录完成
        await page.waitForURL('**/chat**', { timeout: 30000 });
    }

    // 保存认证状态
    await page.context().storageState({ path: authFile });
    console.log('认证状态已保存到:', authFile);
});
