#!/usr/bin/env python3
"""
Claude Code 上下文监控工具

实时估算当前会话的 token 使用情况，避免触发自动压缩。

使用方法：
    python scripts/cc_context_monitor.py

功能：
    - 监控 Claude 会话历史文件
    - 估算当前 token 使用量
    - 显示距离压缩阈值的剩余空间
    - 提供压缩预警
"""

import os
import json
import time
from pathlib import Path
from typing import Optional
import tiktoken


class ContextMonitor:
    """上下文监控器"""

    # Claude Opus 4.6 的上下文限制
    MAX_CONTEXT = 1_000_000
    # 经验值：系统提示词约占用 25K tokens
    SYSTEM_PROMPT_TOKENS = 25_000
    # 压缩触发阈值（约 80%）
    COMPRESSION_THRESHOLD = 800_000
    # 警告阈值（约 60%）
    WARNING_THRESHOLD = 600_000

    def __init__(self):
        # 使用 cl100k_base（GPT-4 tokenizer，与 Claude 接近）
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.claude_dir = Path.home() / ".claude"

    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量"""
        return len(self.encoding.encode(text))

    def find_latest_conversation(self) -> Optional[Path]:
        """查找最新的会话文件"""
        # Claude Code 会话通常存储在 ~/.claude/conversations/
        conv_dir = self.claude_dir / "conversations"
        if not conv_dir.exists():
            return None

        # 查找最新修改的会话文件
        conv_files = list(conv_dir.glob("*.json"))
        if not conv_files:
            return None

        return max(conv_files, key=lambda p: p.stat().st_mtime)

    def analyze_conversation(self, conv_file: Path) -> dict:
        """分析会话文件"""
        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            total_tokens = self.SYSTEM_PROMPT_TOKENS
            message_count = 0

            # 估算消息 token
            if isinstance(data, dict) and 'messages' in data:
                for msg in data['messages']:
                    if isinstance(msg, dict) and 'content' in msg:
                        content = msg['content']
                        if isinstance(content, str):
                            total_tokens += self.estimate_tokens(content)
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and 'text' in item:
                                    total_tokens += self.estimate_tokens(item['text'])
                        message_count += 1

            return {
                'total_tokens': total_tokens,
                'message_count': message_count,
                'usage_percent': (total_tokens / self.MAX_CONTEXT) * 100,
                'remaining_tokens': self.MAX_CONTEXT - total_tokens,
                'status': self._get_status(total_tokens)
            }
        except Exception as e:
            return {'error': str(e)}

    def _get_status(self, tokens: int) -> str:
        """获取状态"""
        if tokens >= self.COMPRESSION_THRESHOLD:
            return '🔴 危险：即将触发压缩'
        elif tokens >= self.WARNING_THRESHOLD:
            return '🟡 警告：上下文较长'
        else:
            return '🟢 安全'

    def format_number(self, num: int) -> str:
        """格式化数字"""
        return f"{num:,}"

    def display_status(self, stats: dict):
        """显示状态"""
        if 'error' in stats:
            print(f"❌ 错误: {stats['error']}")
            return

        print("\n" + "="*60)
        print("📊 Claude Code 上下文使用情况")
        print("="*60)
        print(f"状态: {stats['status']}")
        print(f"消息数: {stats['message_count']} 轮")
        print(f"已用 Token: {self.format_number(stats['total_tokens'])} / {self.format_number(self.MAX_CONTEXT)}")
        print(f"使用率: {stats['usage_percent']:.1f}%")
        print(f"剩余空间: {self.format_number(stats['remaining_tokens'])} tokens")

        # 进度条
        bar_length = 50
        filled = int(bar_length * stats['usage_percent'] / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n[{bar}] {stats['usage_percent']:.1f}%")

        # 建议
        print("\n💡 建议:")
        if stats['total_tokens'] >= self.COMPRESSION_THRESHOLD:
            print("  - ⚠️  立即开启新会话")
            print("  - 保存关键决策到 memory-bank.md")
        elif stats['total_tokens'] >= self.WARNING_THRESHOLD:
            print("  - 考虑在完成当前任务后开启新会话")
            print("  - 避免粘贴大量代码")
        else:
            print("  - 上下文使用正常")

        print("="*60 + "\n")

    def monitor(self, interval: int = 5):
        """持续监控"""
        print("🔍 开始监控 Claude Code 上下文使用情况...")
        print(f"刷新间隔: {interval} 秒")
        print("按 Ctrl+C 退出\n")

        try:
            while True:
                conv_file = self.find_latest_conversation()
                if conv_file:
                    stats = self.analyze_conversation(conv_file)
                    self.display_status(stats)
                else:
                    print("⏳ 未找到活跃会话，等待中...")

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Claude Code 上下文监控工具')
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='刷新间隔（秒），默认 5 秒'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='只检查一次，不持续监控'
    )

    args = parser.parse_args()

    monitor = ContextMonitor()

    if args.once:
        conv_file = monitor.find_latest_conversation()
        if conv_file:
            stats = monitor.analyze_conversation(conv_file)
            monitor.display_status(stats)
        else:
            print("❌ 未找到活跃会话")
    else:
        monitor.monitor(interval=args.interval)


if __name__ == '__main__':
    main()
