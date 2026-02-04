/**
 * 待办 Agent 基础 E2E 测试
 * 
 * @test-case TC-CRUD-01 创建单个待办
 * @test-case TC-CRUD-02 查询待办列表
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { sendMessageAndWait, waitForChatReady } = require('./helpers/auth-helper');

test.describe('Todo Agent E2E Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Listen to console logs
        page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('pageerror', err => console.log(`PAGE ERROR: ${err.toString()}`));

        // 1. Go to Login Page
        await page.goto('/auth');

        // Handle login if redirected (check if we are on auth page)
        if (page.url().includes('/auth')) {
            await expect(page.getByText('登录到系统')).toBeVisible();
            await page.fill('input#identifier', 'admin');
            await page.fill('input#password', '123456');
            await page.getByRole('button', { name: '登录' }).click();
        }

        // 2. Wait for redirect to home/chat
        try {
            await page.waitForURL('**/', { timeout: 15000 });
        } catch (e) {
            console.log('Wait for / timeout, current URL:', page.url());
        }

        // 3. Verify Chat Interface
        await expect(page).toHaveTitle(/嘉银助手|Chat/i);
        await expect(page.locator('[data-testid="chat-input-container"]')).toBeVisible({ timeout: 30000 });
        await expect(page.getByText('AI 可能会出错')).toBeVisible();
    });

    /**
     * @test-case TC-CRUD-01, TC-CRUD-02
     * @description 创建待办并通过查询验证
     */
    test('should create and list todos via chat', async ({ page }) => {
        test.setTimeout(180000);

        const todoTitle = `Buy Milk ${Date.now()}`;

        // 1. Send Create Request and wait for AI response (auto-confirm)
        const createMessage = `帮我创建一个待办：${todoTitle}，优先级高`;
        await sendMessageAndWait(page, createMessage, 60000, true);

        // 2. Send List Request and wait for AI response
        const listMessage = '列出我的所有待办';
        await sendMessageAndWait(page, listMessage, 30000, false);

        // 3. Verify the new todo is in the response
        await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 20000 });
    });
});
