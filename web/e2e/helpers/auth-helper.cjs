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
 * 等待聊天输入框可用（非 streaming，非 waiting-confirm）
 * 检测 data-chat-state 属性：
 * - idle: 空闲，可以输入
 * - streaming: AI 正在响应
 * - waiting-confirm: 等待用户确认
 * 
 * @param {import('@playwright/test').Page} page 
 * @param {number} timeout 超时时间（毫秒），默认 60 秒
 */
async function waitForChatReady(page, timeout = 60000) {
    // 等待 chat-input-container 可见
    await page.waitForSelector('[data-testid="chat-input-container"]', { state: 'visible', timeout: 10000 });
    
    // 等待状态变为 idle
    await page.waitForSelector('[data-testid="chat-input-container"][data-chat-state="idle"]', { timeout });
    
    // 额外等待确保 UI 稳定
    await page.waitForTimeout(500);
}

/**
 * 等待 AI 响应完成（包括处理确认卡片）
 * 如果出现确认卡片，自动点击"确认"按钮
 * 
 * @param {import('@playwright/test').Page} page 
 * @param {number} timeout 超时时间（毫秒），默认 60 秒
 * @param {boolean} autoConfirm 是否自动确认，默认 true
 */
async function waitForAIResponse(page, timeout = 60000, autoConfirm = true) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
        const container = page.locator('[data-testid="chat-input-container"]');
        const state = await container.getAttribute('data-chat-state');
        
        if (state === 'idle') {
            // AI 响应完成，可以继续
            await page.waitForTimeout(500);
            return;
        }
        
        if (state === 'waiting-confirm' && autoConfirm) {
            // 出现确认卡片，点击确认按钮
            const confirmBtn = page.getByRole('button', { name: '确认', exact: true });
            if (await confirmBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                console.log('检测到确认卡片，点击确认');
                await confirmBtn.click();
                await page.waitForTimeout(1000);
                continue;
            }
        }
        
        // 继续等待
        await page.waitForTimeout(1000);
    }
    
    throw new Error(`等待 AI 响应超时 (${timeout}ms)`);
}

/**
 * 发送消息并等待 AI 响应完成
 * @param {import('@playwright/test').Page} page 
 * @param {string} message 要发送的消息
 * @param {number} timeout 等待响应的超时时间
 * @param {boolean} autoConfirm 是否自动确认待办操作，默认 true
 */
async function sendMessageAndWait(page, message, timeout = 60000, autoConfirm = true) {
    // 1. 等待输入框可用
    await waitForChatReady(page, 30000);
    
    // 2. 填写消息并发送
    await page.fill('textarea[data-testid="chat-input"]', message);
    await page.keyboard.press('Enter');
    
    // 3. 等待 AI 响应完成（包括自动确认）
    await waitForAIResponse(page, timeout, autoConfirm);
}

module.exports = {
    loginIfNeeded,
    ensureChatReady,
    waitForChatReady,
    waitForAIResponse,
    sendMessageAndWait,
};
