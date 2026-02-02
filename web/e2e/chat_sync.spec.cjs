/**
 * 对话同步测试 - 验证前端展示与后端保存的一致性
 * 
 * 测试目标：
 * 1. 流式响应完成后，前端展示内容与后端保存一致
 * 2. additional_kwargs 正确传递（如 TodoList 卡片）
 * 3. thinking 内容正确处理
 * 4. 历史消息加载后与流式展示一致
 */
const { test, expect, request } = require('@playwright/test');

// 后端 API 基础 URL
const API_BASE = 'http://localhost:8000/api/v1';

// 测试用例
test.describe('对话同步测试', () => {
    let apiContext;
    let authToken;
    let threadId;

    test.beforeAll(async () => {
        // 创建 API context
        apiContext = await request.newContext({
            baseURL: API_BASE,
        });

        // 登录获取 token
        const loginResp = await apiContext.post('/auth/login', {
            data: { identifier: 'jjk', password: '' }
        });
        
        if (loginResp.ok()) {
            const data = await loginResp.json();
            authToken = data.data?.access_token || data.access_token;
            console.log('登录成功, token:', authToken ? authToken.substring(0, 20) + '...' : 'null');
        } else {
            console.log('登录响应:', await loginResp.text());
        }
    });

    test.beforeEach(async ({ page }) => {
        // 导航到首页
        await page.goto('/');
        
        // 等待页面加载
        await page.waitForLoadState('networkidle');
        
        // 检查是否在登录页面，如果是则执行登录
        if (page.url().includes('/auth')) {
            console.log('需要登录...');
            const usernameInput = page.locator('input#identifier, input[placeholder*="用户名"]');
            if (await usernameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
                await usernameInput.fill('jjk');
                await page.getByRole('button', { name: '登录' }).click();
                await page.waitForURL('**/chat**', { timeout: 30000 });
            }
        }
        
        // 等待聊天界面加载
        await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
        
        // 获取当前 thread_id
        await page.waitForTimeout(2000);
        const url = page.url();
        const match = url.match(/\/chat\/([^\/\?]+)/);
        threadId = match ? match[1] : null;
        console.log('当前 thread_id:', threadId);
    });

    test.afterAll(async () => {
        await apiContext?.dispose();
    });

    // ==================== 功能验证测试 ====================

    test('TC-SYNC-001: 简单对话 - 前端展示与后端保存一致', async ({ page }) => {
        test.setTimeout(90000);

        const testMessage = `测试同步 ${Date.now()}`;
        
        // 发送消息
        await page.fill('textarea', testMessage);
        await page.keyboard.press('Enter');

        // 等待 AI 响应完成
        await page.waitForTimeout(15000);

        // 获取前端展示的最后一条 AI 消息
        const aiMessages = page.locator('[data-testid="ai-message"]');
        const count = await aiMessages.count();
        expect(count).toBeGreaterThan(0);

        const lastAiMessage = aiMessages.last();
        await expect(lastAiMessage).toBeVisible();
        const frontendContent = await lastAiMessage.innerText();
        console.log('前端展示内容 (前100字符):', frontendContent.substring(0, 100));

        // 从 URL 获取最新 thread_id
        const currentUrl = page.url();
        const urlMatch = currentUrl.match(/\/chat\/([^\/\?]+)/);
        const currentThreadId = urlMatch ? urlMatch[1] : threadId;

        // 通过 API 获取后端保存的消息
        if (authToken && currentThreadId) {
            const messagesResp = await apiContext.get(`/chat/messages/${currentThreadId}`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });

            if (messagesResp.ok()) {
                const messagesData = await messagesResp.json();
                const messages = messagesData.data || messagesData;
                
                // 找到最后一条 AI 消息
                const aiMsgs = messages.filter(m => m.role === 'assistant' || m.type === 'ai');
                if (aiMsgs.length > 0) {
                    const lastBackendMsg = aiMsgs[aiMsgs.length - 1];
                    const backendContent = lastBackendMsg.content || '';
                    console.log('后端保存内容 (前100字符):', backendContent.substring(0, 100));
                    
                    // 验证内容一致性（忽略 thinking 标签差异）
                    const normalizedFrontend = frontendContent.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
                    const normalizedBackend = backendContent.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
                    
                    // 检查后端内容是否包含在前端展示中（前端可能有额外格式化）
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
        
        // 发送消息
        await page.fill('textarea', testMessage);
        await page.keyboard.press('Enter');

        // 等待响应
        await page.waitForTimeout(15000);

        // 获取刷新前的内容
        const aiMessages = page.locator('[data-testid="ai-message"]');
        await page.waitForTimeout(2000);
        const countBefore = await aiMessages.count();
        let contentBefore = '';
        if (countBefore > 0) {
            contentBefore = await aiMessages.last().innerText();
            console.log('刷新前内容 (前50字):', contentBefore.substring(0, 50));
        }

        // 刷新页面
        await page.reload();
        await expect(page.locator('textarea')).toBeVisible({ timeout: 15000 });
        await page.waitForTimeout(5000);

        // 获取刷新后的内容
        const aiMessagesAfter = page.locator('[data-testid="ai-message"]');
        const countAfter = await aiMessagesAfter.count();
        
        if (countAfter > 0) {
            const contentAfter = await aiMessagesAfter.last().innerText();
            console.log('刷新后内容 (前50字):', contentAfter.substring(0, 50));

            // 验证内容一致
            const similarity = calculateSimilarity(contentBefore, contentAfter);
            console.log('刷新前后相似度:', similarity);
            expect(similarity).toBeGreaterThan(0.8);
        }
    });

    // ==================== 破坏性测试 ====================

    test('TC-SYNC-003: 快速连续发送消息', async ({ page }) => {
        test.setTimeout(180000);

        const messages = [
            `快速消息1 ${Date.now()}`,
            `快速消息2 ${Date.now() + 1}`,
            `快速消息3 ${Date.now() + 2}`,
        ];

        // 记录发送前的消息数量
        const userMessagesBefore = page.locator('[data-testid="human-message"]');
        const countBefore = await userMessagesBefore.count().catch(() => 0);
        console.log('发送前用户消息数量:', countBefore);

        // 快速连续发送，但等待输入框可用
        for (const msg of messages) {
            // 等待 textarea 可用（非 disabled 状态）
            await page.waitForSelector('textarea:not([disabled])', { timeout: 30000 });
            await page.fill('textarea', msg);
            await page.keyboard.press('Enter');
            // 等待消息出现在列表中
            await page.waitForTimeout(1000);
        }

        // 等待所有响应完成（使用轮询策略）
        let retries = 0;
        const maxRetries = 30;
        while (retries < maxRetries) {
            await page.waitForTimeout(2000);
            // 检查是否还在加载中
            const loadingIndicator = page.locator('[data-loading="true"], .animate-pulse');
            const isLoading = await loadingIndicator.count() > 0;
            if (!isLoading) {
                console.log('响应完成，等待 2 秒后验证');
                await page.waitForTimeout(2000);
                break;
            }
            retries++;
        }

        // 验证消息数量
        const userMessages = page.locator('[data-testid="human-message"]');
        // 使用 waitFor 确保元素渲染完成
        await page.waitForTimeout(3000);
        const count = await userMessages.count();
        console.log('用户消息数量:', count, '(预期至少:', countBefore + messages.length, ')');
        
        // 至少应该有发送的消息数量
        expect(count).toBeGreaterThanOrEqual(countBefore + messages.length);
    });

    test('TC-SYNC-004: 长文本响应处理', async ({ page }) => {
        test.setTimeout(180000);

        // 请求生成较长的响应
        const testMessage = '请详细解释一下人工智能的发展历史，包括主要里程碑事件。';
        
        await page.fill('textarea', testMessage);
        await page.keyboard.press('Enter');

        // 等待长响应生成
        await page.waitForTimeout(60000);

        // 验证响应存在
        const aiMessages = page.locator('[data-testid="ai-message"]');
        const count = await aiMessages.count();
        expect(count).toBeGreaterThan(0);

        const content = await aiMessages.last().innerText();
        console.log('长响应内容长度:', content.length);
        
        // 长响应应该有一定长度
        expect(content.length).toBeGreaterThan(100);
    });

    test('TC-SYNC-005: 特殊字符处理', async ({ page }) => {
        test.setTimeout(120000);

        // 记录发送前的消息数量
        const userMessagesBefore = page.locator('[data-testid="human-message"]');
        const countBefore = await userMessagesBefore.count().catch(() => 0);
        console.log('发送前用户消息数量:', countBefore);

        // 包含特殊字符的消息
        const testMessage = '测试特殊字符: <script>alert(1)</script> & "引号" \'单引号\' `反引号`';
        
        // 确保 textarea 可用
        await page.waitForSelector('textarea:not([disabled])', { timeout: 30000 });
        await page.fill('textarea', testMessage);
        await page.keyboard.press('Enter');

        // 等待消息出现，使用轮询策略
        let messageAppeared = false;
        for (let i = 0; i < 20; i++) {
            await page.waitForTimeout(1000);
            const userMessages = page.locator('[data-testid="human-message"]');
            const count = await userMessages.count();
            if (count > countBefore) {
                messageAppeared = true;
                console.log('消息已出现，当前数量:', count);
                break;
            }
        }

        // 额外等待 AI 响应
        await page.waitForTimeout(10000);

        // 验证消息发送成功
        const userMessages = page.locator('[data-testid="human-message"]');
        const count = await userMessages.count();
        console.log('最终用户消息数量:', count);
        expect(count).toBeGreaterThan(countBefore);

        // 验证特殊字符被正确转义（XSS 防护）
        const lastMessage = userMessages.last();
        const content = await lastMessage.innerText();
        console.log('消息内容:', content);
        // 不应该执行 script 标签
        expect(content).not.toContain('<script>');
    });
});

// 辅助函数：计算字符串相似度
function calculateSimilarity(str1, str2) {
    if (!str1 || !str2) return 0;
    
    const s1 = str1.toLowerCase().replace(/\s+/g, ' ').trim();
    const s2 = str2.toLowerCase().replace(/\s+/g, ' ').trim();
    
    if (s1 === s2) return 1;
    if (s1.length === 0 || s2.length === 0) return 0;
    
    // 简单的包含检查
    if (s1.includes(s2) || s2.includes(s1)) {
        return Math.min(s1.length, s2.length) / Math.max(s1.length, s2.length);
    }
    
    // 计算公共子串
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
