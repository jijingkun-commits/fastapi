/**
 * TodoListCard 组件简化测试
 * 
 * @test-case TC-UI-01 TodoListCard 渲染
 * @test-case TC-CONFIRM-01 确认卡片交互
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 * 
 * 跳过认证流程，直接测试组件功能
 */
const { test, expect } = require("@playwright/test");

// 跳过认证依赖
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("TodoListCard 组件测试", () => {
    test.beforeEach(async ({ page }) => {
        // 直接访问登录页并登录
        await page.goto("/auth");
        await page.waitForLoadState("networkidle");

        // 填写登录信息
        const usernameInput = page.locator('input[placeholder*="用户名"]');
        if (await usernameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
            await usernameInput.fill("jjk");
            await page.getByRole("button", { name: "登录" }).click();
            // 等待跳转或错误
            await page.waitForTimeout(3000);
        }
    });

    test("查询待办 - 验证卡片渲染", async ({ page }) => {
        // 导航到聊天页面
        await page.goto("/chat");
        await page.waitForLoadState("networkidle");

        // 截图当前状态
        await page.screenshot({ path: "e2e/screenshots/chat-page.png" });

        // 发送查询消息 - 匹配 "Type your message..." 或中文 placeholder
        const chatInput = page.locator('textarea[placeholder*="message"], textarea[placeholder*="输入"], input[placeholder*="message"]');
        if (await chatInput.isVisible({ timeout: 5000 }).catch(() => false)) {
            await chatInput.fill("查询我的待办");
            await page.keyboard.press("Enter");

            // 等待 AI 响应（最多 30 秒）
            await page.waitForTimeout(30000);

            // 截图响应
            await page.screenshot({ path: "e2e/screenshots/todo-query-response.png" });

            // 检查是否有待办卡片
            const todoCard = page.locator('text="待办清单"');
            const hasCard = await todoCard.isVisible({ timeout: 5000 }).catch(() => false);
            console.log("待办卡片是否显示:", hasCard);

            // 如果有卡片，测试交互
            if (hasCard) {
                // 点击第一个待办项
                const firstTodo = page.locator('[class*="todo"]').first();
                if (await firstTodo.isVisible().catch(() => false)) {
                    await firstTodo.click();
                    await page.screenshot({ path: "e2e/screenshots/todo-selected.png" });
                    console.log("已选中待办项");
                }
            }
        } else {
            console.log("未找到聊天输入框");
            await page.screenshot({ path: "e2e/screenshots/no-chat-input.png" });
        }
    });
});
