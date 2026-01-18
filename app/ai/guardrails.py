"""护栏系统模块（中文注释）。

借鉴 OpenAI Agents SDK input_guardrails.py 和 output_guardrails.py。
提供输入验证和输出检查，增强安全性。

使用方式：
    from app.ai.guardrails import guardrail_runner
    
    # 在 preprocess 节点中
    passed, content, reason = await guardrail_runner.validate_input(user_message)
    if not passed:
        logger.warning("输入护栏拦截: %s", reason)
"""
import re
import logging
from typing import Callable, TypeVar, Any, Optional, Tuple
from pydantic import BaseModel
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GuardrailResult(BaseModel):
    """护栏检查结果。"""
    passed: bool
    reason: Optional[str] = None
    transformed_content: Optional[str] = None  # 脱敏后的内容


# ==================== 装饰器模式（借鉴 OpenAI @input_guardrail） ====================

def input_guardrail(func: Callable) -> Callable:
    """输入护栏装饰器。"""
    @wraps(func)
    async def wrapper(content: str, *args, **kwargs) -> GuardrailResult:
        return await func(content, *args, **kwargs)
    wrapper._is_guardrail = True
    wrapper._guardrail_type = "input"
    return wrapper


def output_guardrail(func: Callable) -> Callable:
    """输出护栏装饰器。"""
    @wraps(func)
    async def wrapper(content: str, *args, **kwargs) -> GuardrailResult:
        return await func(content, *args, **kwargs)
    wrapper._is_guardrail = True
    wrapper._guardrail_type = "output"
    return wrapper


# ==================== 输入护栏 ====================

@input_guardrail
async def check_prompt_injection(content: str) -> GuardrailResult:
    """检测 Prompt 注入攻击。
    
    检测常见的注入模式，防止用户通过特殊指令操控 LLM 行为。
    """
    patterns = [
        (r"忽略之前的指令", "中文注入"),
        (r"ignore previous instructions", "英文注入"),
        (r"你现在是", "角色篡改"),
        (r"你的新角色是", "角色篡改"),
        (r"system prompt", "系统提示词探测"),
        (r"</s>", "特殊标记注入"),
        (r"\[INST\]", "指令标记注入"),
        (r"SYSTEM:", "系统标记注入"),
        (r"<<SYS>>", "Llama 系统标记"),
    ]
    
    for pattern, attack_type in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning("检测到 Prompt 注入尝试: type=%s, pattern=%s", attack_type, pattern)
            return GuardrailResult(
                passed=False,
                reason=f"检测到潜在的安全风险 ({attack_type})"
            )
    
    return GuardrailResult(passed=True)


@input_guardrail
async def sanitize_sensitive_data(content: str) -> GuardrailResult:
    """脱敏敏感数据（身份证、手机号、银行卡）。
    
    不阻止用户发送敏感信息，而是对其进行脱敏处理。
    """
    transformed = content
    has_sensitive = False
    
    # 身份证号（18位）
    id_pattern = r'(\d{6})\d{8}(\d{4})'
    if re.search(id_pattern, transformed):
        transformed = re.sub(id_pattern, r'\1********\2', transformed)
        has_sensitive = True
        logger.info("护栏: 身份证号已脱敏")
    
    # 手机号（11位，以1开头，第二位3-9）
    phone_pattern = r'(1[3-9]\d)\d{4}(\d{4})'
    if re.search(phone_pattern, transformed):
        transformed = re.sub(phone_pattern, r'\1****\2', transformed)
        has_sensitive = True
        logger.info("护栏: 手机号已脱敏")
    
    # 银行卡号（16-19位）
    card_pattern = r'(\d{4})\d{8,12}(\d{4})'
    if re.search(card_pattern, transformed):
        transformed = re.sub(card_pattern, r'\1****\2', transformed)
        has_sensitive = True
        logger.info("护栏: 银行卡号已脱敏")
    
    return GuardrailResult(
        passed=True,
        transformed_content=transformed if has_sensitive else None
    )


@input_guardrail
async def check_content_length(content: str) -> GuardrailResult:
    """检查内容长度，防止过长输入。"""
    MAX_LENGTH = 50000  # 约 50KB
    
    if len(content) > MAX_LENGTH:
        logger.warning("护栏: 输入过长 (%d > %d)", len(content), MAX_LENGTH)
        return GuardrailResult(
            passed=False,
            reason=f"输入内容过长，请精简后重试（最大 {MAX_LENGTH} 字符）"
        )
    
    return GuardrailResult(passed=True)


# ==================== 输出护栏 ====================

@output_guardrail
async def check_sensitive_output(content: str) -> GuardrailResult:
    """检测输出中的敏感信息泄露。"""
    patterns = [
        (r"API_KEY\s*[=:]\s*\S+", "API 密钥"),
        (r"SECRET\s*[=:]\s*\S+", "密钥"),
        (r"password\s*[=:]\s*\S+", "密码"),
        (r"我的系统提示是", "系统提示词泄露"),
        (r"my system prompt", "系统提示词泄露"),
        (r"\d{17}[\dXx]", "身份证号"),
    ]
    
    for pattern, leak_type in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning("护栏: 检测到输出敏感信息泄露 - %s", leak_type)
            return GuardrailResult(
                passed=False,
                reason=f"输出包含敏感信息 ({leak_type})"
            )
    
    return GuardrailResult(passed=True)


@output_guardrail
async def check_harmful_content(content: str) -> GuardrailResult:
    """检测有害内容（基础版）。"""
    # 这是一个基础检测，生产环境建议使用专业的内容安全 API
    harmful_patterns = [
        r"如何制造炸弹",
        r"如何制作毒品",
        r"自杀方法",
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning("护栏: 检测到有害内容")
            return GuardrailResult(
                passed=False,
                reason="内容违反安全策略"
            )
    
    return GuardrailResult(passed=True)


# ==================== 护栏执行器 ====================

class GuardrailRunner:
    """护栏执行器。
    
    统一管理和执行所有护栏规则。
    """
    
    def __init__(self):
        self.input_guardrails = [
            check_content_length,
            check_prompt_injection,
            sanitize_sensitive_data,
        ]
        self.output_guardrails = [
            check_sensitive_output,
            check_harmful_content,
        ]
    
    async def validate_input(self, content: str) -> Tuple[bool, str, Optional[str]]:
        """执行所有输入护栏。
        
        Args:
            content: 用户输入内容
            
        Returns:
            (是否通过, 处理后的内容, 拦截原因)
        """
        current = content
        
        for guardrail in self.input_guardrails:
            try:
                result = await guardrail(current)
                
                if not result.passed:
                    return False, current, result.reason
                
                if result.transformed_content:
                    current = result.transformed_content
                    
            except Exception as e:
                logger.error("护栏执行异常: %s - %s", guardrail.__name__, e)
                # 护栏执行失败时，默认放行但记录日志
                continue
        
        return True, current, None
    
    async def validate_output(self, content: str) -> Tuple[bool, str, Optional[str]]:
        """执行所有输出护栏。
        
        Args:
            content: LLM 输出内容
            
        Returns:
            (是否通过, 处理后的内容, 拦截原因)
        """
        for guardrail in self.output_guardrails:
            try:
                result = await guardrail(content)
                
                if not result.passed:
                    return False, "[内容已被安全策略过滤]", result.reason
                    
            except Exception as e:
                logger.error("输出护栏执行异常: %s - %s", guardrail.__name__, e)
                continue
        
        return True, content, None
    
    def add_input_guardrail(self, guardrail: Callable):
        """添加自定义输入护栏。"""
        if hasattr(guardrail, '_is_guardrail'):
            self.input_guardrails.append(guardrail)
        else:
            raise ValueError("护栏函数必须使用 @input_guardrail 装饰器")
    
    def add_output_guardrail(self, guardrail: Callable):
        """添加自定义输出护栏。"""
        if hasattr(guardrail, '_is_guardrail'):
            self.output_guardrails.append(guardrail)
        else:
            raise ValueError("护栏函数必须使用 @output_guardrail 装饰器")


# 全局护栏执行器实例
guardrail_runner = GuardrailRunner()
