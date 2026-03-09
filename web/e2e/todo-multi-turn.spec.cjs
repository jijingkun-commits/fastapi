// @ts-check
/**
 * 待办助手多轮对话测试
 *
 * @test-case TC-MULTI-01 多轮对话：创建→查询→完成
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, sendMessageAndWait } = require('./helpers/auth-helper');

function latestAiMessage(page) {
    return page.locator('[data-testid="ai-message"]').last();
}

test.describe('待办助手多轮对话测试', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await loginAndOpenThread(page, testInfo.title, {}, 60000);
    });

    test('多轮对话：创建→查询→完成待办', async ({ page }) => {
        test.setTimeout(180000);

        const todoTitle = `测试待办${Date.now().toString().slice(-6)}`;

        console.log('=== 第一轮：创建待办 ===');
        await sendMessageAndWait(page, `帮我创建一个待办：${todoTitle}`, 90000, true);

        console.log('\n=== 第二轮：查询待办 ===');
        await sendMessageAndWait(page, '查看我的待办列表', 60000, false);

        console.log('\n=== 第三轮：完成待办 ===');
        await sendMessageAndWait(page, `完成待办：${todoTitle}`, 90000, true);
        await expect(latestAiMessage(page)).toContainText(/已完成|完成/, { timeout: 20000 });
    });

    test('多轮对话：创建→删除待办', async ({ page }) => {
        test.setTimeout(180000);

        const todoTitle = `删除测试${Date.now().toString().slice(-6)}`;

        console.log('=== 第一轮：创建待办 ===');
        await sendMessageAndWait(page, `创建待办：${todoTitle}，优先级高`, 90000, true);

        console.log('\n=== 第二轮：删除待办 ===');
        await sendMessageAndWait(page, `删除待办：${todoTitle}`, 90000, true);

        await expect(latestAiMessage(page)).toContainText(/已删除|删除/, { timeout: 20000 });
    });
});
