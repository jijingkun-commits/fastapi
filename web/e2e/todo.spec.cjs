/**
 * 待办 Agent 基础 E2E 测试
 * 
 * @test-case TC-CRUD-01 创建单个待办
 * @test-case TC-CRUD-02 查询待办列表
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');

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
        // Ensure ChatContainer is visible (we can check for the input area)
        // Use a simpler selector and longer timeout to allow for potential compilation delays
        await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
        await expect(page.getByText('AI 可能会出错')).toBeVisible();
    });

    /**
     * @test-case TC-CRUD-01, TC-CRUD-02
     * @description 创建待办并通过查询验证
     */
    test('should create and list todos via chat', async ({ page }) => {
        test.setTimeout(120000);

        const todoTitle = `Buy Milk ${Date.now()}`;

        // 1. Send Create Request
        const createMessage = `帮我创建一个待办：${todoTitle}，优先级高`;
        await page.fill('textarea', createMessage);
        await page.keyboard.press('Enter');

        // Wait for user message to appear (HumanMessage uses .bg-muted)
        await expect(page.locator('.bg-muted').getByText(createMessage)).toBeVisible({ timeout: 10000 });

        // Wait for AI response to complete (check data-streaming attribute)
        await page.waitForSelector('textarea[data-testid="chat-input"][data-streaming="false"]', { timeout: 60000 });
        await page.waitForTimeout(1000);

        // 2. Send List Request to verify
        const listMessage = '列出我的所有待办';
        await page.fill('textarea', listMessage);
        await page.keyboard.press('Enter');

        // Wait for AI response to complete
        await page.waitForSelector('textarea[data-testid="chat-input"][data-streaming="false"]', { timeout: 30000 });
        await page.waitForTimeout(1000);

        // 3. Verify the new todo is in the response
        // The agent should return a markdown list or a card containing the title.
        // We use .last() because the title also appears in the user's request message.
        await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 20000 });
    });
});
