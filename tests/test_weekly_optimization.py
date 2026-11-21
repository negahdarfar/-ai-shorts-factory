import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from weekly_optimization import as_number, records, total, main
from build_factory_dashboard import main as build_dashboard


class WeeklyOptimizationTests(unittest.TestCase):
    def test_numeric_conversion_is_safe(self):
        self.assertEqual(as_number("12.5"), 12.5)
        self.assertEqual(as_number(None), 0.0)
        self.assertEqual(as_number("bad"), 0.0)

    def test_records_and_total(self):
        report = {
            "columnHeaders": [{"name": "views"}, {"name": "engagedViews"}],
            "rows": [[100, 60], [200, 120]],
        }
        parsed = records(report)
        self.assertEqual(total(parsed, "views"), 300)
        self.assertEqual(total(parsed, "engagedViews"), 180)

    def test_blocked_analytics_stays_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "analytics.json"
            output = root / "optimization.json"
            markdown = root / "optimization.md"
            source.write_text(json.dumps({"status": "BLOCKED", "reason": "missing analytics token"}), encoding="utf-8")
            with patch.object(sys, "argv", ["weekly_optimization.py", "--input", str(source),
                                            "--output", str(output), "--markdown", str(markdown),
                                            "--upload-history", str(upload_history)]):
                main()
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("missing analytics token", markdown.read_text(encoding="utf-8"))

    def test_dashboard_is_self_contained_and_escapes_video_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analytics = root / "analytics.json"
            optimization = root / "optimization.json"
            output = root / "dashboard.html"
            analytics.write_text(json.dumps({
                "status": "completed",
                "start_date": "2026-11-01",
                "end_date": "2026-11-21",
                "reports": {
                    "shorts_daily": {"columnHeaders": [{"name": "day"}, {"name": "views"}],
                                     "rows": [["2026-11-20", 123]]},
                    "shorts_videos": {"columnHeaders": [{"name": "video"}, {"name": "views"}],
                                      "rows": [["bad<&id", 123]]},
                },
            }), encoding="utf-8")
            optimization.write_text(json.dumps({"recommendations": ["Review top Shorts."]}), encoding="utf-8")
            with patch.object(sys, "argv", ["build_factory_dashboard.py", "--analytics", str(analytics),
                                            "--optimization", str(optimization), "--output", str(output)]):
                build_dashboard()
            html = output.read_text(encoding="utf-8")
            self.assertIn("KOROUSH VIRAL SHORTS FACTORY", html)
            self.assertIn("Review top Shorts.", html)
            self.assertIn("bad&lt;&amp;id", html)
            self.assertNotIn("bad<&id", html)

    def test_comparison_and_top_video_are_generated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "analytics.json"
            output = root / "optimization.json"
            markdown = root / "optimization.md"
            upload_history = root / "upload_history.json"
            upload_history.write_text(json.dumps({
                "schema_version": 1,
                "uploads": {
                    "public:" + "a" * 64: {
                        "mode": "public", "status": "completed", "topic": "Solar storms",
                        "title": "Solar storms explained", "hook_text": "Why do solar storms happen?",
                        "hook_type": "question", "result": {"video_id": "videoA"}
                    },
                    "public:" + "b" * 64: {
                        "mode": "public", "status": "completed", "topic": "Ocean currents",
                        "title": "Ocean currents explained", "hook_text": "Scientists track ocean currents.",
                        "hook_type": "direct_fact", "result": {"video_id": "videoB"}
                    },
                },
            }), encoding="utf-8")
            payload = {
                "status": "completed",
                "start_date": "2026-10-25",
                "end_date": "2026-11-21",
                "reports": {
                    "shorts_daily": {
                        "columnHeaders": [{"name": "day"}, {"name": "views"}, {"name": "engagedViews"}],
                        "rows": [
                            ["2026-11-05", 100, 50],
                            ["2026-11-10", 120, 70],
                            ["2026-11-18", 80, 50],
                        ],
                    },
                    "shorts_videos": {
                        "columnHeaders": [{"name": "video"}, {"name": "views"}, {"name": "engagedViews"},
                                          {"name": "averageViewPercentage"}],
                        "rows": [
                            ["videoA", 200, 150, 82.5],
                            ["videoB", 300, 120, 40.0],
                        ],
                    },
                },
            }
            source.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(sys, "argv", ["weekly_optimization.py", "--input", str(source),
                                            "--output", str(output), "--markdown", str(markdown)]):
                main()
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["comparison"]["previous_14_day_views"], 100)
            self.assertEqual(result["comparison"]["recent_14_day_views"], 200)
            self.assertEqual(result["comparison"]["views_change_percent"], 100.0)
            self.assertEqual(result["top_by_engaged_views"][0]["video"], "videoA")
            self.assertEqual(result["top_by_engaged_views"][0]["topic"], "Solar storms")
            self.assertEqual(result["top_by_engaged_views"][0]["hook_type"], "question")
            self.assertEqual(result["topic_performance"][0]["topic"], "Solar storms")
            self.assertEqual(result["hook_performance"][0]["hook_type"], "question")
            self.assertEqual(result["metadata_join_coverage"]["videos_with_topic_and_hook"], 2)
            self.assertIn("youtube.com/watch?v=videoA", markdown.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
