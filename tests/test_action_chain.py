import json
from pathlib import Path
import tempfile
import unittest

from action_chain import audit, record_send


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class FakeRobot:
    def send_action(self, requested):
        return {"base.vx": min(requested["base.vx"], 0.5), "base.wz": requested["base.wz"]}


class ActionChainTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads((FIXTURES / "rules.json").read_text())
        self.rows = [json.loads(line) for line in (FIXTURES / "actions.jsonl").read_text().splitlines()]

    def test_clipped_action_is_visible_but_passes_tracking(self):
        for locale in ("fr", "en", "es"):
            report = audit(self.rows, self.rules, locale)
            self.assertEqual(report["status"], "pass")
            self.assertIn("modified", [item["code"] for item in report["findings"]])

    def test_missing_measurement_is_inconclusive(self):
        self.rows[0]["observed"] = None
        self.rows[0]["observed_at_ms"] = None
        self.assertEqual(audit(self.rows, self.rules)["status"], "inconclusive")

    def test_missing_sent_value_is_inconclusive(self):
        self.rows[0]["sent"] = None
        self.assertEqual(audit(self.rows, self.rules)["status"], "inconclusive")

    def test_tracking_error_fails(self):
        self.rows[0]["observed"]["base.vx"] = 0.2
        self.assertEqual(audit(self.rows, self.rules)["status"], "fail")

    def test_wrapper_records_returned_action(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.jsonl"
            times = iter((1000, 1008, 1020))
            sent = record_send(FakeRobot(), {"base.vx": 2.0, "base.wz": 0.0}, path, episode="demo", step=0, units={"base.vx": "m/s", "base.wz": "rad/s"}, observe=lambda: {"base.vx": 0.48, "base.wz": 0.01}, clock=lambda: next(times))
            self.assertEqual(sent["base.vx"], 0.5)
            self.assertEqual(audit([json.loads(path.read_text())], self.rules)["status"], "pass")

    def test_units_mismatch_is_invalid(self):
        self.rows[0]["units"]["base.vx"] = "rad/s"
        with self.assertRaises(ValueError):
            audit(self.rows, self.rules)


if __name__ == "__main__":
    unittest.main()
