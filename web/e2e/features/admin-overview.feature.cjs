const { test, expect } = require('@playwright/test');
const { loginIfNeeded } = require('../helpers/auth-helper');

/**
 * 管理后台总览驾驶舱主流程覆盖。
 *
 * @test-case TC-ADMIN-OV-01 实时 8 块驾驶舱渲染与轮询降级
 * @test-case TC-ADMIN-OV-02 告警/模块跳转路由正确性
 * @see docs/开发文档/测试管理/管理后台测试案例.md
 */
test.describe('用户故事: 管理后台总览驾驶舱', () => {
    test('US-ADMIN-OV-01: 渲染驾驶舱并在 SSE 中断后降级到轮询', async ({ page }) => {
        test.setTimeout(90_000);

        let summaryRequestCount = 0;

        const buildSummaryPayload = (snapshotAt, degraded = false) => ({
            snapshot_at: snapshotAt,
            source: degraded ? 'fallback_snapshot' : 'live',
            degraded,
            health_score: degraded ? 86.2 : 90.4,
            health_level: degraded ? 'warning' : 'healthy',
            budget_usage_pct: 62.1,
            request_quality: {
                status: 'healthy',
                score: 92.6,
                request_total: 1380,
                success_rate: 0.9924,
                error_5xx_rate: 0.0038,
                latency_p95_ms: 612,
            },
            stability: {
                status: 'warning',
                score: 78.8,
                critical_alerts: 1,
                warning_alerts: 2,
                module_score: 81.2,
            },
            capacity_cost: {
                status: 'healthy',
                score: 87.9,
                qps: degraded ? 34.2 : 39.6,
                cost_per_minute: 15.5,
                budget_per_minute: 25,
                budget_usage_pct: 62.1,
                budget_health_level: 'healthy',
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
                status: degraded ? 'expired' : 'fresh',
                score: degraded ? 60 : 94,
                health_level: degraded ? 'warning' : 'healthy',
                delay_sec: degraded ? 132 : 28,
                expired: degraded,
                max_delay_sec: 300,
                source: degraded ? 'polling' : 'live',
            },
            module_matrix: [
                {
                    key: 'users',
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
            change_feed: [
                {
                    id: 'chg-1',
                    title: '模型路由切换至 qwen-max，增加对公问询稳定性',
                    level: 'warning',
                    occurred_at: '2026-02-14T08:00:00Z',
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
                                    health_score: 88.1,
                                    qps: 31.2,
                                },
                                {
                                    timestamp: '2026-02-14T08:00:00Z',
                                    health_score: 90.4,
                                    qps: 39.6,
                                },
                            ],
                            '24h': [
                                {
                                    timestamp: '2026-02-13T09:00:00Z',
                                    qps: 25.4,
                                    health_score: 81.2,
                                },
                                {
                                    timestamp: '2026-02-14T08:00:00Z',
                                    qps: 39.6,
                                    health_score: 90.4,
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
                            health_score: 89.4,
                            health_level: 'warning',
                            freshness: {
                                delay_sec: 66,
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

            await loginIfNeeded(page);
        });

        await test.step('When: 进入 /admin 总览页', async () => {
            await page.goto('/admin');
            await page.waitForLoadState('domcontentloaded');
        });

        await test.step('Then: 首屏可见 8 块驾驶舱信息卡', async () => {
            const cards = [
                'overview-card-health',
                'overview-card-request-quality',
                'overview-card-stability',
                'overview-card-capacity-cost',
                'overview-card-alerts',
                'overview-card-freshness',
                'overview-card-module-matrix',
                'overview-card-change-feed',
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

            await page.getByTestId('overview-module-link-users').click();
            await expect(page).toHaveURL(/\/admin\/users(?:\?.*)?$/);
        });
    });
});
