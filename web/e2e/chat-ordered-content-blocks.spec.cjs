// @ts-check
/**
 * 有序内容块回归测试
 *
 * @test-case TC-CHAT-BLOCK-01 历史 multimodal 消息按“文字 -> 图片 -> 文字”顺序渲染
 */
const { test, expect } = require('@playwright/test');

const THREAD_ID = 'thread-ordered-blocks';
const STREAM_THREAD_ID = 'thread-ordered-blocks-stream';
const KB_IMAGE_ALT = '知识库图片';
const FIRST_TEXT = '第一段说明：先讲结论，再看对应图片。';
const SECOND_TEXT = '第二段说明：图片后继续补充说明。';
const STREAM_USER_PROMPT = '请把图片和说明放在一起';
const STREAM_FINAL_TEXT = '流式第一段 [IMG-0] 流式第二段';
const PNG_BUFFER = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WnXlS4AAAAASUVORK5CYII=',
  'base64',
);
const IMAGE_PATH = '/api/v1/assets/proxy/ragflow/ordered-blocks-image';
const STREAM_IMAGE_PATH = '/api/v1/assets/proxy/ragflow/stream-ordered-blocks-image';

function json(route, data, status = 200) {
  return route.fulfill({
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
    body: JSON.stringify(data),
  });
}

async function setupMockApi(page) {
  const thread = {
    thread_id: THREAD_ID,
    title: '图文混排回归',
    created_at: '2026-03-12T10:00:00Z',
    updated_at: '2026-03-12T10:00:10Z',
  };

  const messagesByThread = {
    [THREAD_ID]: [
      {
        id: 101,
        thread_id: THREAD_ID,
        role: 'human',
        content_type: 'text',
        content: '这张图讲了什么？',
        metadata: {},
        created_at: '2026-03-12T10:00:01Z',
        feedback_score: null,
      },
      {
        id: 102,
        thread_id: THREAD_ID,
        role: 'ai',
        content_type: 'multimodal',
        content: [
          { type: 'markdown', data: { text: FIRST_TEXT } },
          { type: 'image', data: { url: IMAGE_PATH, source: 'knowledge', alt: KB_IMAGE_ALT } },
          { type: 'markdown', data: { text: SECOND_TEXT } },
        ],
        metadata: {},
        created_at: '2026-03-12T10:00:05Z',
        feedback_score: null,
      },
    ],
    [STREAM_THREAD_ID]: [],
  };

  await page.addInitScript(() => {
    window.sessionStorage.setItem('auth:token', 'e2e-mock-token');
  });

  await page.route('**/api/v1/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const { pathname } = url;

    if (req.method() === 'GET' && pathname === '/api/v1/me') {
      return json(route, {
        id: 1,
        username: 'e2e',
        mobile: null,
        data_role: null,
        data_role_label: null,
      });
    }

    if (req.method() === 'GET' && pathname === '/api/v1/llm/models') {
      return json(route, [
        {
          model_code: 'mock-chat',
          model_name: 'Mock Chat',
          model_type: 'chat',
          provider: 'mock',
          supports_thinking: false,
          is_default: true,
        },
      ]);
    }

    if (req.method() === 'GET' && pathname === '/api/v1/chat/threads/latest') {
      return json(route, thread);
    }

    if (req.method() === 'GET' && pathname === '/api/v1/chat/threads') {
      return json(route, [thread]);
    }

    if (req.method() === 'GET' && pathname === '/api/v1/chat/runs/active') {
      return json(route, {
        items: [],
        active_count: 0,
        poll_hint_seconds: 2,
        server_time: '2026-03-12T10:00:06Z',
      });
    }

    const messageMatch = pathname.match(/^\/api\/v1\/chat\/threads\/([^/]+)\/messages$/);
    if (req.method() === 'GET' && messageMatch) {
      const threadId = decodeURIComponent(messageMatch[1]);
      return json(route, messagesByThread[threadId] || []);
    }

    if (req.method() === 'GET' && pathname === IMAGE_PATH) {
      return route.fulfill({
        status: 200,
        headers: { 'content-type': 'image/png' },
        body: PNG_BUFFER,
      });
    }

    if (req.method() === 'GET' && pathname === STREAM_IMAGE_PATH) {
      return route.fulfill({
        status: 200,
        headers: { 'content-type': 'image/png' },
        body: PNG_BUFFER,
      });
    }

    if (req.method() === 'POST' && pathname === '/api/v1/chat/stream') {
      const body = JSON.parse(req.postData() || '{}');
      if (body.thread_id !== STREAM_THREAD_ID || body.prompt !== STREAM_USER_PROMPT) {
        return json(route, { error: 'unexpected stream payload' }, 400);
      }

      const sse = [
        `event: init\ndata: ${JSON.stringify({ thread_id: STREAM_THREAD_ID, run_id: 'run-stream-blocks' })}`,
        `event: token\ndata: ${JSON.stringify({ content: STREAM_FINAL_TEXT })}`,
        `event: kb_images\ndata: ${JSON.stringify({ images: { 0: STREAM_IMAGE_PATH } })}`,
        `event: final_answer\ndata: ${JSON.stringify({ content: STREAM_FINAL_TEXT, meta: { coverage_pass: true } })}`,
        `event: display_blocks\ndata: ${JSON.stringify({
          blocks: [
            { type: 'markdown', data: { text: '流式第一段 ' } },
            { type: 'image', data: { url: STREAM_IMAGE_PATH, source: 'knowledge', alt: KB_IMAGE_ALT } },
            { type: 'markdown', data: { text: ' 流式第二段' } },
          ],
        })}`,
        `event: done\ndata: ${JSON.stringify({ thread_id: STREAM_THREAD_ID, message_id: 9991, final_content: STREAM_FINAL_TEXT })}`,
      ].join('\n\n') + '\n\n';

      return route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream; charset=utf-8',
          'cache-control': 'no-cache',
          connection: 'keep-alive',
        },
        body: sse,
      });
    }

    return json(route, {});
  });
}

test.describe('有序内容块回归', () => {
  test('TC-CHAT-BLOCK-01: 历史 multimodal 消息按文字-图片-文字顺序渲染', async ({ page }) => {
    await setupMockApi(page);

    await page.goto(`/chat?threadId=${encodeURIComponent(THREAD_ID)}`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 15000 });

    const aiMessage = page.locator('[data-testid="ai-message"]').last();
    const firstText = aiMessage.getByText(FIRST_TEXT, { exact: true });
    const image = aiMessage.locator(`img[alt="${KB_IMAGE_ALT}"]`);
    const secondText = aiMessage.getByText(SECOND_TEXT, { exact: true });

    await expect(aiMessage).toBeVisible({ timeout: 15000 });
    await expect(firstText).toBeVisible();
    await expect(image).toBeVisible();
    await expect(secondText).toBeVisible();

    const [firstBox, imageBox, secondBox] = await Promise.all([
      firstText.boundingBox(),
      image.boundingBox(),
      secondText.boundingBox(),
    ]);

    expect(firstBox).not.toBeNull();
    expect(imageBox).not.toBeNull();
    expect(secondBox).not.toBeNull();

    expect(firstBox.y).toBeLessThan(imageBox.y);
    expect(imageBox.y).toBeLessThan(secondBox.y);
  });

  test('TC-CHAT-BLOCK-02: 流式 display_blocks 应覆盖 placeholder 文本并渲染有序块', async ({ page }) => {
    await setupMockApi(page);

    await page.goto(`/chat?threadId=${encodeURIComponent(STREAM_THREAD_ID)}`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible({ timeout: 15000 });

    await page.fill('[data-testid="chat-input"]', STREAM_USER_PROMPT);
    await page.keyboard.press('Enter');

    await expect.poll(async () => {
      return page.locator('[data-testid="chat-input-container"]').getAttribute('data-chat-state');
    }, { timeout: 15000 }).toBe('idle');

    const aiMessage = page.locator('[data-testid="ai-message"]').last();
    const image = aiMessage.locator(`img[alt="${KB_IMAGE_ALT}"]`);
    await expect(aiMessage).not.toContainText('[IMG-0]');
    await expect(image).toBeVisible();
    await expect(aiMessage).toContainText('流式第一段');
    await expect(aiMessage).toContainText('流式第二段');
  });
});
