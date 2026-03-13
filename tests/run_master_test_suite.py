"""待办助手全面测试主程序 (Master Test Runner).

此脚本依次运行以下测试套件，并生成汇总报告：
1. `scripts/verify/todo_comprehensive_suite.py` (基础功能 & 健壮性)
2. `scripts/verify/todo_shortcuts.py` (快捷指令)
3. `scripts/verify/todo_complex_flow.py` (复杂流程)

Author: Antigravity
Date: 2026-01-28
"""
import sys
import asyncio
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

async def run_module(module_path: Path):
    """动态加载并运行测试模块的 main 函数"""
    module_name = module_path.stem
    print(f"\n{'='*20} Running {module_name} {'='*20}")
    
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    try:
        if hasattr(module, "main"):
            if asyncio.iscoroutinefunction(module.main):
                return await module.main()
            else:
                return module.main()
        else:
            print(f"❌ Error: {module_name} has no main() function")
            return 1
    except Exception as e:
        print(f"❌ Exception in {module_name}: {e}")
        return 1

async def main():
    print("🚀 Starting Master Test Suite Execution...\n")
    
    results = {}
    
    # 1. Comprehensive Suite
    ret = await run_module(PROJECT_ROOT / "scripts/verify/todo_comprehensive_suite.py")
    results["Comprehensive Suite"] = "✅ PASS" if ret == 0 else "❌ FAIL"
    
    # 2. Shortcut Suite
    ret = await run_module(PROJECT_ROOT / "scripts/verify/todo_shortcuts.py")
    results["Shortcut Suite"] = "✅ PASS" if ret == 0 else "❌ FAIL"
    
    # 3. Complex Flow Suite
    ret = await run_module(PROJECT_ROOT / "scripts/verify/todo_complex_flow.py")
    results["Complex Flow Suite"] = "✅ PASS" if ret == 0 else "❌ FAIL"
    
    print("\n" + "="*50)
    print("📊 Master Test Suite Report")
    print("="*50)
    
    all_passed = True
    for suite, status in results.items():
        print(f"{suite:<25} {status}")
        if "FAIL" in status:
            all_passed = False
            
    print("-" * 50)
    if all_passed:
        print("🎉 ALL SYSTEMS GO! 全面测试通过。")
        return 0
    else:
        print("⚠️ Some tests failed. Please check logs.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
