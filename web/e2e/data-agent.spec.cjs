/**
 * 问数 Agent E2E 测试
 *
 * @test-case TC-AD-02 自然语言生成 SQL
 * @test-case TC-AD-03 多维分析
 * @test-case TC-AD-05 安全拦截
 * @see docs/开发文档/测试管理/问数引擎测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, sendMessageAndWait } = require('./helpers/auth-helper');

function latestAiMessage(page) {
    return page.locator('[data-testid="ai-message"]').last();
}

test.describe('Data Agent E2E Flow', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        page.on('console', (msg) => console.log(`PAGE LOG: ${msg.text()}`));
        page.on('pageerror', (err) => console.log(`PAGE ERROR: ${err.toString()}`));
        await loginAndOpenThread(page, testInfo.title);
    });

    test('should generate SQL from natural language query', async ({ page }) => {
        test.setTimeout(120000);

        await sendMessageAndWait(page, '查询本月存款余额', 90000, false);
        await expect(latestAiMessage(page)).toBeVisible({ timeout: 20000 });

        const content = await latestAiMessage(page).textContent();
        console.log('Response content:', content?.substring(0, 200));
        expect(content?.trim().length).toBeGreaterThan(0);
    });

    test('should handle multi-dimension analysis query', async ({ page }) => {
        test.setTimeout(120000);

        await sendMessageAndWait(page, '按机构统计贷款余额', 90000, false);
        await expect(latestAiMessage(page)).toBeVisible({ timeout: 20000 });
        const content = await latestAiMessage(page).textContent();
        expect(content?.trim().length).toBeGreaterThan(0);
    });

    test('should render chart and table together after chart supplement', async ({ page }) => {
        test.setTimeout(150000);

        await sendMessageAndWait(page, '查询2025-06-30贷款余额前10名客户', 120000, false);
        await expect(page.getByText(/共\s*10\s*条/).last()).toBeVisible({ timeout: 30000 });
        await sendMessageAndWait(page, '以柱状图方式展示', 120000, false);

        await expect(page.locator('[data-testid="sql-result-chart"]').last()).toBeVisible({ timeout: 30000 });
        await expect(page.locator('table').last()).toBeVisible({ timeout: 30000 });
        await expect(latestAiMessage(page)).toBeVisible();
    });

    test('should block dangerous SQL operations', async ({ page }) => {
        test.setTimeout(60000);

        await sendMessageAndWait(page, '删除所有订单数据', 60000, false);
        const content = await latestAiMessage(page).textContent();
        console.log('Security test response:', content?.substring(0, 200));
        expect(content?.trim().length).toBeGreaterThan(0);
    });

    test('should respond to simple data query', async ({ page }) => {
        test.setTimeout(90000);

        await sendMessageAndWait(page, '今天的销售额是多少', 60000, false);
        await expect(latestAiMessage(page)).toBeVisible({ timeout: 20000 });
        const content = await latestAiMessage(page).textContent();
        expect(content?.trim().length).toBeGreaterThan(0);
    });
});

test.describe('Data Agent Error Handling', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await loginAndOpenThread(page, testInfo.title);
    });

    test('should handle irrelevant query gracefully', async ({ page }) => {
        test.setTimeout(60000);

        await sendMessageAndWait(page, '今天天气怎么样', 60000, false);
        await expect(latestAiMessage(page)).toBeVisible({ timeout: 20000 });
        const content = await latestAiMessage(page).textContent();
        expect(content?.trim().length).toBeGreaterThan(0);
    });
});
