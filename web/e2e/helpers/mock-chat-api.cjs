const { seedAuthToken } = require('./auth-helper');

function json(route, data, status = 200) {
  return route.fulfill({
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
    body: JSON.stringify(data),
  });
}

async function setupMockChatApi(page, options = {}) {
  const threadA = options.threadA ?? {
    thread_id: 'thread-A',
    title: '历史会话A',
    created_at: '2026-03-07T00:00:00Z',
    updated_at: '2026-03-07T00:10:00Z',
  };

  const threadB = options.threadB ?? {
    thread_id: 'thread-B',
    title: '历史会话B',
    created_at: '2026-03-07T00:20:00Z',
    updated_at: '2026-03-07T00:30:00Z',
  };

  const threads = options.threads ?? [threadA, threadB];
  const latestThread = options.latestThread ?? threads[0] ?? null;
  const messagesByThread = options.messagesByThread ?? {
    [threadA.thread_id]: [
      {
        id: 101,
        thread_id: threadA.thread_id,
        role: 'human',
        content: '会话A-问题',
        created_at: '2026-03-07T00:01:00Z',
      },
      {
        id: 102,
        thread_id: threadA.thread_id,
        role: 'ai',
        content: '会话A-回答',
        created_at: '2026-03-07T00:01:10Z',
      },
    ],
    [threadB.thread_id]: [
      {
        id: 201,
        thread_id: threadB.thread_id,
        role: 'human',
        content: '会话B-问题',
        created_at: '2026-03-07T00:21:00Z',
      },
      {
        id: 202,
        thread_id: threadB.thread_id,
        role: 'ai',
        content: '会话B-回答',
        created_at: '2026-03-07T00:21:10Z',
      },
    ],
  };

  await seedAuthToken(page, 'e2e-mock-token');

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
      return json(route, latestThread);
    }

    if (req.method() === 'GET' && pathname === '/api/v1/chat/threads') {
      return json(route, threads);
    }

    const messageMatch = pathname.match(/^\/api\/v1\/chat\/threads\/([^/]+)\/messages$/);
    if (req.method() === 'GET' && messageMatch) {
      const tid = decodeURIComponent(messageMatch[1]);
      return json(route, messagesByThread[tid] || []);
    }

    return json(route, {});
  });
}

async function installMockChatStream(page, options = {}) {
  const events = options.events ?? [];
  const pathFragment = options.pathFragment ?? '/api/v1/chat/stream';

  await page.addInitScript(
    ({ pathFragment: targetPath, events: configuredEvents }) => {
      const originalFetch = window.fetch.bind(window);

      window.fetch = async (input, init) => {
        const url = typeof input === 'string'
          ? input
          : input && typeof input.url === 'string'
            ? input.url
            : '';

        if (!url.includes(targetPath)) {
          return originalFetch(input, init);
        }

        const encoder = new TextEncoder();
        const normalizedEvents = Array.isArray(configuredEvents) ? configuredEvents : [];
        const maxDelay = normalizedEvents.reduce(
          (currentMax, item) => Math.max(currentMax, Number(item.delayMs || 0)),
          0,
        );

        const stream = new ReadableStream({
          start(controller) {
            normalizedEvents.forEach((item) => {
              const payload = `event: ${item.event}\ndata: ${JSON.stringify(item.data)}\n\n`;
              const delayMs = Number(item.delayMs || 0);
              setTimeout(() => {
                controller.enqueue(encoder.encode(payload));
              }, delayMs);
            });

            setTimeout(() => {
              controller.close();
            }, maxDelay + 120);
          },
        });

        return new Response(stream, {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
        });
      };
    },
    { pathFragment, events },
  );
}

module.exports = {
  setupMockChatApi,
  installMockChatStream,
};
