const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    timeout: 120 * 1000, // 2分钟超时
    use: {
        baseURL: 'http://localhost:3000',
        trace: 'on-first-retry',
        screenshot: 'on',
        video: 'on',
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
        command: 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        timeout: 120 * 1000,
    },
});
