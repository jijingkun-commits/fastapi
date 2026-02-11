// @ts-check
/**
 * 待办助手 SSE 协议回归测试
 *
 * @test-case TC-EDGE-08 跨轮不复现历史卡片
 * @test-case TC-EDGE-09 Resume 结构化结果渲染
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
const { test, expect } = require('@playwright/test');
const { loginIfNeeded, waitForChatReady, waitForAIResponse } = require('./helpers/auth-helper');

/**
 * 解析 SSE 文本里的 done 事件 payload 列表
 * @param {string} sseText
 */
function parseDonePayloads(sseText) {
    const normalized = sseText.replace(/\r\n/g, '\n');
    const blocks = normalized.split('\n\n').filter(Boolean);
    const donePayloads = [];

    for (const block of blocks) {
        if (!block.includes('event: done')) continue;
        const dataLine = block.split('\n').find((line) => line.startsWith('data: '));
        if (!dataLine) continue;
        try {
            donePayloads.push(JSON.parse(dataLine.slice(6)));
        } catch {
            // 忽略异常 payload
        }
    }

    return donePayloads;
}

/**
 * 发送消息并抓取本次 /chat/stream SSE 响应
 * @param {import('@playwright/test').Page} page
 * @param {string} message
 * @param {{ timeout?: number, autoConfirm?: boolean }} options
 */
async function sendMessageAndCaptureStream(page, message, options = {}) {
    const timeout = options.timeout ?? 90000;
    const autoConfirm = options.autoConfirm ?? false;

    await waitForChatReady(page, timeout);

    const responsePromise = page.waitForResponse(
        (response) => response.url().includes('/api/v1/chat/stream') && response.request().method() === 'POST',
        { timeout }
    );

    await page.fill('textarea[data-testid="chat-input"]', message);
    await page.keyboard.press('Enter');

    const response = await responsePromise;
    await waitForAIResponse(page, timeout, autoConfirm);

    const sseText = await response.text();
    return {
        sseText,
        donePayloads: parseDonePayloads(sseText),
    };
}

test.describe('待办助手 SSE 协议回归', () => {
    test.use({ storageState: '.auth/user.json' });
    test.describe.configure({ mode: 'serial' });

    test.beforeEach(async ({ page }) => {
        await loginIfNeeded(page);
        await waitForChatReady(page, 60000);

        const newThreadButton = page.getByRole('button', { name: 'New thread' }).first();
        if (await newThreadButton.isVisible().catch(() => false)) {
            await newThreadButton.click();
            await waitForChatReady(page, 30000);
        }
    });

    test('TC-EDGE-08: 跨轮对话不复现历史待办卡片，且 done 不含 additional_kwargs', async ({ page }) => {
        const uniqueId = Date.now().toString().slice(-6);
        const todoTitle = `SSE回归待办${uniqueId}`;

        await sendMessageAndCaptureStream(page, `帮我创建一个待办：${todoTitle}`, {
            timeout: 120000,
            autoConfirm: true,
        });

        await sendMessageAndCaptureStream(page, '查看我的待办列表', {
            timeout: 90000,
            autoConfirm: false,
        });

        const listAiMessage = page.locator('[data-testid="ai-message"]').last();
        await expect(listAiMessage).toContainText('待办清单', { timeout: 30000 });

        const outOfScope = await sendMessageAndCaptureStream(page, '今天上海天气怎么样？', {
            timeout: 90000,
            autoConfirm: false,
        });

        const lastAiMessage = page.locator('[data-testid="ai-message"]').last();
        // 断言重点：最后一条 AI 消息不应回弹上一轮的 todo_list 卡片
        await expect(lastAiMessage).not.toContainText('待办清单');
        await expect(lastAiMessage).not.toContainText(todoTitle);

        expect(outOfScope.donePayloads.length).toBeGreaterThan(0);
        for (const payload of outOfScope.donePayloads) {
            expect(payload).not.toHaveProperty('additional_kwargs');
        }
    });

    test('TC-EDGE-09: resume 流返回 result 时，结构化卡片可渲染', async ({ page }) => {
        const uniqueId = Date.now().toString().slice(-6);
        const threadId = `resume-mock-thread-${uniqueId}`;
        const triggerPrompt = `触发SSE恢复测试-${uniqueId}`;
        const resumeTodoTitle = `ResumeMock待办-${uniqueId}`;

        // 1) mock stream：稳定产出 interrupt，确保出现确认卡片
        await page.route('**/api/v1/chat/stream', async (route) => {
            const request = route.request();
            if (request.method() !== 'POST') {
                await route.continue();
                return;
            }

            const body = request.postData() || '';
            if (!body.includes(triggerPrompt)) {
                await route.continue();
                return;
            }

            const interruptPayload = {
                thread_id: threadId,
                interrupt_id: `interrupt-${uniqueId}`,
                value: {
                    action_requests: [
                        {
                            name: 'create',
                            args: {
                                _display_message: `创建待办：${resumeTodoTitle}`,
                            },
                        },
                    ],
                    review_configs: [
                        {
                            action_name: 'create',
                            allowed_decisions: ['accept', 'reject'],
                        },
                    ],
                    message: '请确认是否执行创建',
                },
            };

            const sse = [
                `event: init\ndata: ${JSON.stringify({ thread_id: threadId })}`,
                `event: interrupt\ndata: ${JSON.stringify(interruptPayload)}`,
            ].join('\n\n') + '\n\n';

            await route.fulfill({
                status: 200,
                headers: {
                    'content-type': 'text/event-stream; charset=utf-8',
                    'cache-control': 'no-cache',
                    connection: 'keep-alive',
                },
                body: sse,
            });

            await page.unroute('**/api/v1/chat/stream');
        });

        await waitForChatReady(page, 60000);
        await page.fill('textarea[data-testid="chat-input"]', triggerPrompt);
        await page.keyboard.press('Enter');

        await page.waitForSelector('[data-testid="chat-input-container"][data-chat-state="waiting-confirm"]', {
            timeout: 90000,
        });
        await expect(page.locator('[data-testid="confirm-button"]')).toBeVisible({ timeout: 10000 });

        // 2) mock resume：返回 result(todo_list) + done
        let resumeCalled = false;
        await page.route('**/api/v1/chat/resume', async (route) => {
            const request = route.request();
            if (request.method() !== 'POST') {
                await route.continue();
                return;
            }

            resumeCalled = true;

            const sse = [
                `event: token\ndata: ${JSON.stringify({ content: '已恢复执行，以下是结构化结果。' })}`,
                `event: result\ndata: ${JSON.stringify({
                    data_type: 'todo_list',
                    data: {
                        todos: [
                            {
                                id: 999001,
                                title: resumeTodoTitle,
                                status: 'todo',
                                priority: 2,
                                progress: 0,
                                description: '用于验证 resume 的 result 渲染',
                            },
                        ],
                    },
                    message: '找到 1 条待办',
                })}`,
                `event: done\ndata: ${JSON.stringify({ thread_id: threadId, message_id: 999001 })}`,
            ].join('\n\n') + '\n\n';

            await route.fulfill({
                status: 200,
                headers: {
                    'content-type': 'text/event-stream; charset=utf-8',
                    'cache-control': 'no-cache',
                    connection: 'keep-alive',
                },
                body: sse,
            });

            await page.unroute('**/api/v1/chat/resume');
        });

        await page.route('**/api/v1/todo*', async (route) => {
            const request = route.request();
            if (request.method() !== 'GET') {
                await route.continue();
                return;
            }

            await route.fulfill({
                status: 200,
                headers: {
                    'content-type': 'application/json; charset=utf-8',
                },
                body: JSON.stringify([
                    {
                        id: 999001,
                        title: resumeTodoTitle,
                        status: 'todo',
                        priority: 2,
                        progress: 0,
                        description: '用于验证 resume 的 result 渲染',
                    },
                ]),
            });

            await page.unroute('**/api/v1/todo*');
        });

        await page.locator('[data-testid="confirm-button"]').click();
        await waitForChatReady(page, 90000);

        expect(resumeCalled).toBeTruthy();

        const resumeAiMessage = page
            .locator('[data-testid="ai-message"]')
            .filter({ hasText: resumeTodoTitle })
            .first();

        await expect(resumeAiMessage).toContainText('待办清单', { timeout: 30000 });
        await expect(resumeAiMessage).toContainText(resumeTodoTitle, { timeout: 30000 });
    });
});
