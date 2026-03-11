const { test, expect } = require('@playwright/test');
const { loginAndOpenThread, ensureChatReady, waitForAIResponse } = require('./helpers/auth-helper');

const PNG_BUFFER = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WnXlS4AAAAASUVORK5CYII=',
    'base64',
);
const TEXT_BUFFER = Buffer.from('hello attachment', 'utf8');

async function sendAttachmentMessage(page, { file, message }) {
    const requestPromise = page.waitForRequest((request) => request.url().includes('/api/v1/chat/stream') && request.method() === 'POST');
    await page.locator('#file-input').setInputFiles(file);
    await page.fill('[data-testid="chat-input"]', message);
    await page.keyboard.press('Enter');
    const streamRequest = await requestPromise;
    const streamPayload = JSON.parse(streamRequest.postData() || '{}');
    expect(streamPayload.attachments?.length).toBe(1);
    expect(streamPayload.attachments?.[0]?.name).toBe(file.name);
    await waitForAIResponse(page, 90000, true);
}

test.describe('Chat Attachment History', () => {
    test('should keep uploaded image visible after refresh', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        const threadId = await loginAndOpenThread(page, testInfo.title);
        await ensureChatReady(page);

        await expect(page.locator('[data-testid="chat-input-container"]')).toBeVisible({ timeout: 10000 });
        await sendAttachmentMessage(page, {
            file: {
                name: 'e2e-attachment.png',
                mimeType: 'image/png',
                buffer: PNG_BUFFER,
            },
            message: '请看这张图',
        });

        await page.goto(`/chat?threadId=${encodeURIComponent(threadId)}`, { waitUntil: 'domcontentloaded' });
        await ensureChatReady(page);

        const humanMessage = page.locator('[data-testid="human-message"]').last();
        const persistedImage = humanMessage.locator('img').last();
        await expect(persistedImage).toBeVisible({ timeout: 15000 });
        await expect(persistedImage).toHaveAttribute('src', /\/api\/v1\/assets\//);
        await expect(persistedImage).toHaveAttribute('alt', 'e2e-attachment.png');
    });

    test('should keep uploaded file link visible after refresh', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        const threadId = await loginAndOpenThread(page, `${testInfo.title}-file`);
        await ensureChatReady(page);

        await sendAttachmentMessage(page, {
            file: {
                name: 'e2e-note.txt',
                mimeType: 'text/plain',
                buffer: TEXT_BUFFER,
            },
            message: '请处理这个文件',
        });

        await page.goto(`/chat?threadId=${encodeURIComponent(threadId)}`, { waitUntil: 'domcontentloaded' });
        await ensureChatReady(page);

        const humanMessage = page.locator('[data-testid="human-message"]').last();
        const persistedLink = humanMessage.locator('a').last();
        await expect(persistedLink).toBeVisible({ timeout: 15000 });
        await expect(persistedLink).toHaveAttribute('href', /\/api\/v1\/assets\//);
        await expect(persistedLink).toHaveText('e2e-note.txt');
    });
});
