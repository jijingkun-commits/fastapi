/**
 * 确认卡片深度测试
 *
 * @test-case TC-CONFIRM-01 创建确认卡片
 * @test-case TC-CONFIRM-02 更新确认卡片
 * @test-case TC-CONFIRM-03 删除确认卡片
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, sendMessageAndWait, waitForChatReady } = require('./helpers/auth-helper');

async function sendRawMessage(page, message) {
    await waitForChatReady(page, 30000);
    await page.fill('textarea', message);
    await page.keyboard.press('Enter');
}

test.describe('Todo Card Deep Testing', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        page.on('console', (msg) => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('pageerror', (err) => console.log(`PAGE ERROR: ${err.toString()}`));
        await loginAndOpenThread(page, testInfo.title);
    });

    test('ConfirmationCard - 确认创建待办', async ({ page }) => {
        test.setTimeout(90000);

        const todoTitle = `CardTest_${Date.now()}`;
        await sendRawMessage(page, `创建待办：${todoTitle}`);

        const confirmBtn = page.locator('[data-testid="confirm-button"]');
        await expect(confirmBtn).toBeVisible({ timeout: 60000 });
        await confirmBtn.click();
        await waitForChatReady(page, 60000);

        await sendMessageAndWait(page, '查看我的待办', 60000, false);
        await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 15000 });
    });

    test('ConfirmationCard - 编辑后确认', async ({ page }) => {
        test.setTimeout(90000);

        const todoTitle = `EditTest_${Date.now()}`;
        await sendRawMessage(page, `创建待办：${todoTitle}`);

        const editBtn = page.locator('button:has-text("编辑"), [aria-label*="edit"]');
        await expect(editBtn.first()).toBeVisible({ timeout: 60000 });
        await editBtn.first().click();

        const titleInput = page.locator('input[value*="EditTest"], input[placeholder*="标题"]');
        await expect(titleInput).toBeVisible({ timeout: 10000 });
        await titleInput.fill(`${todoTitle}_Modified`);

        const confirmBtn = page.locator('[data-testid="confirm-button"]');
        await expect(confirmBtn).toBeVisible({ timeout: 10000 });
        await confirmBtn.click();
        await waitForChatReady(page, 60000);
        await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible();
    });

    test('ConfirmationCard - 拒绝创建', async ({ page }) => {
        test.setTimeout(90000);

        const todoTitle = `RejectTest_${Date.now()}`;
        await sendRawMessage(page, `创建待办：${todoTitle}`);

        const rejectBtn = page.locator('[data-testid="reject-button"]');
        await expect(rejectBtn).toBeVisible({ timeout: 60000 });
        await rejectBtn.click();
        await waitForChatReady(page, 60000);

        await sendMessageAndWait(page, '查看我的待办', 60000, false);
        await expect(page.locator('[data-testid="ai-message"]').last()).not.toContainText(todoTitle);
    });

    test('TodoListCard - 查看待办列表', async ({ page }) => {
        test.setTimeout(60000);

        await sendMessageAndWait(page, '列出我所有的待办事项', 60000, false);

        const todoList = page.locator('[class*="todo"], [data-testid*="todo"]');
        if (await todoList.first().isVisible({ timeout: 5000 }).catch(() => false)) {
            await expect(todoList.first()).toBeVisible();
            return;
        }

        const listItems = page.locator('li, .todo-item');
        await expect.poll(async () => listItems.count(), { timeout: 10000 }).toBeGreaterThan(0);
    });
});
