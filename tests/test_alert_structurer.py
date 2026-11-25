"""Contract tests for Tool A."""

import importlib.util
import json
import unittest
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "chat_agent"
    / "tools"
    / "alert_structurer.py"
)
_SPEC = importlib.util.spec_from_file_location("alert_structurer", _MODULE_PATH)
alert_structurer = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(alert_structurer)
format_alert_info = alert_structurer.format_alert_info


class AlertStructurerTest(unittest.TestCase):
    def test_object_success_contract(self):
        result = json.loads(
            format_alert_info(
                {
                    "title": "CPU 高",
                    "severity": "HIGH",
                    "service": "payment-api",
                    "extra": "ignored",
                }
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["severity"], "high")
        self.assertEqual(result["data"]["affected_service"], "payment-api")
        self.assertEqual(
            set(result["data"]),
            {
                "alert_id",
                "title",
                "severity",
                "status",
                "source",
                "affected_service",
                "event_time",
                "description",
                "raw_text",
                "confidence",
                "notes",
            },
        )
        self.assertGreaterEqual(result["data"]["confidence"], 0)
        self.assertLessEqual(result["data"]["confidence"], 1)
        self.assertIn("输入中存在未纳入通用契约的字段：extra", result["data"]["notes"])
        self.assertIn("affected_service 通过别名 service 映射", result["data"]["notes"])

    def test_json_string_and_invalid_json_downgrades_to_free_text(self):
        parsed = json.loads(
            format_alert_info('{"alert_id":"A-1","severity":"critical"}')
        )
        self.assertTrue(parsed["success"])
        self.assertEqual(parsed["data"]["alert_id"], "A-1")
        self.assertEqual(parsed["data"]["severity"], "critical")

        free = json.loads(format_alert_info("告警等级：严重；影响服务：payment-api"))
        self.assertTrue(free["success"])
        self.assertEqual(free["data"]["severity"], "critical")
        self.assertEqual(free["data"]["affected_service"], "payment-api")

    def test_missing_values_are_not_invented(self):
        result = json.loads(format_alert_info("CPU 使用率超过阈值"))["data"]
        self.assertIsNone(result["alert_id"])
        self.assertIsNone(result["severity"])
        self.assertIsNone(result["status"])
        self.assertEqual(result["raw_text"], "CPU 使用率超过阈值")
        self.assertIsInstance(result["confidence"], (int, float))
        self.assertTrue(result["notes"])

    def test_unrecognized_enum_is_null_with_note(self):
        result = json.loads(format_alert_info({"severity": "storm", "status": "gone"}))
        self.assertTrue(result["success"])
        self.assertIsNone(result["data"]["severity"])
        self.assertIsNone(result["data"]["status"])
        self.assertIn(
            "severity 值无法映射到约定枚举，已置为 null：storm",
            result["data"]["notes"],
        )

    def test_structured_errors(self):
        empty = json.loads(format_alert_info(""))
        unsupported = json.loads(format_alert_info(123))
        multiple = json.loads(format_alert_info([{"title": "a"}, {"title": "b"}]))

        self.assertFalse(empty["success"])
        self.assertEqual(empty["error_code"], "EMPTY_INPUT")
        self.assertFalse(unsupported["success"])
        self.assertEqual(unsupported["error_code"], "UNSUPPORTED_INPUT")
        self.assertFalse(multiple["success"])
        self.assertEqual(multiple["error_code"], "MULTIPLE_ALERTS")


if __name__ == "__main__":
    unittest.main()
