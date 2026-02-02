const { test } = require('@playwright/test');

/**
 * 需求文档: docs/内部参考/需求文档/问数引擎需求.md
 * 测试用例: docs/开发文档/测试管理/问数引擎测试案例.md
 * @test-case TC-AD-01
 * @test-case TC-AD-02
 * @test-case TC-AD-03
 *
 * 当前问数引擎以 API/脚本验证为主，E2E UI 入口待补充。
 */
test.describe('用户故事: 问数引擎', () => {
    test.skip('US-AD-01~03: 当前使用后端脚本验证', async () => {
        // 参考: tests/test_ask_data_flow.py
    });
});
