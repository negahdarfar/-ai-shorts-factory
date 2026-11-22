import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from free_model_router import discover_free_models, is_explicitly_free


class FreeModelRouterTests(unittest.TestCase):
    def test_only_explicit_free_ids_or_metadata_are_eligible(self):
        self.assertTrue(is_explicitly_free("nvidia/nemotron:free"))
        self.assertTrue(is_explicitly_free("kilo-auto/free"))
        self.assertTrue(is_explicitly_free("vendor/model", {"is_free": True}))
        self.assertTrue(is_explicitly_free("avalai/model", {"pricing": {"input": 0, "output": 0}}))
        self.assertTrue(is_explicitly_free("vendor/model", {"pricing": {"prompt": "0", "completion": "0"}}))
        self.assertFalse(is_explicitly_free("anthropic/claude-sonnet"))
        self.assertFalse(is_explicitly_free("provider/model-with-unknown-pricing"))
        self.assertFalse(is_explicitly_free("vendor/model", {"pricing": {"prompt": "0", "completion": "0.0001"}}))
        self.assertFalse(is_explicitly_free("vendor/model", {"pricing": {"prompt": "0"}}))

    def test_avalai_catalogue_cache_reuses_model_pricing_within_ttl(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = str(Path(directory) / "models.json")
            env = {"AVALAI_MODEL_CACHE_PATH": cache, "AVALAI_MODEL_CACHE_TTL_SECONDS": "300"}
            with patch.dict(os.environ, env, clear=False):
                with patch("free_model_router.AvalAIClient") as client_class:
                    client_class.return_value.list_models.return_value = [
                        {"id": "avalai/free-flash", "pricing": {"input": 0, "output": 0}}
                    ]
                    first = discover_free_models("https://api.avalai.ir/v1", "test-key", task="translation")
                    second = discover_free_models("https://api.avalai.ir/v1", "test-key", task="translation")
        self.assertEqual(first, ["avalai/free-flash"])
        self.assertEqual(second, first)
        client_class.return_value.list_models.assert_called_once()

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
    def test_structured_zero_pricing_models_are_discovered(self, urlopen):
        payload = {
            "data": [
                {"id": "vendor/paid", "pricing": {"prompt": "0.00001", "completion": "0.00002"}},
                {"id": "vendor/free-flash", "pricing": {"prompt": "0", "completion": "0"}},
                {"id": "vendor/declared-free", "free_tier": True},
                {"id": "vendor/unknown"},
            ]
        }
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
        result = discover_free_models("http://gateway/v1", "secret", task="seo")
        self.assertEqual(set(result), {"vendor/free-flash", "vendor/declared-free"})
        self.assertNotIn("vendor/paid", result)
        self.assertNotIn("vendor/unknown", result)

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
