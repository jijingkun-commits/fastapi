const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, ensureChatReady, sendMessageAndWait } = require('../helpers/auth-helper');

/**
 * 需求文档: docs/产品文档/待办助手需求.md
 * 测试用例: docs/开发文档/测试管理/待办助手测试案例.md
 * @test-case TC-CRUD-01
 * @test-case TC-CRUD-02
 */
test.describe('用户故事: 待办助手', () => {
    test('US-TODO-01: 创建待办并可查询', async ({ page }, testInfo) => {
        test.setTimeout(180000);
        const todoTitle = `BDD-待办-${Date.now()}`;

        await test.step('Given: 用户已登录并进入聊天界面', async () => {
            await loginAndOpenThread(page, testInfo.title);
            await ensureChatReady(page);
        });

        await test.step('When: 用户发送创建待办的消息', async () => {
            await sendMessageAndWait(page, `帮我创建一个待办：${todoTitle}，优先级高`, 60000, true);
        });

        await test.step('Then: 通过查询验证待办已创建', async () => {
            await sendMessageAndWait(page, '列出我的所有待办', 30000, false);
            await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 20000 });
        });
    });
});
