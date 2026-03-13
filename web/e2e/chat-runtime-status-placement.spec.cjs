const { test, expect } = require('@playwright/test');
const { buildE2EThreadId } = require('./helpers/auth-helper');

function installChatRuntimeMock(page, threadId) {
    return page.addInitScript((targetThreadId) => {
        window.sessionStorage.setItem('auth:token', 'mock-token');

        const originalFetch = window.fetch.bind(window);
        const encoder = new TextEncoder();

        function jsonResponse(payload, init = {}) {
            return new Response(JSON.stringify(payload), {
                status: 200,
                headers: {
                    'Content-Type': 'application/json',
                    ...(init.headers || {}),
                },
                ...init,
            });
        }

        function sseChunk(eventType, payload) {
            return `event: ${eventType}\ndata: ${JSON.stringify(payload)}\n\n`;
        }

        window.fetch = async (input, init = {}) => {
            const url = typeof input === 'string' ? input : input.url;

            if (url.includes('/api/v1/llm/models')) {
                return jsonResponse([
                    {
                        model_code: 'qwen3.5-plus',
                        model_name: 'qwen3.5-plus',
                        model_type: 'chat',
                        provider: 'mock',
                        supports_thinking: false,
                        is_default: true,
                    },
                ]);
            }

            if (url.includes('/api/v1/chat/runs/active')) {
                return jsonResponse({
                    items: [],
                    active_count: 0,
                    poll_hint_seconds: 5,
                    server_time: new Date().toISOString(),
                });
            }

            if (url.includes('/api/v1/chat/threads/latest')) {
                return jsonResponse(null);
            }

            if (/\/api\/v1\/chat\/threads\/[^/]+\/messages/.test(url)) {
                return jsonResponse([]);
            }

            if (/\/api\/v1\/chat\/threads(?:\?|$)/.test(url)) {
                return jsonResponse([]);
            }

            if (url.includes('/api/v1/chat/stream')) {
                const payload = typeof init.body === 'string' ? JSON.parse(init.body) : {};
                const finalText = '这是一个用于测试状态位置的模拟回复。';
                const stream = new ReadableStream({
                    start(controller) {
                        const push = (chunk, delayMs) => {
                            setTimeout(() => {
                                controller.enqueue(encoder.encode(chunk));
                            }, delayMs);
                        };

                        push(sseChunk('init', {
                            thread_id: payload.thread_id || targetThreadId,
                            run_id: 'mock-run-1',
                        }), 0);
                        push(sseChunk('status', {
                            message: '已预装 23 个技能目录，可按需加载。',
                            phase: 'processing',
                        }), 100);
                        push(sseChunk('token', {
                            content: finalText,
                        }), 800);
                        push(sseChunk('final_answer', {
                            content: finalText,
                            meta: { status: 'ok' },
                        }), 1000);
                        push(sseChunk('done', {
                            thread_id: payload.thread_id || targetThreadId,
                            message_id: 1,
                            final_content: finalText,
                            meta: { status: 'completed' },
                        }), 1200);

                        setTimeout(() => {
                            controller.close();
                        }, 1300);
                    },
                });

                return new Response(stream, {
                    status: 200,
                    headers: {
                        'Content-Type': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                    },
                });
            }

            if (url.includes('/api/v1/me')) {
                return jsonResponse({
                    id: 1,
                    username: 'jjk',
                });
            }

            return originalFetch(input, init);
        };
    }, threadId);
}

test.describe('Chat Runtime Status Placement', () => {
    test('runtime status should render with assistant reply instead of footer', async ({ page }) => {
        const threadId = buildE2EThreadId('runtime-status-placement');
        await installChatRuntimeMock(page, threadId);

        await page.goto(`/chat?threadId=${encodeURIComponent(threadId)}`, {
            waitUntil: 'domcontentloaded',
        });

        await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 15000 });

        await page.fill('[data-testid="chat-input"]', '请帮我查询嘉兴近一周的天气并分点总结');
        await page.keyboard.press('Enter');

        await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'streaming', {
            timeout: 15000,
        });

        const runtimeStatus = page.locator('[data-testid="runtime-status"]');
        await expect(runtimeStatus).toBeVisible({ timeout: 15000 });

        const renderedInsideFooter = await runtimeStatus.evaluate((element) => {
            return Boolean(element.closest('footer'));
        });

        expect(renderedInsideFooter).toBe(false);

        await expect(page.locator('[data-testid="chat-input-container"]')).toHaveAttribute('data-chat-state', 'idle', {
            timeout: 15000,
        });
    });
});
