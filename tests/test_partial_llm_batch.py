import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_seo_metadata", ROOT / "scripts" / "generate_seo_metadata.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PartialBatchTests(unittest.TestCase):
    def test_partial_provider_batch_is_rejected_for_failover(self):
        response = {
            "choices": [
                {"message": {"content": json.dumps({"items": []})}}
            ]
        }
        with patch.object(MODULE.urllib.request, "urlopen", return_value=FakeResponse(response)) as mocked_request:
            with patch.object(MODULE.time, "sleep"):
                with self.assertRaisesRegex(RuntimeError, "incomplete content batch"):
                    MODULE.generate_batch(
                        ["Solar storms", "Ocean currents"],
                        "English",
                        "unused-model",
                        "",
                        api_base_url="https://example.invalid/v1",
                        api_key="test-key",
                        api_model="free-model",
                        api_provider="Cloudflare",
                    )
            self.assertEqual(mocked_request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
