import json
import unittest
from unittest.mock import patch

from scripts import generate_seo_metadata as seo


class OllamaSeoProviderTests(unittest.TestCase):
    def test_local_ollama_generates_valid_item_without_authorization_header(self):
        script = " ".join(
            ["Solar storms can affect Earth magnetic field and create bright auroras across the night sky."] * 9
        )
        item = {
            "index": 1,
            "video_script": script,
            "video_terms": [
                "solar flare closeup", "Sun surface activity", "Earth aurora lights",
                "solar observatory telescope", "space weather satellite",
            ],
            "metadata": {
                "primary_keyword": "solar storms",
                "secondary_keywords": ["space weather", "solar activity"],
                "title": "Solar storms explained",
                "description": "A factual introduction to solar storms.",
                "hashtags": ["science"],
                "tags": ["solar storms", "space weather"],
                "pinned_comment": "What should we explore next?",
                "thumbnail_concept": "The Sun with a solar flare",
                "search_intent": "Understand solar storms",
            },
        }
        response_payload = {"items": [item]}

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({
                    "choices": [{
                        "message": {"content": json.dumps(response_payload)}
                    }]
                }).encode("utf-8")

        with patch.object(seo.urllib.request, "urlopen", return_value=Response()) as mocked:
            result = seo.generate_batch(
                ["Solar storms"], "English", "", "",
                api_base_url="http://127.0.0.1:11434/v1",
                api_key="", api_model="qwen2.5:3b",
                api_provider="Ollama", max_attempts=1, repair_missing=False,
            )

        self.assertIn(1, result)
        request = mocked.call_args.args[0]
        self.assertNotIn("Authorization", request.headers)


if __name__ == "__main__":
    unittest.main()
