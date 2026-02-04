const { test, expect } = require('@playwright/test');
const { loginIfNeeded, ensureChatReady } = require('../helpers/auth-helper');

/**
 * 需求文档: docs/产品文档/聊天系统需求.md
 * 测试用例: docs/开发文档/测试管理/聊天系统测试案例.md
 * @test-case TC-CHAT-01
 */
test.describe('用户故事: 聊天系统', () => {
    test('US-CHAT-01: 发送消息后获得流式响应', async ({ page }) => {
        test.setTimeout(90000);
        const message = `你好，简短回复我 ${Date.now()}`;

        await test.step('Given: 用户已登录并进入聊天界面', async () => {
            await loginIfNeeded(page, { username: 'admin', password: '123456' });
            await ensureChatReady(page);
        });

        await test.step('When: 用户发送消息', async () => {
            await page.fill('textarea', message);
            await page.keyboard.press('Enter');
            await expect(page.locator('.bg-muted').getByText(message)).toBeVisible({ timeout: 10000 });
        });

        await test.step('Then: AI 返回可见响应内容', async () => {
            const aiMessages = page.locator('[data-testid="ai-message"]');
            await expect(aiMessages.last()).toBeVisible({ timeout: 20000 });
            const content = await aiMessages.last().innerText();
            expect(content.trim().length).toBeGreaterThan(0);
        });
    });
});
