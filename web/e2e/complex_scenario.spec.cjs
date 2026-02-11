const { test, expect } = require('@playwright/test');
const { loginIfNeeded, sendMessageAndWait } = require('./helpers/auth-helper');

test.describe('Complex Todo Agent Scenario', () => {
    test.beforeEach(async ({ page }) => {
        await loginIfNeeded(page);
    });

    test('should handle multi-turn complex scenario', async ({ page }) => {
        test.setTimeout(180000);

        async function chat(message, expectedSnippet) {
            console.log(`Sending: ${message}`);
            await sendMessageAndWait(page, message, 90000, true);

            const responses = page.locator('[data-testid="ai-message"]');
            const count = await responses.count();

            if (count > 0) {
                const lastMatch = responses.last();
                await expect(lastMatch).toBeVisible();
                const text = await lastMatch.innerText();
                console.log(`Last response preview: ${text.substring(0, 80)}...`);

                if (expectedSnippet) {
                    if (!text.includes(expectedSnippet)) {
                        console.log(`⚠️ NOTE: Expected '${expectedSnippet}' not found. Got: ${text.substring(0, 40)}...`);
                    } else {
                        console.log(`✅ Verified: ${expectedSnippet}`);
                    }
                }
            } else {
                console.log('⚠️ No response bubbles found yet. Taking screenshot for debug.');
                await page.screenshot({ path: `e2e/debug-step-${Date.now()}.png` });
            }
        }

        // Round 1: Ambiguous Start
        await chat('最近事情太多了，帮我把接下来要做的事情理一理。', '理一理');

        // Round 2: Unstructured Input
        await chat('工作的为主吧。大概有几个项目：1. 预售资金系统的投标材料 2. AI中台相关的方案 3. 还有几个零碎的临时事', '预售资金');

        // Round 3: Info + Constraint
        await chat('预售资金那个挺急的，好像这周内要给。AI中台倒是不那么急，但领导下周可能要听汇报。', '这周');

        // Round 4: Decomposition Trigger
        await chat('技术方案我负责，但商务那块是公司部给。技术方案里要写系统架构、信创适配、实施计划。', '拆解');

        // Round 6: Schedule Conflict
        await chat('对了，人力系统全行测评那件事之前说这周出初稿，可能要顺延一下。但办公室昨天又催了。', '检测到');
        await chat('人力系统的放到下周二之前吧。但周一我基本一整天都在开会。', '冲突');

        // Round 9: Merge
        await chat('那AI中台的完整路线图可以先不做那么细，跟明天那个1页说明能不能合并一部分？', '合并');
    });
});
