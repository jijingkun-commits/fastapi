"""测试 AssetService 的 URL 替换功能。"""
import re

def test_url_pattern():
    """测试正则表达式匹配 minio:// URL。"""
    test_content = """分析结果如下：
![图表](minio://chat-assets/zhangsan/abc123/charts/550e8400.png)
这是一个测试图片 ![图片](minio://chat-assets/user1/thread1/images/12345.jpg)
普通文本不受影响
"""
    
    pattern = r'minio://([a-zA-Z0-9\-]+)/([^\s\)\]"]+)'
    matches = re.findall(pattern, test_content)
    
    print("✅ 正则匹配测试:")
    assert len(matches) == 2, f"期望匹配2个，实际匹配{len(matches)}个"
    
    for bucket, key in matches:
        print(f"  - bucket: {bucket}, key: {key}")
    
    # 验证第一个匹配
    assert matches[0][0] == "chat-assets"
    assert matches[0][1] == "zhangsan/abc123/charts/550e8400.png"
    
    # 验证第二个匹配
    assert matches[1][0] == "chat-assets"
    assert matches[1][1] == "user1/thread1/images/12345.jpg"
    
    print("✅ 所有断言通过!")


def test_import():
    """测试模块导入。"""
    from app.models.chat_asset import ChatAsset, AssetType
    from app.schemas.chat_asset import ChatAssetCreate, ChatAssetOut
    from app.services.asset_service import AssetService, get_asset_service
    
    print("✅ 所有模块导入成功")
    
    # 验证 AssetType 枚举
    assert AssetType.CHART.value == "chart"
    assert AssetType.IMAGE.value == "image"
    assert AssetType.EXPORT.value == "export"
    
    print("✅ AssetType 枚举验证通过")


if __name__ == "__main__":
    test_url_pattern()
    test_import()
    print("\n🎉 所有测试通过!")
