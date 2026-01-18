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
    await page.goto('/login');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 检查是否已登录 (如果能访问 /chat 就说明已登录)
    const response = await page.goto('/chat');
    if (response && response.url().includes('/chat')) {
        // 已登录，直接保存状态
        console.log('用户已登录，保存认证状态...');
        await page.context().storageState({ path: authFile });
        return;
    }

    // 需要登录 - 根据实际登录表单调整选择器
    // 方式1: 用户名密码登录
    const usernameInput = page.locator('input[name="username"], input[type="text"]').first();
    const passwordInput = page.locator('input[name="password"], input[type="password"]');
    const loginButton = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Login")');

    // 检查登录表单是否存在
    if (await usernameInput.isVisible({ timeout: 5000 }).catch(() => false)) {
        // 填写登录信息 (请替换为实际的测试账号)
        await usernameInput.fill(process.env.TEST_USERNAME || 'test');
        await passwordInput.fill(process.env.TEST_PASSWORD || 'test123');
        await loginButton.click();

        // 等待登录完成
        await page.waitForURL('**/chat**', { timeout: 30000 });
    }

    // 方式2: 如果是 OAuth 或其他登录方式，可以手动设置 cookies/localStorage
    // 例如: 直接设置 JWT token
    // await page.evaluate(() => {
    //   localStorage.setItem('token', 'your-test-token');
    // });

    // 保存认证状态
    await page.context().storageState({ path: authFile });
    console.log('认证状态已保存到:', authFile);
});
