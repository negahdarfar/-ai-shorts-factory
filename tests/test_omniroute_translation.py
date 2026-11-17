import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from add_persian_subtitles import parse_translation_json


class OmniRouteTranslationParsingTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"index": 1, "timing": "00:00:01,000 --> 00:00:02,000", "text": "Hello"},
            {"index": 2, "timing": "00:00:02,000 --> 00:00:03,000", "text": "Goodbye"},
        ]

    def test_parses_json_object(self):
        raw = '{"translations":[{"index":1,"text":"سلام"},{"index":2,"text":"خداحافظ"}]}'
        result = parse_translation_json(raw, self.rows, "OmniRoute")
        self.assertEqual(result, {1: "سلام", 2: "خداحافظ"})

    def test_parses_markdown_fenced_json(self):
        raw = ' ```json\n{"translations":[{"index":1,"text":"سلام"},{"index":2,"text":"خداحافظ"}]}\n``` '
        result = parse_translation_json(raw, self.rows, "OmniRoute")
        self.assertEqual(result[1], "سلام")

    def test_rejects_missing_cues(self):
        raw = '{"translations":[{"index":1,"text":"سلام"}]}'
        with self.assertRaises(RuntimeError):
            parse_translation_json(raw, self.rows, "OmniRoute")


if __name__ == "__main__":
    unittest.main()
