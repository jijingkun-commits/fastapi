const { test, expect } = require('@playwright/test');

const E2E_MOCK_TOKEN = 'e2e-admin-overview-token';

/**
 * 管理后台总览驾驶舱主流程覆盖。
 *
 * @test-case TC-ADMIN-OV-01 精简驾驶舱渲染与轮询降级
 * @test-case TC-ADMIN-OV-02 告警/模块跳转路由正确性
 * @see docs/开发文档/测试管理/管理后台测试案例.md
 */
test.describe('用户故事: 管理后台总览驾驶舱', () => {
    test('US-ADMIN-OV-01: 渲染驾驶舱并在 SSE 中断后降级到轮询', async ({ page }) => {
        test.setTimeout(90_000);

        let summaryRequestCount = 0;

        const buildSummaryPayload = (snapshotAt, degraded = false) => ({
            snapshot_at: snapshotAt,
            source: degraded ? 'empty' : 'bucket',
            degraded,
            request_quality: {
                status: degraded ? 'degraded' : 'ok',
                health_level: degraded ? 'unknown' : 'healthy',
                score: degraded ? null : 92.6,
                request_total: degraded ? 0 : 1380,
                success_rate: degraded ? null : 0.9924,
                error_5xx_rate: degraded ? null : 0.0038,
                latency_p95_ms: degraded ? null : 612,
                qps: degraded ? null : 39.6,
                explain: degraded ? '请求质量暂不可判定。' : '全业务 API 请求质量正常。',
            },
            question_health: {
                status: degraded ? 'degraded' : 'ok',
                health_level: degraded ? 'unknown' : 'healthy',
                score: degraded ? null : 89.6,
                question_total: degraded ? 0 : 72,
                question_success_rate: degraded ? null : 0.985,
                question_latency_p95_ms: degraded ? null : 648,
                question_qps: degraded ? null : 2.1,
                explain: degraded ? '提问链路暂不可判定。' : '提问链路健康。',
            },
            alerts: [
                {
                    code: 'llm.rate_limit',
                    severity: 'warning',
                    message: 'LLM 模块出现限流告警，请评估并发配置。',
                    module: 'llm',
                    status: 'active',
                },
            ],
            freshness: {
                status: degraded ? 'unknown' : 'fresh',
                score: degraded ? null : 94,
                health_level: degraded ? 'unknown' : 'healthy',
                delay_sec: degraded ? null : 28,
                expired: degraded,
                max_delay_sec: 300,
                source: degraded ? 'empty' : 'bucket',
            },
            module_matrix: [
                {
                    key: 'user',
                    label: '用户管理',
                    health_level: 'healthy',
                    score: 88.2,
                    error_rate: 0.0012,
                    latency_p95_ms: 433,
                    data_delay_sec: 21,
                },
                {
                    key: 'llm',
                    label: '模型配置',
                    health_level: 'warning',
                    score: 74.9,
                    error_rate: 0.008,
                    latency_p95_ms: 905,
                    data_delay_sec: 47,
                },
            ],
            meta: {
                generated_at: snapshotAt,
                trace_id: `trace-${summaryRequestCount}`,
            },
        });

        await test.step('Given: 管理员已登录且总览接口被模拟', async () => {
            await page.route('**/api/v1/admin-overview/summary', async (route) => {
                summaryRequestCount += 1;

                const degraded = summaryRequestCount > 1;
                const payload = buildSummaryPayload(
                    degraded ? '2026-02-14T08:00:12Z' : '2026-02-14T08:00:00Z',
                    degraded,
                );

                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(payload),
                });
            });

            await page.route('**/api/v1/admin-overview/trends**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        windows: {
                            '1h': [
                                {
                                    timestamp: '2026-02-14T07:50:00Z',
                                    request_qps: 31.2,
                                    question_qps: 1.8,
                                },
                                {
                                    timestamp: '2026-02-14T08:00:00Z',
                                    request_qps: 39.6,
                                    question_qps: 2.1,
                                },
                            ],
                            '24h': [
                                {
                                    timestamp: '2026-02-13T09:00:00Z',
                                    request_qps: 25.4,
                                    question_qps: 1.1,
                                },
                                {
                                    timestamp: '2026-02-14T08:00:00Z',
                                    request_qps: 39.6,
                                    question_qps: 2.1,
                                },
                            ],
                        },
                    }),
                });
            });

            await page.route('**/api/v1/admin-overview/stream', async (route) => {
                const streamBody = [
                    'event: result',
                    `data: ${JSON.stringify({
                        snapshot_at: '2026-02-14T08:00:06Z',
                        patch: {
                            freshness: {
                                delay_sec: 66,
                                status: 'fresh',
                                expired: false,
                            },
                        },
                    })}`,
                    '',
                    'event: interrupt',
                    `data: ${JSON.stringify({
                        reason: 'stream_disconnected',
                        level: 'warning',
                        message: '流连接中断，降级轮询生效。',
                        retry_after_sec: 10,
                    })}`,
                    '',
                ].join('\n');

                await route.fulfill({
                    status: 200,
                    headers: {
                        'content-type': 'text/event-stream; charset=utf-8',
                        'cache-control': 'no-cache',
                    },
                    body: streamBody,
                });
            });

        });

        await test.step('Given/When: 管理员进入 /admin 总览页', async () => {
            await page.addInitScript((token) => {
                window.sessionStorage.setItem('auth:token', token);
            }, E2E_MOCK_TOKEN);
            await page.goto('/admin', { waitUntil: 'domcontentloaded' });
        });

        await test.step('Then: 首屏可见精简后的 6 个主展示块', async () => {
            const cards = [
                'overview-card-request-quality',
                'overview-card-alerts',
                'overview-card-freshness',
                'overview-card-module-matrix',
                'overview-card-question-health',
                'overview-card-traffic-trends',
            ];

            for (const cardId of cards) {
                await expect(page.getByTestId(cardId)).toBeVisible();
            }
        });

        await test.step('Then: SSE 中断后 10 秒内进入轮询并显示状态提示', async () => {
            await expect(page.getByTestId('admin-overview-realtime-status')).toContainText('轮询');
            await expect.poll(() => summaryRequestCount, { timeout: 12_000 }).toBeGreaterThan(1);
        });

        await test.step('Then: 异常告警与模块矩阵可跳转到正确路由', async () => {
            await page.getByTestId('overview-alert-link-0').click();
            await expect(page).toHaveURL(/\/admin\/llm(?:\?.*)?$/);

            await page.goBack();
            await expect(page).toHaveURL(/\/admin(?:\?.*)?$/);

            await page.getByTestId('overview-module-link-user').click();
            await expect(page).toHaveURL(/\/admin\/users(?:\?.*)?$/);
        });
    });
});
