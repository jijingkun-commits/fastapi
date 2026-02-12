const { defineConfig, devices } = require('@playwright/test');

const HEADED = process.env.HEADED === 'true';
const SLOW_MO = Number.parseInt(process.env.SLOW_MO || '0', 10);
const FRONTEND_PORT = Number.parseInt(
    process.env.PLAYWRIGHT_FRONTEND_PORT || process.env.TEST_FRONTEND_PORT || '3000',
    10,
);
const BACKEND_PORT = Number.parseInt(process.env.TEST_BACKEND_PORT || '8000', 10);
const API_BASE = process.env.E2E_API_BASE || `http://127.0.0.1:${BACKEND_PORT}`;
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${FRONTEND_PORT}`;

module.exports = defineConfig({
    testDir: './e2e',
    testMatch: ['**/*.spec.cjs', '**/*.feature.cjs'],
    fullyParallel: !HEADED,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : HEADED ? 1 : undefined,
    reporter: 'html',
    timeout: 120 * 1000, // 2分钟超时
    use: {
        baseURL: BASE_URL,
        trace: HEADED ? 'on' : 'on-first-retry',
        screenshot: 'on',
        video: 'retain-on-failure',
        headless: !HEADED,
        launchOptions: {
            slowMo: SLOW_MO || (HEADED ? 500 : 0),
        },
    },
    projects: [
        // 认证设置项目 (首先运行)
        {
            name: 'setup',
            testMatch: /auth\.setup\.cjs/,
        },
        // 主测试项目 (使用认证状态)
        {
            name: 'chromium',
            use: {
                ...devices['Desktop Chrome'],
                // 复用认证状态
                storageState: '.auth/user.json',
            },
            dependencies: ['setup'], // 依赖 setup 项目
        },
    ],
    webServer: {
        command: `NEXT_PUBLIC_API_BASE_URL=${API_BASE} npm run dev -- -p ${FRONTEND_PORT}`,
        url: BASE_URL,
        reuseExistingServer: true,
        timeout: 120 * 1000,
    },
});
