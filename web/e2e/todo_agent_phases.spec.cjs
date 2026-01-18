/**
 * 复杂多轮对话场景 E2E 测试
 * 
 * 测试 To-Do Agent 的增强能力:
 * - Phase 1: 自然语言时间解析
 * - Phase 2: 深度冲突检测
 * - Phase 3: 动态优先级重排
 * - Phase 4: 隐含需求推理
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:3000';

// 辅助函数: 发送消息并等待回复
async function sendMessage(page, message) {
    const input = page.locator('[data-testid="chat-input"], textarea[placeholder*="输入"]');
    await input.fill(message);
    await input.press('Enter');

    // 等待 AI 回复
    await page.waitForSelector('[data-testid="ai-message"]', { timeout: 30000 });
    await page.waitForTimeout(2000); // 等待流式输出完成
}

// 辅助函数: 获取最新的 AI 回复内容
async function getLatestAIMessage(page) {
    const messages = await page.locator('[data-testid="ai-message"]').all();
    if (messages.length === 0) return '';

    return await messages[messages.length - 1].textContent();
}

test.describe('Todo Agent 多轮对话测试', () => {

    test.beforeEach(async ({ page }) => {
        // 确保登录状态
        await page.goto(`${BASE_URL}/chat`);
        await page.waitForLoadState('networkidle');
    });

    test('Phase 1: 时间解析 - 下周二', async ({ page }) => {
        await sendMessage(page, '帮我创建一个任务,下周二之前完成');

        const response = await getLatestAIMessage(page);

        // 验证时间被解析 (应该显示具体日期而非"下周二")
        // 注意: 实际日期取决于测试运行时间
        expect(response).not.toContain('下周二');
        // 应该包含待办信息展示
        expect(response).toContain('待办信息');
    });

    test('Phase 2: 冲突检测 - 工作量超载', async ({ page }) => {
        // 先创建多个同一天的任务
        await sendMessage(page, '帮我在周五创建5个任务: 任务1, 任务2, 任务3, 任务4, 任务5');

        const response = await getLatestAIMessage(page);

        // 应该检测到工作量冲突
        // 5个任务 * 2小时 = 10小时 > 8小时
        const hasConflictWarning =
            response.includes('过载') ||
            response.includes('冲突') ||
            response.includes('时间紧张');

        expect(hasConflictWarning).toBe(true);
    });

    test('Phase 3: 紧急任务识别', async ({ page }) => {
        await sendMessage(page, '刚刚领导说明天要一个项目进度报告');

        const response = await getLatestAIMessage(page);

        // 应该识别为紧急任务
        const isUrgentRecognized =
            response.includes('紧急') ||
            response.includes('🚨') ||
            response.includes('高优先级') ||
            response.includes('🔴');

        expect(isUrgentRecognized).toBe(true);
    });

    test('Phase 4: 隐含需求推理 - 汇报准备', async ({ page }) => {
        await sendMessage(page, '领导下周要听项目汇报');

        const response = await getLatestAIMessage(page);

        // 应该主动询问准备材料
        const hasImpliedQuestion =
            response.includes('PPT') ||
            response.includes('材料') ||
            response.includes('准备') ||
            response.includes('需要');

        expect(hasImpliedQuestion).toBe(true);
    });

    test('Phase 1B: 时间约束提取 - 周一不可用', async ({ page }) => {
        await sendMessage(page, '帮我在下周二前完成报告,但周一我全天开会');

        const response = await getLatestAIMessage(page);

        // 应该识别到约束或在后续冲突检测中使用
        // 至少应该确认任务信息
        expect(response).toContain('待办信息');
    });

});

test.describe('端到端完整流程', () => {

    test('完整多轮对话模拟', async ({ page }) => {
        await page.goto(`${BASE_URL}/chat`);
        await page.waitForLoadState('networkidle');

        // Round 1: 模糊起始
        await sendMessage(page, '帮我理一理最近的事');
        let response = await getLatestAIMessage(page);
        expect(response.length).toBeGreaterThan(0);

        // Round 2: 补充项目信息
        await sendMessage(page, '主要是AI中台和人力系统两个项目的事');
        response = await getLatestAIMessage(page);
        expect(response.length).toBeGreaterThan(0);

        // Round 3: 添加时间
        await sendMessage(page, '预售资金这周内要给银行');
        response = await getLatestAIMessage(page);
        // 应该包含待办确认
        expect(response).toContain('待办');

        console.log('✅ E2E 多轮对话测试完成');
    });

});

// 🆕 新增测试 - 覆盖原测试案例的 Round 4/9/10
test.describe('复杂场景测试 - Round 4/9/10', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto(`${BASE_URL}/chat`);
        await page.waitForLoadState('networkidle');
    });

    test('Round 4: 任务拆解 - 复合任务识别', async ({ page }) => {
        await sendMessage(page, '技术方案里要写系统架构、信创适配、实施计划');

        const response = await getLatestAIMessage(page);

        // 应该识别为复合任务并尝试拆解或询问详情
        const hasDecomposition =
            response.includes('子任务') ||
            response.includes('拆解') ||
            response.includes('系统架构') ||
            response.includes('信创');

        expect(hasDecomposition).toBe(true);
    });

    test('Round 9: 任务合并 - 合并请求识别', async ({ page }) => {
        await sendMessage(page, '路线图跟说明能不能合并一下?');

        const response = await getLatestAIMessage(page);

        // 应该识别合并意图
        const hasMergeRecognition =
            response.includes('合并') ||
            response.includes('结合') ||
            response.includes('整合');

        expect(hasMergeRecognition).toBe(true);
    });

    test('Round 10: 结构化输出 - 待办清单生成', async ({ page }) => {
        // 先创建一些待办
        await sendMessage(page, '帮我创建一个高优先级任务: 准备项目汇报');
        await page.waitForTimeout(2000);

        // 请求清单
        await sendMessage(page, '按优先级给我待办清单');

        const response = await getLatestAIMessage(page);

        // 应该返回结构化的待办清单
        const hasStructuredOutput =
            response.includes('高优先级') ||
            response.includes('🔴') ||
            response.includes('清单') ||
            response.includes('待办');

        expect(hasStructuredOutput).toBe(true);
    });

    test('多项目识别 - 逐项目追问', async ({ page }) => {
        await sendMessage(page, '有几个项目要做: 预售资金系统、AI中台、人力系统评测');

        const response = await getLatestAIMessage(page);

        // 应该识别到多个项目并开始逐项追问
        const hasMultiProjectHandling =
            response.includes('预售资金') ||
            response.includes('AI中台') ||
            response.includes('项目') ||
            response.includes('待讨论');

        expect(hasMultiProjectHandling).toBe(true);
    });

});
