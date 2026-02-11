const { expect } = require('@playwright/test');

const DEFAULT_USERNAME = 'jjk';
const DEFAULT_API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000';

/**
 * 通过后端 API 直接登录，并将 token 写入 sessionStorage。
 * 适用于 UI 登录不稳定或重定向异常时的兜底。
 */
async function loginViaApi(page, options = {}) {
    const {
        username = DEFAULT_USERNAME,
        password = '',
        apiBase = DEFAULT_API_BASE,
    } = options;

    const response = await page.request.post(`${apiBase}/api/v1/login`, {
        data: { username, password },
    });

    if (!response.ok()) {
        const body = await response.text().catch(() => '<empty>');
        throw new Error(`API 登录失败: ${response.status()} ${body}`);
    }

    const data = await response.json().catch(() => ({}));
    const token = data?.access_token || data?.data?.access_token;

    if (!token) {
        throw new Error('API 登录成功但未返回 access_token');
    }

    await page.addInitScript((value) => {
        window.sessionStorage.setItem('auth:token', value);
    }, token);

    await page.goto('/chat', { waitUntil: 'domcontentloaded' }).catch(() => undefined);
    await page.evaluate((value) => {
        window.sessionStorage.setItem('auth:token', value);
    }, token).catch(() => undefined);

    return token;
}

/**
 * 确保登录并进入聊天页。
 * 策略：
 * 1) 先尝试直接访问 /chat（若已有会话可直接通过）
 * 2) 尝试 UI 登录
 * 3) UI 登录失败则回退 API 登录
 */
async function loginIfNeeded(page, options = {}) {
    const {
        username = DEFAULT_USERNAME,
        password = '',
        forceApi = false,
        apiBase = DEFAULT_API_BASE,
    } = options;

    const chatInput = page.locator('[data-testid="chat-input"]');
    const identifierInput = page.locator('input#identifier, input[placeholder*="用户名"]');

    await page.goto('/chat');
    await page.waitForLoadState('domcontentloaded');

    if (await chatInput.isVisible({ timeout: 5000 }).catch(() => false)) {
        return;
    }

    // 尝试 UI 登录
    if (!forceApi) {
        const isAuthPage = page.url().includes('/auth') || await identifierInput.isVisible({ timeout: 3000 }).catch(() => false);

        if (isAuthPage) {
            await expect(identifierInput).toBeVisible({ timeout: 10000 });
            await identifierInput.fill(username);

            const passwordInput = page.locator('input#password, input[type="password"]');
            if (await passwordInput.isVisible().catch(() => false)) {
                await passwordInput.fill(password);
            }

            await page.getByRole('button', { name: '登录' }).click();

            await Promise.race([
                page.waitForURL('**/chat**', { timeout: 15000 }),
                chatInput.waitFor({ state: 'visible', timeout: 15000 }),
            ]).catch(() => undefined);
        }
    }

    // UI 登录仍失败时，回退 API 登录
    if (!await chatInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('UI 登录未就绪，回退 API 登录...');
        await loginViaApi(page, { username, password, apiBase });
    }

    await page.goto('/chat', { waitUntil: 'domcontentloaded' }).catch(() => undefined);
    await expect(chatInput).toBeVisible({ timeout: 30000 });
}

async function ensureChatReady(page) {
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 30000 });
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
            // 出现确认卡片，使用 data-testid 选择器点击确认按钮
            const confirmBtn = page.locator('[data-testid="confirm-button"]');
            if (await confirmBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                // 等待按钮可点击（非 disabled）
                const isDisabled = await confirmBtn.isDisabled().catch(() => true);
                if (!isDisabled) {
                    console.log('检测到确认卡片，点击确认');
                    await confirmBtn.click();
                    await page.waitForTimeout(1000);
                    continue;
                }
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
    loginViaApi,
    ensureChatReady,
    waitForChatReady,
    waitForAIResponse,
    sendMessageAndWait,
};
