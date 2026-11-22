import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from avalai_client import AvalAIClient, AvalAIError, DEFAULT_BASE_URL
from free_model_router import is_explicitly_free, is_chat_capable


class FakeResponse:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size=-1):
        return json.dumps(self.value).encode("utf-8")


class AvalAIClientTests(unittest.TestCase):
    def test_default_base_url(self):
        self.assertEqual(DEFAULT_BASE_URL, "https://api.avalai.ir/v1")

    def test_missing_secret_fails_before_network(self):
        with patch.dict(os.environ, {"AVALAI_API_KEY": ""}):
            client = AvalAIClient(api_key="")
        with patch("urllib.request.urlopen") as call:
            with self.assertRaisesRegex(AvalAIError, "not configured"):
                client.list_models()
            call.assert_not_called()

    def test_model_catalogue_is_read_only_get(self):
        client = AvalAIClient(api_key="dummy", max_retries=0)
        with patch("urllib.request.urlopen", return_value=FakeResponse({"data":[{"id":"sample"}]})) as call:
            rows = client.list_models()
        self.assertEqual(rows[0]["id"], "sample")
        self.assertEqual(call.call_args.args[0].get_method(), "GET")

    def test_chat_completion_parses_response(self):
        client = AvalAIClient(api_key="dummy", max_retries=0)
        payload = {"choices":[{"message":{"content":"hello"}}]}
        with patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
            self.assertEqual(client.chat_completion("sample", [{"role":"user","content":"hi"}]), "hello")

    def test_moderate_uses_dedicated_endpoint_and_parses_results(self):
        client = AvalAIClient(api_key="dummy", max_retries=0)
        payload = {"results": [{"flagged": False, "categories": {}}]}
        with patch("urllib.request.urlopen", return_value=FakeResponse(payload)) as call:
            result = client.moderate("omni-moderation-latest", ["safe text"])
        self.assertFalse(result["results"][0]["flagged"])
        self.assertTrue(call.call_args.args[0].full_url.endswith("/moderations"))
        self.assertEqual(call.call_args.args[0].get_method(), "POST")

    def test_moderation_rejects_result_count_mismatch(self):
        client = AvalAIClient(api_key="dummy", max_retries=0)
        with patch("urllib.request.urlopen", return_value=FakeResponse({"results": []})):
            with self.assertRaisesRegex(AvalAIError, "no moderation results"):
                client.moderate("omni-moderation-latest", ["text"])

    def test_http_error_does_not_leak_body_or_key(self):
        client = AvalAIClient(api_key="secret-value", max_retries=0)
        error = HTTPError("https://api.avalai.ir/v1/models", 401, "bad", {}, BytesIO(b"secret-value"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(AvalAIError) as caught:
                client.list_models()
        self.assertNotIn("secret-value", str(caught.exception))
        self.assertIn("401", str(caught.exception))

    def test_zero_price_catalogue_model_is_explicitly_free(self):
        metadata = {"pricing": {"prompt": "0", "completion": "0"}}
        self.assertTrue(is_explicitly_free("catalogue-model", metadata))

    def test_avalai_catalogue_zero_input_output_prices_are_free(self):
        metadata = {"min_tier": 0, "pricing": {"input": 0, "output": 0, "cached_input": 0}}
        self.assertTrue(is_explicitly_free("cf-free-example", metadata))
        self.assertTrue(is_explicitly_free("avalai-catalogue-model", metadata))

    def test_search_and_tool_models_are_not_chat_capable(self):
        for model in ("serper-search", "perplexity-search", "parallel_ai-search-pro", "tavily-search", "scribe_v2", "scribe_v1", "muse-image-1.0", "eleven_v4_turbo", "eleven_flash_v2", "voice-chat-model"):
            with self.subTest(model=model):
                self.assertFalse(is_chat_capable(model, {}))

    def test_text_chat_models_remain_chat_capable(self):
        self.assertTrue(is_chat_capable("qwen3-32b", {"architecture": {"modality": "text->text"}}))
        self.assertTrue(is_chat_capable("llama-3.3-70b", {"modalities": ["text"]}))

    def test_catalogue_task_metadata_excludes_search_endpoint(self):
        self.assertFalse(is_chat_capable(
            "provider-model",
            {"task": "web_search", "description": "Search the web and return sources"}
        ))

    def test_per_query_fee_disqualifies_zero_token_price_model(self):
        metadata = {
            "pricing": {
                "input": 0,
                "output": 0,
                "input_cost_per_query": 0.001,
            }
        }
        self.assertFalse(is_explicitly_free("serper-search", metadata))

    def test_all_advertised_costs_must_be_zero(self):
        self.assertTrue(is_explicitly_free(
            "free-chat-model",
            {"pricing": {"input": 0, "output": 0, "cached_input": 0}}
        ))
        self.assertFalse(is_explicitly_free(
            "model:free",
            {"pricing": {"input": 0, "output": 0, "image": 0.02}}
        ))

    def test_unknown_or_paid_model_is_never_assumed_free(self):
        self.assertFalse(is_explicitly_free("catalogue-model", {"pricing": {"prompt": "0.1", "completion": "0.2"}}))
        self.assertFalse(is_explicitly_free("catalogue-model", {}))

    def test_retries_rate_limit_then_succeeds(self):
        client = AvalAIClient(api_key="dummy", max_retries=1)
        rate_limit = HTTPError("https://api.avalai.ir/v1/models", 429, "rate limited",
                               {"Retry-After": "0"}, BytesIO(b""))
        with patch("urllib.request.urlopen", side_effect=[rate_limit, FakeResponse({"data": [{"id": "free-model"}]})]) as call:
            with patch("time.sleep") as sleep:
                rows = client.list_models()
        self.assertEqual(rows[0]["id"], "free-model")
        self.assertEqual(call.call_count, 2)
        sleep.assert_called_once()

    def test_rejects_non_https_base(self):
        with self.assertRaises(ValueError):
            AvalAIClient(api_key="x", base_url="http://example.com/v1")


if __name__ == "__main__":
    unittest.main()
