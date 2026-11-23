import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from add_persian_subtitles import translate_with_fallback


class FreeTranslationFallbackTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"index": 1, "timing": "00:00:01,000 --> 00:00:02,000", "text": "Hello"},
            {"index": 2, "timing": "00:00:02,000 --> 00:00:03,000", "text": "Goodbye"},
        ]
        self.free = ("http://free/v1", "test-key", "auto")
        self.gemini = ("test-gemini-key", "gemini-2.5-flash")

    @patch("add_persian_subtitles.translate_ollama")
    def test_prefers_local_ollama(self, ollama):
        ollama.return_value = {1: "سلام", 2: "خداحافظ"}
        result, provider = translate_with_fallback(
            self.rows, self.free, self.gemini, False, ("http://localhost:11434", "qwen2.5:3b")
        )
        self.assertEqual(provider, "Ollama (local)")
        self.assertEqual(result[1], "سلام")

    @patch("add_persian_subtitles.translate_freellmapi")
    @patch("add_persian_subtitles.discover_free_models", return_value=["provider/free-model"])
    def test_uses_explicitly_free_freellmapi_model(self, discovery, translate):
        translate.return_value = {1: "سلام", 2: "خداحافظ"}
        result, provider = translate_with_fallback(self.rows, self.free, self.gemini)
        self.assertEqual(provider, "FreeLLMAPI")
        self.assertEqual(result[1], "سلام")
        discovery.assert_called_once()

    @patch("add_persian_subtitles.translate_ollama", side_effect=RuntimeError("local model unavailable"))
    @patch("add_persian_subtitles.translate_freellmapi", return_value={1: "سلام", 2: "خداحافظ"})
    @patch("add_persian_subtitles.discover_free_models", return_value=["provider/free-model"])
    def test_fails_over_from_local_to_free_gateway(self, discovery, translate, ollama):
        result, provider = translate_with_fallback(
            self.rows, self.free, self.gemini, False, ("http://localhost:11434", "qwen2.5:3b")
        )
        self.assertEqual(provider, "FreeLLMAPI")
        self.assertEqual(result[2], "خداحافظ")

    @patch("add_persian_subtitles.translate_gemini")
    @patch("add_persian_subtitles.discover_free_models", return_value=[])
    def test_blocks_unknown_price_and_paid_fallback_by_default(self, discovery, gemini):
        with self.assertRaisesRegex(RuntimeError, "All configured subtitle providers failed"):
            translate_with_fallback(self.rows, self.free, self.gemini, False)
        gemini.assert_not_called()

    @patch("add_persian_subtitles.translate_gemini", return_value={1: "سلام", 2: "خداحافظ"})
    @patch("add_persian_subtitles.discover_free_models", return_value=[])
    def test_gemini_is_used_only_when_free_tier_explicitly_enabled(self, discovery, gemini):
        result, provider = translate_with_fallback(self.rows, ("", "", "auto"), self.gemini, True)
        self.assertEqual(provider, "Gemini Free Tier")
        self.assertEqual(result[1], "سلام")

    def test_fails_when_no_provider_is_configured(self):
        with self.assertRaises(RuntimeError):
            translate_with_fallback(self.rows, ("", "", "auto"), ("", "gemini-2.5-flash"))


if __name__ == "__main__":
    unittest.main()
