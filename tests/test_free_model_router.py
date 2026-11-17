import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from free_model_router import discover_free_models, is_explicitly_free


class FreeModelRouterTests(unittest.TestCase):
    def test_only_explicit_free_ids_are_eligible(self):
        self.assertTrue(is_explicitly_free("nvidia/nemotron:free"))
        self.assertTrue(is_explicitly_free("kilo-auto/free"))
        self.assertFalse(is_explicitly_free("anthropic/claude-sonnet"))
        self.assertFalse(is_explicitly_free("provider/model-with-unknown-pricing"))

    @patch("free_model_router.urllib.request.urlopen")
    def test_discovers_and_ranks_free_translation_models(self, urlopen):
        payload = {
            "data": [
                {"id": "nvidia/nemotron-3.5-super-vl:free"},
                {"id": "nvidia/nemotron-3.5-lightning:free"},
                {"id": "kilo-auto/free"},
                {"id": "provider/paid-model"},
            ]
        }
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps(payload).encode("utf-8")
        result = discover_free_models("http://gateway/v1", "secret", task="translation")
        self.assertEqual(result[0], "nvidia/nemotron-3.5-lightning:free")
        self.assertIn("kilo-auto/free", result)
        self.assertNotIn("provider/paid-model", result)
        urlopen.assert_called_once()

    @patch("free_model_router.urllib.request.urlopen")
    def test_seo_prefers_reasoning_or_super_models(self, urlopen):
        payload = {
            "data": [
                {"id": "nvidia/nemotron-3.5-lightning:free"},
                {"id": "nvidia/nemotron-3-ultra-550b:free"},
                {"id": "kilo-auto/free"},
            ]
        }
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
        result = discover_free_models("http://gateway/v1", "secret", task="seo")
        self.assertEqual(result[0], "nvidia/nemotron-3-ultra-550b:free")

    @patch("free_model_router.urllib.request.urlopen")
    def test_unknown_or_empty_catalogue_returns_no_models(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"data":[]}'
        self.assertEqual(discover_free_models("http://gateway/v1", "secret"), [])


if __name__ == "__main__":
    unittest.main()
