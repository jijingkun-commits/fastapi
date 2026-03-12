const { test, expect } = require('@playwright/test');

/**
 * 测试用例: docs/开发文档/测试管理/管理后台测试案例.md
 * @test-case TC-ADMIN-EXAM-01
 * @test-case TC-ADMIN-EXAM-03
 */
test.describe('用户故事: AI 出题后台', () => {
    test('US-ADMIN-EXAM-01: 展示题量提示、历史记录并触发直接下载', async ({ page }) => {
        test.setTimeout(90_000);

        await test.step('Given: 管理后台 API 被 mock，且会话内已存在 token', async () => {
            await page.addInitScript(() => {
                window.sessionStorage.setItem('auth:token', 'e2e-mock-token');
            });

            await page.route('**/api/v1/exam-admin/template', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        template: {
                            paper_title: '默认试卷',
                            single_choice_count: 5,
                            multiple_choice_count: 3,
                            judge_count: 3,
                            short_answer_count: 2,
                            difficulty_distribution: { easy: 0.4, medium: 0.4, hard: 0.2 },
                            score_strategy: { single_choice: 2, multiple_choice: 3, judge: 1, short_answer: 10 },
                            answer_section_enabled: true,
                            answer_page_break: true,
                            answer_explanation_mode: 'short',
                        },
                        available_datasets: [
                            { dataset_id: 'kb-a', label: '知识库 A' },
                            { dataset_id: 'kb-b', label: '知识库 B' },
                        ],
                        limits: {
                            max_total_questions: 100,
                            max_active_jobs_per_user: 3,
                        },
                    }),
                });
            });

            await page.route('**/api/v1/exam-admin/jobs?limit=50', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([
                        {
                            id: 7,
                            user_id: 1,
                            title: '历史试卷 A',
                            status: 'succeeded',
                            dataset_ids: ['kb-a', 'kb-b'],
                            asset_id: 99,
                            minio_object_key: '1/exam-job-7/exports/demo.pdf',
                            download_url: '/api/v1/exam-admin/jobs/7/download',
                            error_message: null,
                            created_at: '2026-03-11T00:00:00Z',
                            updated_at: '2026-03-11T00:00:00Z',
                            started_at: '2026-03-11T00:00:01Z',
                            finished_at: '2026-03-11T00:00:02Z',
                        },
                    ]),
                });
            });

            await page.route('**/api/v1/exam-admin/jobs/7/download', async (route) => {
                await route.fulfill({
                    status: 200,
                    headers: {
                        'content-type': 'application/pdf',
                        'content-disposition': 'attachment; filename="exam-job-7.pdf"',
                    },
                    body: '%PDF-1.4\nmock',
                });
            });
        });

        await test.step('When: 打开 AI 出题后台页面', async () => {
            await page.goto('/admin/exam-generation', { waitUntil: 'domcontentloaded' });
        });

        await test.step('Then: 页面显示题量上限、历史记录和下载按钮', async () => {
            await expect(page.getByRole('heading', { name: 'AI 出题' })).toBeVisible({ timeout: 15000 });
            await expect(page.getByText('题量上限 100')).toBeVisible();
            await expect(page.getByText('并发上限 3')).toBeVisible();
            await expect(page.getByText('历史试卷 A')).toBeVisible();
            await expect(page.getByText('知识库 A')).toBeVisible();
            await expect(page.getByRole('button', { name: '下载', exact: true })).toBeVisible();
        });

        await test.step('Then: 点击下载会直接命中导出接口', async () => {
            const downloadRequest = page.waitForRequest('**/api/v1/exam-admin/jobs/7/download');
            await page.getByRole('button', { name: '下载', exact: true }).click();
            await downloadRequest;
        });
    });
});
