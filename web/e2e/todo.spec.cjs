/**
 * 待办 Agent 基础 E2E 测试
 *
 * @test-case TC-CRUD-01 创建单个待办
 * @test-case TC-CRUD-02 查询待办列表
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, sendMessageAndWait } = require('./helpers/auth-helper');

test.describe('Todo Agent E2E Flow', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        page.on('console', (msg) => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('pageerror', (err) => console.log(`PAGE ERROR: ${err.toString()}`));
        await loginAndOpenThread(page, testInfo.title);
    });

    test('should create and list todos via chat', async ({ page }) => {
        test.setTimeout(180000);

        const todoTitle = `Buy Milk ${Date.now()}`;
        await sendMessageAndWait(page, `帮我创建一个待办：${todoTitle}，优先级高`, 60000, true);
        await sendMessageAndWait(page, '列出我的所有待办', 30000, false);
        await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 20000 });
    });
});
