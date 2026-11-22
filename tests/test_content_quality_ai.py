import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_content_quality import local_review, parse_ai, evaluate


class ContentQualityTests(unittest.TestCase):
    def test_local_fallback_never_claims_fact_check(self):
        rows = local_review([{"title":"Example", "video_script":"A short factual script."}])
        self.assertEqual(rows[0]["decision"], "NEEDS_HUMAN_REVIEW")
        self.assertFalse(rows[0]["factual_accuracy_verified"])

    def test_ai_response_requires_exact_item_count(self):
        with self.assertRaises(ValueError):
            parse_ai('{"items":[]}', 1)

    def test_ai_response_accepts_valid_editorial_result(self):
        rows = parse_ai('{"items":[{"score":82,"decision":"REVIEW","issues":[],"strengths":["Clear hook"]}]}', 1)
        self.assertEqual(rows[0]["score"], 82)
        self.assertFalse(rows[0]["factual_accuracy_verified"])

    def test_evaluate_local_fallback_when_no_free_models(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.json"
            target = Path(directory) / "out.json"
            source.write_text(json.dumps([{"title":"Demo","video_script":"A story about a subject."}]), encoding="utf-8")
            with patch("evaluate_content_quality.routes", return_value=[]):
                result = evaluate(str(source), str(target))
            self.assertEqual(result["status"], "LOCAL_FALLBACK_NEEDS_HUMAN_REVIEW")
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
