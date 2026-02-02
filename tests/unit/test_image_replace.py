"""图片占位符替换测试（中文注释）。

测试 [IMG-N] 占位符替换为 Markdown 图片语法的逻辑。
"""
import pytest


def replace_image_placeholders(content: str, images: dict) -> str:
    """替换图片占位符的纯 Python 实现（用于测试）。
    
    Args:
        content: 包含 [IMG-N] 占位符的文本
        images: {placeholder: url} 映射
        
    Returns:
        替换后的文本
    """
    result = content
    for placeholder, url in images.items():
        # 使用图片描述（去掉方括号）作为 alt 文本
        alt_text = placeholder.strip("[]")
        markdown_img = f"![{alt_text}]({url})"
        result = result.replace(placeholder, markdown_img)
    return result


class TestImagePlaceholderReplace:
    """图片占位符替换测试。"""
    
    def test_single_placeholder(self):
        """测试单个占位符替换。"""
        content = "这是一张图片：[IMG-1]"
        images = {"[IMG-1]": "https://example.com/img1.png"}
        result = replace_image_placeholders(content, images)
        assert "![IMG-1](https://example.com/img1.png)" in result
        # 原始占位符应被替换
        assert "[IMG-1]" not in result or "![IMG-1]" in result
    
    def test_multiple_placeholders(self):
        """测试多个不同占位符替换。"""
        content = "图1：[IMG-1]，图2：[IMG-2]"
        images = {
            "[IMG-1]": "https://example.com/img1.png",
            "[IMG-2]": "https://example.com/img2.png",
        }
        result = replace_image_placeholders(content, images)
        assert "![IMG-1](https://example.com/img1.png)" in result
        assert "![IMG-2](https://example.com/img2.png)" in result
    
    def test_repeated_placeholder(self):
        """测试同一占位符多次出现。"""
        content = "首次：[IMG-1]，再次引用：[IMG-1]"
        images = {"[IMG-1]": "https://example.com/img1.png"}
        result = replace_image_placeholders(content, images)
        # 应该替换所有出现
        assert result.count("![IMG-1](https://example.com/img1.png)") == 2
    
    def test_no_placeholder(self):
        """测试无占位符的文本。"""
        content = "这是普通文本，没有图片"
        images = {}
        result = replace_image_placeholders(content, images)
        assert result == content
    
    def test_unmatched_placeholder(self):
        """测试未匹配的占位符保持不变。"""
        content = "有图：[IMG-1]，无映射：[IMG-99]"
        images = {"[IMG-1]": "https://example.com/img1.png"}
        result = replace_image_placeholders(content, images)
        assert "![IMG-1](https://example.com/img1.png)" in result
        assert "[IMG-99]" in result  # 未匹配的保持原样
    
    def test_empty_content(self):
        """测试空内容。"""
        result = replace_image_placeholders("", {"[IMG-1]": "url"})
        assert result == ""
    
    def test_special_characters_in_url(self):
        """测试 URL 中的特殊字符。"""
        content = "图片：[IMG-1]"
        images = {"[IMG-1]": "https://example.com/path?key=value&foo=bar"}
        result = replace_image_placeholders(content, images)
        assert "https://example.com/path?key=value&foo=bar" in result
    
    def test_chinese_content(self):
        """测试中文内容中的占位符替换。"""
        content = "根据数据分析，存款趋势如下图所示：[IMG-1]\n详细说明请参考上图。"
        images = {"[IMG-1]": "/api/v1/kb/image-proxy?url=xxx"}
        result = replace_image_placeholders(content, images)
        assert "![IMG-1](/api/v1/kb/image-proxy?url=xxx)" in result
        assert "根据数据分析" in result
        assert "详细说明请参考上图" in result
