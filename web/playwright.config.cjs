const { defineConfig, devices } = require('@playwright/test');
const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '.env.vk.local') });
dotenv.config({ path: path.resolve(__dirname, '../.env.vk.local') });
dotenv.config({ path: path.resolve(__dirname, '.env.local') });

const HEADED = process.env.HEADED === 'true';
const SLOW_MO = Number.parseInt(process.env.SLOW_MO || '0', 10);
const BROWSER_CHANNEL = process.env.PLAYWRIGHT_BROWSER_CHANNEL || (process.env.CI ? undefined : 'chrome');
const REUSE_EXISTING_SERVER = process.env.PLAYWRIGHT_REUSE_EXISTING_SERVER === 'true';

function requiredEnv(name, fallback) {
    const value = (process.env[name] || fallback || '').trim();
    if (!value) {
        throw new Error(`缺少必需环境变量 ${name}，请先执行 eval "$(bash scripts/vk_ports.sh --export)" 或加载 .env.vk.local`);
    }
    return value;
}

const BASE_URL = requiredEnv('PLAYWRIGHT_BASE_URL', process.env.VK_FRONTEND_BASE_URL);
const API_BASE = requiredEnv('E2E_API_BASE', process.env.VK_BACKEND_BASE_URL);
const FRONTEND_PORT = Number.parseInt(
    process.env.PLAYWRIGHT_FRONTEND_PORT
        || process.env.TEST_FRONTEND_PORT
        || process.env.VK_FRONTEND_PORT
        || new URL(BASE_URL).port,
    10,
);
const BACKEND_PORT = Number.parseInt(
    process.env.TEST_BACKEND_PORT
        || process.env.VK_BACKEND_PORT
        || new URL(API_BASE).port,
    10,
);
const E2E_BROWSER_USE = {
    ...devices['Desktop Chrome'],
    ...(BROWSER_CHANNEL ? { channel: BROWSER_CHANNEL } : {}),
};

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
        {
            name: 'chromium',
            use: E2E_BROWSER_USE,
        },
    ],
    webServer: {
        command: `NEXT_PUBLIC_API_BASE_URL=${API_BASE} npm run dev -- -p ${FRONTEND_PORT}`,
        url: BASE_URL,
        reuseExistingServer: REUSE_EXISTING_SERVER,
        timeout: 120 * 1000,
    },
});
