const { test, expect } = require('@playwright/test');
const { loginAndGoto } = require('../helpers/auth-helper');

/**
 * 需求文档: docs/产品文档/管理后台需求.md
 * 测试用例: docs/开发文档/测试管理/管理后台测试案例.md
 * @test-case TC-ADMIN-02
 */
test.describe('用户故事: 管理后台', () => {
    test('US-ADMIN-02: 进入 LLM 配置管理页面', async ({ page }) => {
        test.setTimeout(60000);

        await test.step('Given/When: 管理员进入 LLM 配置页面', async () => {
            await loginAndGoto(page, '/admin/llm');
        });

        await test.step('Then: 页面显示 LLM 配置相关内容', async () => {
            await expect(page.getByRole('heading', { name: '大模型配置' })).toBeVisible({ timeout: 15000 });
            await expect(page.getByText('模型列表')).toBeVisible();
        });
    });
});
