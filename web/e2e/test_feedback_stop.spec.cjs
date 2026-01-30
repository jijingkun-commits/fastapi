const { test, expect } = require('@playwright/test');

test.describe('Chat Feedback and Stop', () => {
    test('should stop generation', async ({ page }) => {
        await page.goto('/');

        // Enter a long prompt that takes time to generate
        const prompt = '写一篇关于人工智能发展的长文，至少500字';
        await page.fill('textarea', prompt);

        // Click send
        const sendButton = page.locator('button[type="submit"]');
        await sendButton.click();

        // Wait for generation to start (stop button appears)
        // Stop button usually replaces send button or appears in input area with loading spinner
        // Checking for the square stop icon or button with Loading state
        // In the code, it's a button with LoaderCircle when loading
        const stopButton = page.locator('button:has(.animate-spin)');
        await expect(stopButton).toBeVisible({ timeout: 5000 });

        // Click stop
        await stopButton.click();

        // Verify stop button reverts to send button
        await expect(page.locator('button[type="submit"]')).toBeVisible();
        await expect(page.locator('.lucide-arrow-up')).toBeVisible(); // ArrowUp icon
    });

    test('should allow like and dislike', async ({ page }) => {
        await page.goto('/');

        // Send a simple message
        await page.fill('textarea', '你好');
        await page.locator('button[type="submit"]').click();

        // Wait for AI response (markdown-text)
        await expect(page.locator('.markdown-text')).toBeVisible({ timeout: 10000 });

        // Hover over the message to show action bar
        // We find the last AI message container
        const aiMessage = page.locator('[data-testid="ai-message"]').last();
        await aiMessage.hover();

        // Click Like (ThumbsUp)
        const likeButton = aiMessage.locator('button[aria-label="Good response"]');
        await expect(likeButton).toBeVisible();
        await likeButton.click();

        // Verify visual feedback (class change or similar, here we assume checking active state)
        // In shared.tsx: className={score === 1 ? "text-green-600 bg-green-50" : ""}
        await expect(likeButton).toHaveClass(/text-green-600/);

        // Click Dislike (ThumbsDown) - should toggle
        const dislikeButton = aiMessage.locator('button[aria-label="Bad response"]');
        await dislikeButton.click();

        // Verify Dislike is active and Like is inactive
        await expect(dislikeButton).toHaveClass(/text-red-600/);
        await expect(likeButton).not.toHaveClass(/text-green-600/);
    });
});
