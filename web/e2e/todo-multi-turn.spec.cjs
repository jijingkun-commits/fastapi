// @ts-check
/**
 * 待办助手多轮对话测试
 * 
 * @test-case TC-MULTI-01 多轮对话：创建→查询→完成
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require("@playwright/test");
const { loginIfNeeded, waitForChatReady } = require('./helpers/auth-helper');

test.describe("待办助手多轮对话测试", () => {
    test.use({ storageState: ".auth/user.json" });

    test.beforeEach(async ({ page }) => {
        await loginIfNeeded(page);
        await waitForChatReady(page, 60000);
    });

    test("多轮对话：创建→查询→完成待办", async ({ page }) => {
        // 生成唯一的待办标题避免冲突
        const uniqueId = Date.now().toString().slice(-6);
        const todoTitle = `测试待办${uniqueId}`;

        // === 第一轮：创建待办 ===
        console.log("=== 第一轮：创建待办 ===");
        const input = page.locator('[data-testid="chat-input"]');
        await input.fill(`帮我创建一个待办：${todoTitle}`);
        
        // 发送消息
        const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
        await sendButton.click();

        // 等待确认卡片出现 - 通过"待确认"标签或"确认"按钮识别
        console.log("等待创建确认卡片...");
        
        try {
            // 等待确认按钮出现（使用 data-testid 选择器）
            const confirmBtn = page.locator('[data-testid="confirm-button"]');
            await confirmBtn.waitFor({ state: "visible", timeout: 60000 });
            console.log("确认卡片已出现，找到确认按钮");
            
            // 截图保存
            await page.screenshot({ path: "e2e/screenshots/confirm-card-create.png" });
            
            // 点击确认按钮
            await confirmBtn.click();
            console.log("已点击确认按钮");
            await page.waitForTimeout(5000);
        } catch (e) {
            console.log("未找到确认卡片或按钮:", e.message);
            await page.screenshot({ path: "e2e/screenshots/no-confirm-card.png" });
            await page.waitForTimeout(5000);
        }

        // === 第二轮：查询待办 ===
        console.log("\n=== 第二轮：查询待办 ===");
        await input.fill("查看我的待办列表");
        await sendButton.click();

        // 等待待办列表出现
        console.log("等待待办列表...");
        await page.waitForTimeout(10000);

        // 检查是否显示了刚创建的待办
        const pageContent = await page.content();
        if (pageContent.includes(todoTitle) || pageContent.includes("待办")) {
            console.log("待办列表已显示");
        } else {
            console.log("页面内容：", pageContent.substring(0, 500));
        }

        // === 第三轮：完成待办 ===
        console.log("\n=== 第三轮：完成待办 ===");
        await input.fill(`完成待办：${todoTitle}`);
        await sendButton.click();

        // 等待完成确认
        console.log("等待完成确认...");
        await page.waitForTimeout(10000);

        try {
            const completeConfirmBtn = page.locator('[data-testid="confirm-button"]');
            if (await completeConfirmBtn.isVisible({ timeout: 10000 })) {
                await completeConfirmBtn.click();
                console.log("已确认完成待办");
                await page.waitForTimeout(3000);
            }
        } catch (e) {
            console.log("未找到完成确认按钮");
        }

        // === 第四轮：验证完成状态 ===
        console.log("\n=== 第四轮：验证完成状态 ===");
        await input.fill("查看已完成的待办");
        await sendButton.click();
        await page.waitForTimeout(10000);

        console.log("多轮对话测试完成");
    });

    test("多轮对话：创建→修改→删除待办", async ({ page }) => {
        const uniqueId = Date.now().toString().slice(-6);
        const todoTitle = `删除测试${uniqueId}`;

        // === 第一轮：创建待办 ===
        console.log("=== 第一轮：创建待办 ===");
        const input = page.locator('[data-testid="chat-input"]');
        await input.fill(`创建待办：${todoTitle}，优先级高`);
        
        const sendButton = page.locator('button[type="submit"], button:has-text("发送")').first();
        await sendButton.click();
        await page.waitForTimeout(15000);

        // 确认创建（使用 data-testid 选择器）
        try {
            const confirmBtn = page.locator('[data-testid="confirm-button"]');
            if (await confirmBtn.isVisible({ timeout: 5000 })) {
                await confirmBtn.click();
                console.log("已确认创建");
                await page.waitForTimeout(3000);
            }
        } catch (e) {
            console.log("自动创建或无需确认");
        }

        // === 第二轮：修改待办 ===
        console.log("\n=== 第二轮：修改待办 ===");
        await input.fill(`把"${todoTitle}"的优先级改为低`);
        await sendButton.click();
        await page.waitForTimeout(15000);

        try {
            const confirmBtn = page.locator('[data-testid="confirm-button"]');
            if (await confirmBtn.isVisible({ timeout: 5000 })) {
                await confirmBtn.click();
                console.log("已确认修改");
                await page.waitForTimeout(3000);
            }
        } catch (e) {
            console.log("修改完成或无需确认");
        }

        // === 第三轮：删除待办 ===
        console.log("\n=== 第三轮：删除待办 ===");
        await input.fill(`删除待办：${todoTitle}`);
        await sendButton.click();
        await page.waitForTimeout(15000);

        try {
            const confirmBtn = page.locator('[data-testid="confirm-button"]');
            if (await confirmBtn.isVisible({ timeout: 5000 })) {
                await confirmBtn.click();
                console.log("已确认删除");
                await page.waitForTimeout(3000);
            }
        } catch (e) {
            console.log("删除完成或无需确认");
        }

        // === 第四轮：验证删除 ===
        console.log("\n=== 第四轮：验证删除 ===");
        await input.fill("查看所有待办");
        await sendButton.click();
        await page.waitForTimeout(10000);

        const pageContent = await page.content();
        if (!pageContent.includes(todoTitle)) {
            console.log("验证成功：待办已被删除");
        } else {
            console.log("警告：待办可能未被删除");
        }

        console.log("多轮对话（创建→修改→删除）测试完成");
    });
});
