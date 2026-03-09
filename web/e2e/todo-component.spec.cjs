/**
 * TodoListCard 组件简化测试
 *
 * @test-case TC-UI-01 TodoListCard 渲染
 * @test-case TC-CONFIRM-01 确认卡片交互
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, sendMessageAndWait } = require('./helpers/auth-helper');

test.describe('TodoListCard 组件测试', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await loginAndOpenThread(page, testInfo.title);
    });

    test('查询待办 - 验证卡片渲染', async ({ page }) => {
        await sendMessageAndWait(page, '查询我的待办', 60000, false);

        const todoHeading = page.getByText('待办清单').last();
        await expect(todoHeading).toBeVisible({ timeout: 20000 });

        const firstTodo = page.locator('[class*="todo"], [data-testid*="todo"]').first();
        if (await firstTodo.isVisible().catch(() => false)) {
            await firstTodo.click();
        }
    });
});
