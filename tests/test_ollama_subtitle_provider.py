import json
import unittest
from unittest.mock import patch

from scripts import add_persian_subtitles as subtitles


class OllamaSubtitleProviderTests(unittest.TestCase):
    def test_local_translation_preserves_cue_indices_without_api_key(self):
        rows = [
            {"index": 7, "timing": "00:00:01,000 --> 00:00:02,000", "text": "Hello world"},
            {"index": 9, "timing": "00:00:02,000 --> 00:00:03,000", "text": "Welcome back"},
        ]
        response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "translations": [
                            {"index": 7, "text": "سلام دنیا"},
                            {"index": 9, "text": "خوش آمدید"},
                        ]
                    }, ensure_ascii=False)
                }
            }]
        }
        with patch.object(subtitles, "post_json_with_retry", return_value=response) as mocked:
            translated = subtitles.translate_ollama(
                rows, "http://127.0.0.1:11434/v1", "qwen2.5:3b"
            )

        self.assertEqual(translated, {7: "سلام دنیا", 9: "خوش آمدید"})
        self.assertEqual(mocked.call_args.args[2], {"Content-Type": "application/json"})
        self.assertNotIn("Authorization", mocked.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
