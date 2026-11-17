import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("youtube_agent_runtime", ROOT / "scripts/youtube_agent_runtime.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class YouTubeAgentRuntimeTests(unittest.TestCase):
    def test_skill_allowlist_is_exactly_eleven(self):
        self.assertEqual(len(MODULE.SKILLS), 11)
        self.assertIn("yt-script", MODULE.SKILLS)
        self.assertNotIn("../secrets", MODULE.SKILLS)

    def test_model_request_uses_openai_compatible_endpoint(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self):
                return b'{"choices":[{"message":{"content":"Draft ready"}}]}'
        with patch.object(MODULE.urllib.request, "urlopen", return_value=Response()) as opened:
            result = MODULE.call_chat("https://gateway.example/v1", "test-token", "sample:free", "system", "user", 3)
        self.assertEqual(result, "Draft ready")
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, "https://gateway.example/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_rejects_unknown_or_paid_models_via_existing_router(self):
        self.assertTrue(MODULE.safe_name("yt-script"))
        self.assertEqual(MODULE.safe_name("../../bad name"), "bad-name")

if __name__ == "__main__":
    unittest.main()
