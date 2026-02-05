"""自然语言时间解析服务 (Regex版)。

由于 dateparser 在处理特定相对日期时表现不稳定，
本模块使用正则表达式和 datetime 计算实现核心的高频时间解析需求。
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

class NaturalTimeParser:
    """中文自然语言时间解析器 (规则引擎版)"""
    
    def __init__(self, base_time: datetime = None):
        self.base_time = base_time or datetime.now()
        # 将 base_time 归一化为当天的 00:00，避免时间偏移影响日期计算
        self.base_date = self.base_time.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def parse(self, text: str) -> Tuple[Optional[datetime], Dict]:
        """解析时间表达式。
        
        支持的格式：
        - 相对日期：今天、明天、后天
        - 星期：周一、下周二、本周三
        - 周期：这周内、下周内
        - 具体时间点：9点、10点30分、下午3点半、早上8点
        - 时间段：早上、上午、下午、晚上、下班前
        """
        if not text:
            return None, {}

        parsed_time = None
        constraints = self._extract_constraints(text)
        
        # 1. 相对日期解析 (明天、后天)
        if "明天" in text:
            parsed_time = self.base_date + timedelta(days=1)
        elif "后天" in text:
            parsed_time = self.base_date + timedelta(days=2)
        elif "今天" in text:
            parsed_time = self.base_date
            
        # 2. 星期解析 (周X、下周X)
        if not parsed_time:
            parsed_time = self._parse_weekday(text)
            
        # 3. 泛指周期解析 (这周内、下周内)
        if not parsed_time:
            parsed_time = self._parse_period(text)

        # 4. 提取具体时间点 (如 "9点"、"10点30分"、"3点半")
        # 此步骤必须在设置默认时间之前
        specific_time = self._parse_specific_time(text)
        
        # 5. 如果只有时间点没有日期，默认使用今天
        if specific_time and not parsed_time:
            parsed_time = self.base_date
        
        # 6. 时间微调 (上午/下午/下班前/早上)
        # 默认时间设为 9:00 (如果只是日期)
        if parsed_time:
            if specific_time:
                # 有具体时间点，直接使用
                hour, minute = specific_time
                parsed_time = parsed_time.replace(hour=hour, minute=minute)
            else:
                # 没有具体时间点，使用默认值 9:00
                if parsed_time.hour == 0 and parsed_time.minute == 0:
                    parsed_time = parsed_time.replace(hour=9)
                # 根据时间段调整
                parsed_time = self._adjust_time_of_day(parsed_time, text)

        return parsed_time, {
            "original_text": text,
            "is_fuzzy": self._is_fuzzy_time(text),
            "constraints": constraints
        }
    
    def _parse_weekday(self, text: str) -> Optional[datetime]:
        """解析 周X / 下周X / 本周X"""
        # 匹配模式: (下|本|这)?(周|星期)([一二三四五六日])
        match = re.search(r'(下|本|这)?(周|星期)([一二三四五六日])', text)
        if not match:
            return None
            
        prefix = match.group(1) # 下 / 本 / 这 / None
        weekday_char = match.group(3) # 一 ~ 日
        
        day_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6}
        target_weekday = day_map[weekday_char]
        
        current_weekday = self.base_date.weekday() # 0=Monday
        
        delta_days = 0
        if prefix == "下":
            # 下周X = (7 - current + target)
            delta_days = 7 - current_weekday + target_weekday
        else:
            # 本周X / 周X (默认为本周，如果今天已经过了该周几，逻辑上通常指下周？或者保持本周？)
            # 策略：如果 "周一" 且今天是 "周三"，通常指 "下周一"，但也可能指 "本周一" (回顾)
            # 这里采用 'future' 策略：如果目标日 <= 今天，则算作下周 (除非明确说了"本")
            # 但简单起见，且由测试用例 "下周二" 驱动，先按本周算，
            # 如果是"下周二" 已经由 prefix=="下" 处理了。
            
            # 假设 "周X" 默认指未来最近的一个 X ? 
            # dateparser 'PREFER_DATES_FROM': 'future' 的行为
            
            # 这里简化逻辑：
            # 1. 算出本周该日
            delta_days = target_weekday - current_weekday
            
            # 2. 如果加上前缀 "本/这"，就锁定在本周
            if prefix in ["本", "这"]:
                pass 
            # 3. 如果没前缀，且目标日已过去 (delta < 0)，则+7天 (下周)
            elif delta_days < 0:
                delta_days += 7
                
        return self.base_date + timedelta(days=delta_days)

    def _parse_period(self, text: str) -> Optional[datetime]:
        """解析 这周内 / 下周内"""
        # 策略：默认截止到周五
        current_weekday = self.base_date.weekday()
        
        if "下周" in text:
            # 下周五
            # days_to_next_monday = 7 - current_weekday
            # next_friday = days_to_next_monday + 4
            delta = (7 - current_weekday) + 4
            return self.base_date + timedelta(days=delta)
            
        if "这周" in text or "本周" in text:
            # 本周五
            delta = 4 - current_weekday
            # 如果今天是周六(5)或周日(6)，本周五已过去，是否要变下周五？
            # 暂时保持返回过去的时间或当天，由业务层判断 overdue
            return self.base_date + timedelta(days=delta)
            
        return None

    def _parse_specific_time(self, text: str) -> Optional[Tuple[int, int]]:
        """提取具体时间点，如 "9点"、"10点30分"、"3点半"、"早上8点"。
        
        Returns:
            (hour, minute) 元组，如果没有匹配则返回 None
        """
        # 匹配模式：
        # - (早上|上午|中午|下午|晚上)? - 可选的时间段前缀
        # - (\d{1,2}) - 小时数
        # - [点:：时] - 分隔符
        # - (?:(\d{1,2})[分]?|半)? - 可选的分钟数或"半"
        pattern = r'(早上|凌晨|上午|中午|下午|傍晚|晚上)?(\d{1,2})[点:：时](?:(\d{1,2})[分]?|(半))?'
        match = re.search(pattern, text)
        
        if not match:
            return None
        
        period = match.group(1)  # 时间段前缀
        hour = int(match.group(2))  # 小时
        minute_str = match.group(3)  # 分钟数字
        is_half = match.group(4)  # "半"
        
        # 计算分钟
        if is_half:
            minute = 30
        elif minute_str:
            minute = int(minute_str)
        else:
            minute = 0
        
        # 根据时间段前缀调整小时（12小时制转24小时制）
        if period in ["下午", "傍晚", "晚上"] and hour < 12:
            hour += 12
        elif period == "中午" and hour == 12:
            pass  # 中午12点保持不变
        elif period in ["凌晨"] and hour == 12:
            hour = 0  # 凌晨12点 = 0点
        elif period in ["早上", "上午", "凌晨"]:
            # 早上/上午时间保持不变（1-12点）
            if hour == 12:
                hour = 0  # 上午12点 = 0点（凌晨）
        elif period is None and hour <= 6:
            # 没有时间段前缀且小时数很小时，可能指的是下午
            # 例如 "3点开会" 通常指下午3点
            # 但这个规则比较模糊，暂时保守处理，不自动转换
            pass
        
        # 验证时间范围
        if hour > 23:
            hour = 23
        if minute > 59:
            minute = 59
        
        return (hour, minute)

    def _adjust_time_of_day(self, dt: datetime, text: str) -> datetime:
        """根据 早上/上午/下午/晚上/下班前 调整时间。
        
        注意：此方法仅在没有具体时间点时调用，用于设置默认时间。
        """
        if "下班前" in text:
            return dt.replace(hour=18, minute=0)
        if "晚上" in text:
            return dt.replace(hour=20, minute=0)
        if "下午" in text or "傍晚" in text:
            # 如果当前是默认的9点，改为14点
            if dt.hour == 9: 
                return dt.replace(hour=14, minute=0)
        if "中午" in text:
            # 中午默认12点
            if dt.hour == 9:
                return dt.replace(hour=12, minute=0)
        if "上午" in text or "早上" in text:
            # 早上/上午保持9点
            if dt.hour == 9:
                pass
        if "凌晨" in text:
            # 凌晨默认6点
            if dt.hour == 9:
                return dt.replace(hour=6, minute=0)
        
        return dt

    def _extract_constraints(self, text: str) -> Dict:
        """提取时间约束"""
        constraints = {}
        # 匹配 "周X...不可用/开会"
        # 使用 finditer 查找所有可能的约束
        # 中间的间隔符不能包含 "周" 或 "星期"，防止跨越匹配 (e.g. "周一 (周五不可用)")
        pattern = r'(周[一二三四五六日]|星期[一二三四五六日])([^周星期]{0,10}?)(不可用|开会|忙)'
        
        matches = re.finditer(pattern, text)
        day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}
        
        blocked_weekdays = []
        for match in matches:
            # match.group(1) 是 "周X"
            # 获取 X
            day_char = match.group(1)[-1] 
            if day_char in day_map:
                weekday = day_map[day_char]
                if weekday not in blocked_weekdays:
                     blocked_weekdays.append(weekday)
        
        if blocked_weekdays:
            constraints["blocked_weekdays"] = blocked_weekdays
            
        return constraints

    def _is_fuzzy_time(self, text: str) -> bool:
        """判断时间表达是否模糊。"""
        keywords = ["下午", "上午", "晚上", "早上", "凌晨", "可能", "大概", "左右"]
        return any(k in text for k in keywords)
