const { expect } = require('@playwright/test');

const DEFAULT_USERNAME = 'jjk';
const CHAT_INPUT_SELECTOR = '[data-testid="chat-input"]';
const CHAT_INPUT_CONTAINER_SELECTOR = '[data-testid="chat-input-container"]';

function resolveApiBase(apiBase = '') {
    const value = String(apiBase || process.env.E2E_API_BASE || process.env.VK_BACKEND_BASE_URL || '').trim();
    if (!value) {
        throw new Error('缺少 E2E_API_BASE / VK_BACKEND_BASE_URL，无法执行 API 登录');
    }
    return value;
}

function normalizeThreadLabel(label = 'e2e') {
    return String(label || 'e2e')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 48) || 'e2e';
}

function buildE2EThreadId(label = 'e2e') {
    return `${normalizeThreadLabel(label)}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

async function seedAuthToken(page, token) {
    if (!token) return;

    await page.addInitScript((value) => {
        try {
            window.sessionStorage.setItem('auth:token', value);
        } catch {}
    }, token);
}

async function writeSessionToken(page, token) {
    if (!token) return;

    await page.evaluate((value) => {
        try {
            window.sessionStorage.setItem('auth:token', value);
        } catch {}
    }, token).catch(() => undefined);
}

async function loginViaApi(page, options = {}) {
    const {
        username = DEFAULT_USERNAME,
        password = '',
        apiBase = '',
    } = options;
    const targetApiBase = resolveApiBase(apiBase);

    const response = await page.request.post(`${targetApiBase}/api/v1/login`, {
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

    return token;
}

async function loginAndGoto(page, targetPath = '/chat', options = {}) {
    const token = await loginViaApi(page, options);
    await seedAuthToken(page, token);
    await page.goto(targetPath, { waitUntil: 'domcontentloaded' });
    await writeSessionToken(page, token);
    return token;
}


async function ensureChatReady(page) {
    await expect(page.locator(CHAT_INPUT_SELECTOR)).toBeVisible({ timeout: 30000 });
}

async function waitForChatReady(page, timeout = 60000) {
    const container = page.locator(CHAT_INPUT_CONTAINER_SELECTOR);
    await expect(container).toBeVisible({ timeout });
    await expect(container).toHaveAttribute('data-chat-state', 'idle', { timeout });
}

async function waitForAIResponse(page, timeout = 60000, autoConfirm = true) {
    const container = page.locator(CHAT_INPUT_CONTAINER_SELECTOR);

    await expect.poll(async () => {
        const state = await container.getAttribute('data-chat-state');

        if (state === 'waiting-confirm' && autoConfirm) {
            const confirmBtn = page.locator('[data-testid="confirm-button"]');
            const visible = await confirmBtn.isVisible({ timeout: 1000 }).catch(() => false);
            const disabled = await confirmBtn.isDisabled().catch(() => true);
            if (visible && !disabled) {
                console.log('检测到确认卡片，点击确认');
                await confirmBtn.click();
            }
        }

        return await container.getAttribute('data-chat-state');
    }, {
        timeout,
        intervals: [250, 500, 1000],
    }).toBe('idle');
}

async function sendMessageAndWait(page, message, timeout = 60000, autoConfirm = true) {
    await waitForChatReady(page, 30000);
    await page.fill('textarea[data-testid="chat-input"]', message);
    await page.keyboard.press('Enter');
    await waitForAIResponse(page, timeout, autoConfirm);
}

async function loginAndOpenThread(page, label = 'e2e', options = {}, timeout = 60000) {
    const threadId = buildE2EThreadId(label);
    await loginAndGoto(page, `/chat?threadId=${encodeURIComponent(threadId)}`, options);
    await waitForChatReady(page, timeout);
    return threadId;
}

module.exports = {
    buildE2EThreadId,
    resolveApiBase,
    loginViaApi,
    loginAndGoto,
    loginAndOpenThread,
    ensureChatReady,
    waitForChatReady,
    waitForAIResponse,
    sendMessageAndWait,
};
