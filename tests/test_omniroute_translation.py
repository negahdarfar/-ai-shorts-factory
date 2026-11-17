import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from unittest.mock import patch
from add_persian_subtitles import parse_translation_json, translate_with_fallback


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

    @patch("add_persian_subtitles.translate_omniroute")
    @patch("add_persian_subtitles.translate_freellmapi")
    @patch("add_persian_subtitles.translate_gemini")
    @patch("add_persian_subtitles.discover_free_models", return_value=["kilo-auto/free"])
    def test_prefers_omniroute(self, discovery, gemini, free, omni):
        omni.return_value = {1: "سلام", 2: "خداحافظ"}
        result, provider = translate_with_fallback(
            self.rows, ("http://omni/v1", "key", "auto"),
            ("http://free/v1", "key", "auto"), ("gemini-key", "gemini-flash")
        )
        self.assertEqual(provider, "OmniRoute")
        self.assertEqual(result[1], "سلام")
        free.assert_not_called()
        gemini.assert_not_called()

    @patch("add_persian_subtitles.translate_omniroute", side_effect=RuntimeError("offline"))
    @patch("add_persian_subtitles.translate_freellmapi")
    @patch("add_persian_subtitles.translate_gemini")
    @patch("add_persian_subtitles.discover_free_models", return_value=["kilo-auto/free"])
    def test_falls_back_to_freellmapi_before_gemini(self, discovery, gemini, free, omni):
        free.return_value = {1: "سلام", 2: "خداحافظ"}
        result, provider = translate_with_fallback(
            self.rows, ("http://omni/v1", "key", "auto"),
            ("http://free/v1", "key", "auto"), ("gemini-key", "gemini-flash")
        )
        self.assertEqual(provider, "FreeLLMAPI")
        self.assertEqual(result[1], "سلام")
        gemini.assert_not_called()

    @patch("add_persian_subtitles.translate_omniroute", side_effect=RuntimeError("offline"))
    @patch("add_persian_subtitles.translate_freellmapi", side_effect=RuntimeError("offline"))
    @patch("add_persian_subtitles.translate_gemini")
    @patch("add_persian_subtitles.discover_free_models", return_value=["kilo-auto/free"])
    def test_uses_gemini_as_last_fallback(self, discovery, gemini, free, omni):
        gemini.return_value = {1: "سلام", 2: "خداحافظ"}
        result, provider = translate_with_fallback(
            self.rows, ("http://omni/v1", "key", "auto"),
            ("http://free/v1", "key", "auto"), ("gemini-key", "gemini-flash")
        )
        self.assertEqual(provider, "Gemini")
        self.assertEqual(result[2], "خداحافظ")

    def test_fails_when_no_provider_is_configured(self):
        with self.assertRaises(RuntimeError):
            translate_with_fallback(
                self.rows, ("", "", "auto"), ("", "", "auto"), ("", "gemini-flash")
            )


if __name__ == "__main__":
    unittest.main()
