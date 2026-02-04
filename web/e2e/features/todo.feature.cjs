const { test, expect } = require('@playwright/test');
const { loginIfNeeded, ensureChatReady, waitForAIResponse, sendMessageAndWait } = require('../helpers/auth-helper');

/**
 * 需求文档: docs/产品文档/待办助手需求.md
 * 测试用例: docs/开发文档/测试管理/待办助手测试案例.md
 * @test-case TC-CRUD-01
 * @test-case TC-CRUD-02
 */
test.describe('用户故事: 待办助手', () => {
    test('US-TODO-01: 创建待办并可查询', async ({ page }) => {
        test.setTimeout(120000);
        const todoTitle = `BDD-待办-${Date.now()}`;
        const createMessage = `帮我创建一个待办：${todoTitle}，优先级高`;
        const listMessage = '列出我的所有待办';

        await test.step('Given: 用户已登录并进入聊天界面', async () => {
            await loginIfNeeded(page, { username: 'admin', password: '123456' });
            await ensureChatReady(page);
        });

        await test.step('When: 用户发送创建待办的消息', async () => {
            await sendMessageAndWait(page, createMessage, 60000);
            await expect(page.locator('.bg-muted').getByText(createMessage)).toBeVisible({ timeout: 10000 });
        });

        await test.step('Then: 通过查询验证待办已创建', async () => {
            await sendMessageAndWait(page, listMessage, 30000);
            await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 20000 });
        });
    });
});
