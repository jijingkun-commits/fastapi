const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { loginAndOpenThread, ensureChatReady, waitForAIResponse } = require('./helpers/auth-helper');

const PNG_BUFFER = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WnXlS4AAAAASUVORK5CYII=',
    'base64',
);
const TEXT_BUFFER = Buffer.from('hello attachment', 'utf8');
const DOCX_BUFFER = fs.readFileSync(path.join(__dirname, 'fixtures', 'sample.docx'));
const PDF_BUFFER = fs.readFileSync(path.join(__dirname, 'fixtures', 'sample.pdf'));
const XLSX_BUFFER = fs.readFileSync(path.join(__dirname, 'fixtures', 'sample.xlsx'));
const toastLocator = (page, text) => page.locator('li[data-sonner-toast]', { hasText: text });

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

async function previewAndPersistFileAttachment(page, testInfo, { file, message }) {
    const threadId = await loginAndOpenThread(page, `${testInfo.title}-${file.name}`);
    await ensureChatReady(page);

    const requestPromise = page.waitForRequest((request) => request.url().includes('/api/v1/chat/stream') && request.method() === 'POST');
    await page.locator('#file-input').setInputFiles(file);

    const inputContainer = page.locator('[data-testid="chat-input-container"]');
    await expect(inputContainer.getByText(file.name)).toBeVisible({ timeout: 10000 });
    await expect(inputContainer.getByText('不支持的文件类型')).toHaveCount(0);

    await page.fill('[data-testid="chat-input"]', message);
    await page.keyboard.press('Enter');

    const streamRequest = await requestPromise;
    const streamPayload = JSON.parse(streamRequest.postData() || '{}');
    expect(streamPayload.attachments?.length).toBe(1);
    expect(streamPayload.attachments?.[0]?.name).toBe(file.name);
    await waitForAIResponse(page, 90000, true);

    await page.goto(`/chat?threadId=${encodeURIComponent(threadId)}`, { waitUntil: 'domcontentloaded' });
    await ensureChatReady(page);

    const humanMessage = page.locator('[data-testid="human-message"]').last();
    const persistedLink = humanMessage.locator('a').last();
    await expect(persistedLink).toBeVisible({ timeout: 15000 });
    await expect(persistedLink).toHaveAttribute('href', /\/api\/v1\/assets\//);
    await expect(persistedLink).toHaveText(file.name);
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

    test('should preview and persist uploaded docx after refresh', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        await previewAndPersistFileAttachment(page, testInfo, {
            file: {
                name: 'e2e-sample.docx',
                mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                buffer: DOCX_BUFFER,
            },
            message: '请记录这个 docx 附件',
        });
    });

    test('should preview and persist uploaded pdf after refresh', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        await previewAndPersistFileAttachment(page, testInfo, {
            file: {
                name: 'e2e-sample.pdf',
                mimeType: 'application/pdf',
                buffer: PDF_BUFFER,
            },
            message: '请记录这个 pdf 附件',
        });
    });

    test('should preview and persist uploaded xlsx after refresh', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        await previewAndPersistFileAttachment(page, testInfo, {
            file: {
                name: 'e2e-sample.xlsx',
                mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                buffer: XLSX_BUFFER,
            },
            message: '请记录这个 excel 附件',
        });
    });

    test('should show convert hint for legacy doc upload', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        await loginAndOpenThread(page, `${testInfo.title}-legacy-doc`);
        await ensureChatReady(page);

        await page.locator('#file-input').setInputFiles({
            name: 'legacy-upload.doc',
            mimeType: 'application/msword',
            buffer: Buffer.from('legacy doc binary', 'utf8'),
        });

        await expect(toastLocator(page, '请先转换为 .docx')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('[data-testid="chat-input-container"]').getByText('legacy-upload.doc')).toHaveCount(0);
    });
});
