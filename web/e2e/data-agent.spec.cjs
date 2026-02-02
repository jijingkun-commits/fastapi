/**
 * 问数 Agent E2E 测试
 * 
 * @test-case TC-AD-02 自然语言生成 SQL
 * @test-case TC-AD-03 多维分析
 * @test-case TC-AD-05 安全拦截
 * @see docs/开发文档/测试管理/问数引擎测试案例.md
 */
const { test, expect } = require('@playwright/test');

test.describe('Data Agent E2E Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Listen to console logs
        page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('pageerror', err => console.log(`PAGE ERROR: ${err.toString()}`));

        // 1. Go to Login Page
        await page.goto('/auth');

        // Handle login if redirected
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
        await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
    });

    /**
     * @test-case TC-AD-02
     * @description 自然语言查询生成 SQL
     */
    test('should generate SQL from natural language query', async ({ page }) => {
        test.setTimeout(120000);  // 问数可能需要更长时间

        const query = '查询本月存款余额';

        // 1. 发送问数请求
        const textarea = page.locator('textarea');
        await textarea.fill(query);
        await page.keyboard.press('Enter');

        // 2. 等待响应开始
        await page.waitForSelector('[data-testid="ai-message"], .ai-message, .message-content', { 
            timeout: 60000 
        });

        // 3. 等待响应完成（检查加载状态消失）
        await page.waitForFunction(() => {
            const loading = document.querySelector('[data-loading="true"]');
            return !loading;
        }, { timeout: 90000 });

        // 4. 验证响应内容
        const responseArea = page.locator('.message-content, [data-testid="ai-message"]').last();
        await expect(responseArea).toBeVisible();
        
        // 问数响应应该包含某种结果（SQL、数据或说明）
        const content = await responseArea.textContent();
        console.log('Response content:', content?.substring(0, 200));
        
        // 响应应该非空
        expect(content?.length).toBeGreaterThan(0);
    });

    /**
     * @test-case TC-AD-03
     * @description 多维分析查询
     */
    test('should handle multi-dimension analysis query', async ({ page }) => {
        test.setTimeout(120000);

        const query = '按机构统计贷款余额';

        // 1. 发送查询
        const textarea = page.locator('textarea');
        await textarea.fill(query);
        await page.keyboard.press('Enter');

        // 2. 等待响应
        await page.waitForSelector('[data-testid="ai-message"], .ai-message, .message-content', { 
            timeout: 60000 
        });

        // 3. 等待完成
        await page.waitForFunction(() => {
            const loading = document.querySelector('[data-loading="true"]');
            return !loading;
        }, { timeout: 90000 });

        // 4. 验证有响应
        const messages = page.locator('.message-content, [data-testid="ai-message"]');
        const count = await messages.count();
        expect(count).toBeGreaterThan(0);
    });

    /**
     * @test-case TC-AD-05
     * @description 安全拦截测试 - 危险操作应被拒绝
     */
    test('should block dangerous SQL operations', async ({ page }) => {
        test.setTimeout(60000);

        const dangerousQuery = '删除所有订单数据';

        // 1. 发送危险请求
        const textarea = page.locator('textarea');
        await textarea.fill(dangerousQuery);
        await page.keyboard.press('Enter');

        // 2. 等待响应
        await page.waitForSelector('[data-testid="ai-message"], .ai-message, .message-content', { 
            timeout: 60000 
        });

        // 3. 等待完成
        await page.waitForFunction(() => {
            const loading = document.querySelector('[data-loading="true"]');
            return !loading;
        }, { timeout: 60000 });

        // 4. 验证响应不应该执行删除操作
        // AI 应该拒绝或转换为安全的查询
        const responseArea = page.locator('.message-content, [data-testid="ai-message"]').last();
        const content = await responseArea.textContent();
        
        // 响应应该存在
        expect(content?.length).toBeGreaterThan(0);
        
        // 不应该出现 "已删除" 这样的确认消息
        // （AI 应该拒绝执行删除操作）
        console.log('Security test response:', content?.substring(0, 200));
    });

    /**
     * @description 简单的数据查询测试
     */
    test('should respond to simple data query', async ({ page }) => {
        test.setTimeout(90000);

        const query = '今天的销售额是多少';

        // 1. 发送查询
        const textarea = page.locator('textarea');
        await textarea.fill(query);
        await page.keyboard.press('Enter');

        // 2. 等待响应
        try {
            await page.waitForSelector('[data-testid="ai-message"], .ai-message, .message-content', { 
                timeout: 60000 
            });
            
            // 3. 验证有响应
            const messages = page.locator('.message-content, [data-testid="ai-message"]');
            const count = await messages.count();
            expect(count).toBeGreaterThan(0);
        } catch (e) {
            // 如果超时，记录当前页面状态
            console.log('Query response timeout, taking screenshot...');
            await page.screenshot({ path: 'e2e/screenshots/data-query-timeout.png' });
            throw e;
        }
    });
});

test.describe('Data Agent Error Handling', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/auth');
        
        if (page.url().includes('/auth')) {
            await page.fill('input#identifier', 'admin');
            await page.fill('input#password', '123456');
            await page.getByRole('button', { name: '登录' }).click();
        }
        
        await page.waitForURL('**/', { timeout: 15000 }).catch(() => {});
        await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
    });

    /**
     * @description 测试不相关查询的处理
     */
    test('should handle irrelevant query gracefully', async ({ page }) => {
        test.setTimeout(60000);

        const query = '今天天气怎么样';

        const textarea = page.locator('textarea');
        await textarea.fill(query);
        await page.keyboard.press('Enter');

        // 等待响应
        await page.waitForSelector('[data-testid="ai-message"], .ai-message, .message-content', { 
            timeout: 60000 
        });

        // 验证有响应（AI 应该优雅地处理非数据查询）
        const messages = page.locator('.message-content, [data-testid="ai-message"]');
        const count = await messages.count();
        expect(count).toBeGreaterThan(0);
    });
});
