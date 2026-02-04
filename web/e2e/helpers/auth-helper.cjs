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

/**
 * 等待 AI 响应完成
 * 检测 textarea 的 data-streaming 属性变为 "false"
 * @param {import('@playwright/test').Page} page 
 * @param {number} timeout 超时时间（毫秒），默认 60 秒
 */
async function waitForAIResponse(page, timeout = 60000) {
    // 等待 textarea 可见
    await page.waitForSelector('textarea[data-testid="chat-input"]', { state: 'visible', timeout: 10000 });
    
    // 等待流式输出完成（data-streaming 变为 false）
    await page.waitForSelector('textarea[data-testid="chat-input"][data-streaming="false"]', { timeout });
    
    // 额外等待确保 UI 稳定
    await page.waitForTimeout(1000);
}

/**
 * 发送消息并等待 AI 响应完成
 * @param {import('@playwright/test').Page} page 
 * @param {string} message 要发送的消息
 * @param {number} timeout 等待响应的超时时间
 */
async function sendMessageAndWait(page, message, timeout = 60000) {
    // 1. 等待流式输出完成（如果有的话）
    await page.waitForSelector('textarea[data-testid="chat-input"][data-streaming="false"]', { timeout: 30000 });
    
    // 2. 填写消息并发送
    await page.fill('textarea[data-testid="chat-input"]', message);
    await page.keyboard.press('Enter');
    
    // 3. 等待 AI 响应完成
    await waitForAIResponse(page, timeout);
}

module.exports = {
    loginIfNeeded,
    ensureChatReady,
    waitForAIResponse,
    sendMessageAndWait,
};
