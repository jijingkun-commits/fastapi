import unittest
from datetime import datetime, timedelta
from app.services.time_parser import NaturalTimeParser

class TestNaturalTimeParser(unittest.TestCase):
    def setUp(self):
        # 固定基准时间为 2024-01-10 (周三)
        self.base_time = datetime(2024, 1, 10, 9, 0, 0)
        self.parser = NaturalTimeParser(base_time=self.base_time)

    def test_parse_simple_date(self):
        # 明天 -> 2024-01-11
        text = "明天"
        parsed, _ = self.parser.parse(text)
        self.assertEqual(parsed.date(), (self.base_time + timedelta(days=1)).date())

    def test_parse_next_week_tuesday(self):
        # 下周二 -> 2024-01-16 (周三+6天)
        # 1月10日是周三
        # 本周日是 1月14日
        # 下周二是 1月16日
        text = "下周二"
        parsed, _ = self.parser.parse(text)
        self.assertEqual(parsed.year, 2024)
        self.assertEqual(parsed.month, 1)
        self.assertEqual(parsed.day, 16)

    def test_parse_this_week_deadline(self):
        # 这周内 -> 往往会被映射为 this Friday 或 Sunday
        # 我们在预处理中映射为 this Friday
        text = "这周内"
        parsed, _ = self.parser.parse(text)
        # 1月10日(周三) 的 this Friday 是 1月12日
        self.assertEqual(parsed.date(), datetime(2024, 1, 12).date())

    def test_extract_constraints(self):
        text = "下周二之前完成，但这周一全天开会不可用"
        parsed, meta = self.parser.parse(text)
        # 应该解析出下周二
        self.assertEqual(parsed.day, 16)
        
        # 应该提取出周一不可用
        # "这周一" -> 周一 (weekday=1)
        constraints = meta.get("constraints")
        self.assertIn("blocked_weekdays", constraints)
        self.assertIn(1, constraints["blocked_weekdays"])

    def test_fuzzy_time_adjustment(self):
        # 明天下午 -> 明天 14:00
        text = "明天下午"
        parsed, _ = self.parser.parse(text)
        self.assertEqual(parsed.hour, 14)

    def test_before_end_of_work_day(self):
        text = "明天下班前"
        parsed, _ = self.parser.parse(text)
        self.assertEqual(parsed.hour, 18)

if __name__ == "__main__":
    unittest.main()
