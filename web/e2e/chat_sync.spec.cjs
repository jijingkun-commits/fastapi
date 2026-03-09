/**
 * 对话同步测试 - 验证前端展示与后端保存的一致性
 *
 * @test-case TC-SYNC-01 前后端消息一致性
 * @test-case TC-SYNC-02 刷新后消息完整加载
 * @test-case TC-SYNC-03 快速连续发送
 * @test-case TC-SYNC-04 长文本响应完整性
 * @test-case TC-SYNC-05 特殊字符处理
 * @see docs/开发文档/测试管理/聊天系统测试案例.md
 *
 * 测试目标：
 * 1. 流式响应完成后，前端展示内容与后端保存一致
 * 2. additional_kwargs 正确传递（如 TodoList 卡片）
 * 3. thinking 内容正确处理
 * 4. 历史消息加载后与流式展示一致
 */
const { test, expect, request } = require('@playwright/test');
const { loginAndOpenThread, resolveApiBase, waitForChatReady, sendMessageAndWait } = require('./helpers/auth-helper');

const API_BASE = resolveApiBase();


function extractThreadId(url) {
    try {
        const parsed = new URL(url);
        return parsed.searchParams.get('threadId') || (parsed.pathname.match(/\/chat\/([^\/?]+)/)?.[1] ?? null);
    } catch {
        return null;
    }
}

test.describe('对话同步测试', () => {
    let apiContext;
    let authToken;
    let threadId;

    test.beforeAll(async () => {
        apiContext = await request.newContext({
            baseURL: API_BASE,
        });

        const loginResp = await apiContext.post('/api/v1/login', {
            data: { username: 'jjk', password: '' }
        });

        if (loginResp.ok()) {
            const data = await loginResp.json();
            authToken = data.data?.access_token || data.access_token;
            console.log('登录成功, token:', authToken ? authToken.substring(0, 20) + '...' : 'null');
        } else {
            console.log('登录响应:', await loginResp.text());
        }
    });

    test.beforeEach(async ({ page }, testInfo) => {
        threadId = await loginAndOpenThread(page, testInfo.titlePath[testInfo.titlePath.length - 1], {}, 60000);
        console.log('当前 thread_id:', threadId);
    });

    test.afterAll(async () => {
        await apiContext?.dispose();
    });

    test('TC-SYNC-001: 简单对话 - 前端展示与后端保存一致', async ({ page }) => {
        test.setTimeout(90000);

        const testMessage = `测试同步 ${Date.now()}`;
        await sendMessageAndWait(page, testMessage, 90000);

        const aiMessages = page.locator('[data-testid="ai-message"]');
        await expect(aiMessages.last()).toBeVisible({ timeout: 15000 });
        const count = await aiMessages.count();
        expect(count).toBeGreaterThan(0);

        const frontendContent = await aiMessages.last().innerText();
        console.log('前端展示内容 (前100字符):', frontendContent.substring(0, 100));

        const currentThreadId = extractThreadId(page.url()) || threadId;

        if (authToken && currentThreadId) {
            const messagesResp = await apiContext.get(`/api/v1/chat/messages/${currentThreadId}`, {
                headers: { Authorization: `Bearer ${authToken}` }
            });

            if (messagesResp.ok()) {
                const messagesData = await messagesResp.json();
                const messages = messagesData.data || messagesData;
                const aiMsgs = messages.filter((message) => message.role === 'assistant' || message.type === 'ai');
                if (aiMsgs.length > 0) {
                    const lastBackendMsg = aiMsgs[aiMsgs.length - 1];
                    const backendContent = lastBackendMsg.content || '';
                    console.log('后端保存内容 (前100字符):', backendContent.substring(0, 100));

                    const normalizedFrontend = frontendContent.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
                    const normalizedBackend = backendContent.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
                    const similarity = calculateSimilarity(normalizedBackend, normalizedFrontend);
                    console.log('内容相似度:', similarity);
                    expect(similarity).toBeGreaterThan(0.5);
                }
            }
        }
    });

    test('TC-SYNC-002: 页面刷新后历史消息一致性', async ({ page }) => {
        test.setTimeout(90000);

        const testMessage = `刷新测试 ${Date.now()}`;
        await sendMessageAndWait(page, testMessage, 90000);

        const aiMessages = page.locator('[data-testid="ai-message"]');
        await expect(aiMessages.last()).toBeVisible({ timeout: 15000 });
        const countBefore = await aiMessages.count();
        let contentBefore = '';
        if (countBefore > 0) {
            contentBefore = await aiMessages.last().innerText();
            console.log('刷新前内容 (前50字):', contentBefore.substring(0, 50));
        }

        await page.reload({ waitUntil: 'domcontentloaded' });
        await waitForChatReady(page, 60000);

        const aiMessagesAfter = page.locator('[data-testid="ai-message"]');
        await expect(aiMessagesAfter.last()).toBeVisible({ timeout: 15000 });
        const countAfter = await aiMessagesAfter.count();

        if (countAfter > 0) {
            const contentAfter = await aiMessagesAfter.last().innerText();
            console.log('刷新后内容 (前50字):', contentAfter.substring(0, 50));

            const similarity = calculateSimilarity(contentBefore, contentAfter);
            console.log('刷新前后相似度:', similarity);
            expect(similarity).toBeGreaterThan(0.8);
        }
    });

    test('TC-SYNC-003: 快速连续发送消息', async ({ page }) => {
        test.setTimeout(180000);

        const messages = [
            `快速消息1 ${Date.now()}`,
            `快速消息2 ${Date.now() + 1}`,
            `快速消息3 ${Date.now() + 2}`,
        ];

        const userMessages = page.locator('[data-testid="human-message"]');
        const countBefore = await userMessages.count().catch(() => 0);
        console.log('发送前用户消息数量:', countBefore);

        for (const message of messages) {
            await sendMessageAndWait(page, message, 90000, true);
        }

        await expect.poll(async () => userMessages.count(), {
            timeout: 15000,
            message: '等待连续发送后的用户消息数量稳定'
        }).toBeGreaterThanOrEqual(countBefore + messages.length);

        const count = await userMessages.count();
        console.log('用户消息数量:', count, '(预期至少:', countBefore + messages.length, ')');
        expect(count).toBeGreaterThanOrEqual(countBefore + messages.length);
    });

    test('TC-SYNC-004: 长文本响应处理', async ({ page }) => {
        test.setTimeout(180000);

        const testMessage = '请详细解释一下人工智能的发展历史，包括主要里程碑事件。';
        await sendMessageAndWait(page, testMessage, 120000);

        const aiMessages = page.locator('[data-testid="ai-message"]');
        await expect(aiMessages.last()).toBeVisible({ timeout: 15000 });
        const count = await aiMessages.count();
        expect(count).toBeGreaterThan(0);

        const content = await aiMessages.last().innerText();
        console.log('长响应内容长度:', content.length);
        expect(content.length).toBeGreaterThan(100);
    });

    test('TC-SYNC-005: 特殊字符处理', async ({ page }) => {
        test.setTimeout(120000);

        const userMessages = page.locator('[data-testid="human-message"]');
        const countBefore = await userMessages.count().catch(() => 0);
        console.log('发送前用户消息数量:', countBefore);

        const testMessage = '测试特殊字符: <script>alert(1)</script> & "引号" \'单引号\' `反引号`';

        let dialogTriggered = false;
        page.on('dialog', async (dialog) => {
            dialogTriggered = true;
            await dialog.dismiss();
        });

        await sendMessageAndWait(page, testMessage, 90000);

        await expect.poll(async () => userMessages.count(), {
            timeout: 15000,
            message: '等待特殊字符消息写入会话列表'
        }).toBeGreaterThan(countBefore);

        const count = await userMessages.count();
        console.log('最终用户消息数量:', count);
        expect(count).toBeGreaterThan(countBefore);

        const content = await userMessages.last().innerText();
        console.log('消息内容:', content);
        expect(content).toContain('<script>alert(1)</script>');
        expect(dialogTriggered).toBe(false);
    });
});

function calculateSimilarity(str1, str2) {
    if (!str1 || !str2) return 0;

    const s1 = str1.toLowerCase().replace(/\s+/g, ' ').trim();
    const s2 = str2.toLowerCase().replace(/\s+/g, ' ').trim();

    if (s1 === s2) return 1;
    if (s1.length === 0 || s2.length === 0) return 0;

    if (s1.includes(s2) || s2.includes(s1)) {
        return Math.min(s1.length, s2.length) / Math.max(s1.length, s2.length);
    }

    const shorter = s1.length < s2.length ? s1 : s2;
    const longer = s1.length < s2.length ? s2 : s1;

    let matches = 0;
    const words = shorter.split(' ');
    for (const word of words) {
        if (word.length > 2 && longer.includes(word)) {
            matches++;
        }
    }

    return words.length > 0 ? matches / words.length : 0;
}
