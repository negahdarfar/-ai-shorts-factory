import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from avalai_client import AvalAIClient, AvalAIError, DEFAULT_BASE_URL


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

    def test_http_error_does_not_leak_body_or_key(self):
        client = AvalAIClient(api_key="secret-value", max_retries=0)
        error = HTTPError("https://api.avalai.ir/v1/models", 401, "bad", {}, BytesIO(b"secret-value"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(AvalAIError) as caught:
                client.list_models()
        self.assertNotIn("secret-value", str(caught.exception))
        self.assertIn("401", str(caught.exception))

    def test_rejects_non_https_base(self):
        with self.assertRaises(ValueError):
            AvalAIClient(api_key="x", base_url="http://example.com/v1")


if __name__ == "__main__":
    unittest.main()
