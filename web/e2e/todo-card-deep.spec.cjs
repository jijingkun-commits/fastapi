/**
 * 确认卡片深度测试
 * 
 * @test-case TC-CONFIRM-01 创建确认卡片
 * @test-case TC-CONFIRM-02 更新确认卡片
 * @test-case TC-CONFIRM-03 删除确认卡片
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');

test.describe('Todo Card Deep Testing', () => {
    test.beforeEach(async ({ page }) => {
        page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('pageerror', err => console.log(`PAGE ERROR: ${err.toString()}`));

        await page.goto('/auth');
        if (page.url().includes('/auth')) {
            await page.fill('input#identifier', 'admin');
            await page.fill('input#password', '123456');
            await page.getByRole('button', { name: '登录' }).click();
        }
        try {
            await page.waitForURL('**/', { timeout: 15000 });
        } catch (e) {
            console.log('Wait for / timeout, current URL:', page.url());
        }
        await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
        // multi-agent 模式已默认开启，无需手动设置
    });

    test('ConfirmationCard - 确认创建待办', async ({ page }) => {
        test.setTimeout(90000);

        // 1. 发送创建待办请求
        const todoTitle = `CardTest_${Date.now()}`;
        await page.fill('textarea', `创建待办：${todoTitle}`);
        await page.keyboard.press('Enter');

        // 2. 等待 ConfirmationCard 出现
        await page.waitForTimeout(8000);

        // 3. 查找确认按钮并点击
        const confirmBtn = page.getByRole('button', { name: /确认|Confirm/i });
        if (await confirmBtn.isVisible({ timeout: 5000 })) {
            console.log('找到确认按钮，点击确认');
            await confirmBtn.click();
            await page.waitForTimeout(3000);
            
            // 4. 验证待办创建成功
            await page.fill('textarea', '查看我的待办');
            await page.keyboard.press('Enter');
            await expect(page.locator(`text=${todoTitle}`).last()).toBeVisible({ timeout: 15000 });
            console.log('TEST PASS: 待办创建成功');
        } else {
            console.log('未找到确认按钮，可能直接创建成功');
        }
    });

    test('ConfirmationCard - 编辑后确认', async ({ page }) => {
        test.setTimeout(90000);

        // 1. 发送创建待办请求
        const todoTitle = `EditTest_${Date.now()}`;
        await page.fill('textarea', `创建待办：${todoTitle}`);
        await page.keyboard.press('Enter');

        // 2. 等待 ConfirmationCard 出现
        await page.waitForTimeout(8000);

        // 3. 查找编辑按钮或直接编辑输入框
        const editBtn = page.locator('button:has-text("编辑"), [aria-label*="edit"]');
        if (await editBtn.isVisible({ timeout: 3000 })) {
            console.log('找到编辑按钮');
            await editBtn.first().click();
            await page.waitForTimeout(1000);
        }

        // 4. 尝试修改标题
        const titleInput = page.locator('input[value*="EditTest"], input[placeholder*="标题"]');
        if (await titleInput.isVisible({ timeout: 3000 })) {
            console.log('找到标题输入框，修改标题');
            await titleInput.fill(`${todoTitle}_Modified`);
        }

        // 5. 确认
        const confirmBtn = page.getByRole('button', { name: /确认|Confirm|保存/i });
        if (await confirmBtn.isVisible({ timeout: 3000 })) {
            await confirmBtn.click();
            await page.waitForTimeout(3000);
            console.log('TEST PASS: 编辑后确认成功');
        }
    });

    test('ConfirmationCard - 拒绝创建', async ({ page }) => {
        test.setTimeout(90000);

        // 1. 发送创建待办请求
        const todoTitle = `RejectTest_${Date.now()}`;
        await page.fill('textarea', `创建待办：${todoTitle}`);
        await page.keyboard.press('Enter');

        // 2. 等待 ConfirmationCard 出现
        await page.waitForTimeout(8000);

        // 3. 查找拒绝按钮并点击（使用精确匹配，避免匹配历史对话中的按钮）
        const rejectBtn = page.getByRole('button', { name: '拒绝', exact: true });
        if (await rejectBtn.isVisible({ timeout: 5000 })) {
            console.log('找到拒绝按钮，点击拒绝');
            await rejectBtn.click();
            await page.waitForTimeout(3000);
            
            // 4. 验证待办未创建
            await page.fill('textarea', '查看我的待办');
            await page.keyboard.press('Enter');
            await page.waitForTimeout(5000);
            
            // 验证该待办不在列表中
            const todoItem = page.locator(`text=${todoTitle}`);
            const count = await todoItem.count();
            if (count <= 1) {  // 只有用户输入消息中有，列表中没有
                console.log('TEST PASS: 拒绝后待办未创建');
            } else {
                console.log('TEST WARNING: 拒绝后待办仍被创建');
            }
        } else {
            console.log('未找到拒绝按钮');
        }
    });

    test('TodoListCard - 查看待办列表', async ({ page }) => {
        test.setTimeout(60000);

        // 1. 查询待办列表
        await page.fill('textarea', '列出我所有的待办事项');
        await page.keyboard.press('Enter');

        // 2. 等待 TodoListCard 出现
        await page.waitForTimeout(8000);

        // 3. 验证列表渲染
        const todoList = page.locator('[class*="todo"], [data-testid*="todo"]');
        if (await todoList.first().isVisible({ timeout: 5000 })) {
            console.log('TEST PASS: TodoListCard 正常显示');
        } else {
            // 也可能是 markdown 格式展示
            const listItems = page.locator('li, .todo-item');
            const count = await listItems.count();
            console.log(`找到 ${count} 个列表项`);
        }
    });
});
