/**
 * 用户管理模块 E2E 测试
 * 
 * @test-case TC-USER-01 用户列表查看
 * @test-case TC-USER-02 用户创建
 * @test-case TC-USER-03 用户禁用/启用
 * @see docs/开发文档/测试管理/用户管理测试案例.md
 */

const { test, expect } = require('@playwright/test');

// 测试配置
const ADMIN_USERNAME = 'jjk';  // 登录用账号（jjk 拥有管理员权限）
const TEST_USER_PREFIX = 'e2e_test_';

// Sonner toast 选择器辅助函数
const toastLocator = (page, text) => {
    // Sonner toast 使用 li[data-sonner-toast] 包含文本
    return page.locator('li[data-sonner-toast]', { hasText: text });
};

// 登录辅助函数
async function loginAsAdmin(page) {
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');
    
    // 如果已经登录（不在 auth 页面），直接返回
    if (!page.url().includes('/auth')) {
        return;
    }
    
    await page.fill('#identifier', ADMIN_USERNAME);
    await page.click('button[type="submit"]');
    
    // 等待登录成功 - 离开 /auth 页面
    await page.waitForFunction(() => !window.location.pathname.includes('/auth'), { timeout: 15000 });
}

test.describe('用户管理模块', () => {
    // 每个测试前先登录管理员账号
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
    });

    test.describe('TC-USER-01: 用户列表', () => {
        test('应该正确显示用户列表页面', async ({ page }) => {
            await page.goto('/admin/users');
            
            // 验证页面标题
            await expect(page.getByText('用户管理')).toBeVisible();
            await expect(page.getByText('管理系统用户账户')).toBeVisible();
            
            // 验证表格列头
            await expect(page.getByRole('columnheader', { name: 'ID' })).toBeVisible();
            await expect(page.getByRole('columnheader', { name: '用户名' })).toBeVisible();
            await expect(page.getByRole('columnheader', { name: '角色' })).toBeVisible();
            await expect(page.getByRole('columnheader', { name: '状态' })).toBeVisible();
        });

        test('应该支持搜索功能', async ({ page }) => {
            await page.goto('/admin/users');
            
            // 输入搜索关键词
            await page.fill('input[placeholder*="搜索"]', 'admin');
            await page.click('button:has-text("搜索")');
            
            // 验证搜索结果包含 admin 用户
            await expect(page.getByRole('cell', { name: 'admin' })).toBeVisible();
        });

        test('创建用户按钮应该可见', async ({ page }) => {
            await page.goto('/admin/users');
            await expect(page.getByRole('button', { name: /创建用户/ })).toBeVisible();
        });
    });

    test.describe('TC-USER-02: 用户创建', () => {
        test('应该打开创建用户对话框', async ({ page }) => {
            await page.goto('/admin/users');
            
            // 点击创建用户按钮
            await page.click('button:has-text("创建用户")');
            
            // 验证对话框显示
            await expect(page.getByRole('dialog')).toBeVisible();
            await expect(page.getByText('填写用户信息以创建新账户')).toBeVisible();
            
            // 验证表单字段
            await expect(page.getByLabel('用户名 *')).toBeVisible();
            await expect(page.getByLabel('密码 *')).toBeVisible();
            await expect(page.getByLabel('手机号')).toBeVisible();
            await expect(page.getByLabel('角色')).toBeVisible();
        });

        test('创建用户时应该验证必填字段', async ({ page }) => {
            await page.goto('/admin/users');
            await page.click('button:has-text("创建用户")');
            await page.waitForSelector('[role="dialog"]', { state: 'visible' });
            
            // 不填写任何字段直接点击创建
            await page.click('button:has-text("创建"):not(:has-text("创建用户"))');
            
            // 验证方式：对话框仍然打开（因为验证失败不会关闭）
            await page.waitForTimeout(500);
            await expect(page.getByRole('dialog')).toBeVisible();
            
            // 验证用户名输入框仍为空且可见（说明表单未提交）
            await expect(page.locator('#username')).toHaveValue('');
        });

        test('应该成功创建新用户', async ({ page }) => {
            await page.goto('/admin/users');
            await page.click('button:has-text("创建用户")');
            await page.waitForSelector('[role="dialog"]', { state: 'visible' });
            
            // 生成唯一用户名和手机号
            const timestamp = Date.now();
            const testUsername = `${TEST_USER_PREFIX}${timestamp}`;
            // 使用时间戳生成唯一手机号（138 + 后8位）
            const testMobile = `138${String(timestamp).slice(-8)}`;
            
            // 填写表单
            await page.fill('#username', testUsername);
            await page.fill('#password', 'Test@123456');
            await page.fill('#mobile', testMobile);
            
            // 点击创建
            await page.click('button:has-text("创建"):not(:has-text("创建用户"))');
            
            // 验证对话框关闭（成功标志）
            await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 10000 });
            
            // 验证用户出现在列表中
            await expect(page.getByRole('cell', { name: testUsername })).toBeVisible({ timeout: 5000 });
        });

        test('应该拒绝重复用户名', async ({ page }) => {
            await page.goto('/admin/users');
            await page.click('button:has-text("创建用户")');
            await page.waitForSelector('[role="dialog"]', { state: 'visible' });
            
            // 使用已存在的用户名
            await page.fill('#username', 'admin');
            await page.fill('#password', 'Test@123456');
            
            await page.click('button:has-text("创建"):not(:has-text("创建用户"))');
            
            // 验证方式：对话框在一段时间后仍然打开（创建失败不会关闭）
            await page.waitForTimeout(2000);
            await expect(page.getByRole('dialog')).toBeVisible();
            
            // 额外验证：用户名输入框仍有值（表单未被清空）
            await expect(page.locator('#username')).toHaveValue('admin');
        });
    });

    test.describe('TC-USER-03: 用户禁用/启用', () => {
        test('应该显示状态确认对话框', async ({ page }) => {
            await page.goto('/admin/users');
            
            // 找到一个非 admin 用户的状态开关并点击
            // 查找状态为"启用"且不是 admin 的行
            const userRow = page.locator('tr:has(td:text("普通用户"))').first();
            const switchButton = userRow.locator('button[role="switch"]');
            
            if (await switchButton.isVisible()) {
                await switchButton.click();
                
                // 验证确认对话框显示
                await expect(page.getByRole('alertdialog')).toBeVisible();
                await expect(page.getByText(/确定要.*用户/)).toBeVisible();
            }
        });

        test('管理员不能禁用自己', async ({ page }) => {
            await page.goto('/admin/users');
            
            // 找到 admin 用户行
            const adminRow = page.locator('tr:has(td:text("admin"))');
            const switchButton = adminRow.locator('button[role="switch"]');
            
            if (await switchButton.isVisible()) {
                // 检查开关是否被禁用或点击后是否有错误提示
                const isDisabled = await switchButton.isDisabled();
                
                if (!isDisabled) {
                    await switchButton.click();
                    // 应该提示不能禁用自己
                    await expect(page.getByText(/不能禁用自己|无法禁用当前/)).toBeVisible({ timeout: 5000 });
                }
            }
        });
    });
});

test.describe('权限验证', () => {
    test('未登录用户访问用户管理页应跳转登录', async ({ browser }) => {
        // 使用新的浏览器上下文（无登录状态）
        const context = await browser.newContext();
        const page = await context.newPage();
        
        await page.goto('/admin/users');
        
        // 应该跳转到登录页或显示未授权提示
        await expect(page).toHaveURL(/auth|login/);
        
        await context.close();
    });
});
