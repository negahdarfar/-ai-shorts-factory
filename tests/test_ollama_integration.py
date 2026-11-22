import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class OllamaIntegrationTests(unittest.TestCase):
    def test_seo_generation_uses_local_openai_compatible_endpoint_without_auth(self):
        module = load_script("seo_generator_ollama_test", "scripts/generate_seo_metadata.py")
        script = " ".join(["A clear factual narration sentence explains the subject with useful context and a practical takeaway."] * 9)
        metadata = {
            "primary_keyword": "solar storms",
            "secondary_keywords": ["space weather"],
            "title": "Solar storms explained",
            "description": "A factual introduction to solar storms.",
            "hashtags": ["science"],
            "tags": ["solar storms", "space weather"],
            "pinned_comment": "What should we explore next?",
            "thumbnail_concept": "The Sun with a solar flare",
            "search_intent": "Understand solar storms",
        }
        payload = {"items": [{
            "index": 1, "video_script": script,
            "video_terms": ["solar flare closeup", "Sun surface activity", "Earth aurora lights", "solar observatory telescope", "space weather satellite"],
            "metadata": metadata,
        }]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps({"choices": [{"message": {"content": json.dumps(payload)}}]}).encode()
        with patch.object(module.urllib.request, "urlopen", return_value=Response()) as mocked:
            result = module.generate_batch(
                ["Solar storms"], "English", "", "", api_base_url="http://127.0.0.1:11434/v1",
                api_key="", api_model="qwen2.5:3b", api_provider="Ollama", max_attempts=1,
                repair_missing=False,
            )
        self.assertIn(1, result)
        request = mocked.call_args.args[0]
        self.assertNotIn("Authorization", request.headers)

    def test_ollama_subtitle_translation_preserves_cue_indices(self):
        module = load_script("subtitle_ollama_test", "scripts/add_persian_subtitles.py")
        rows = [{"index": 7, "timing": "00:00:01,000 --> 00:00:02,000", "text": "Hello world"}]
        response = {"choices": [{"message": {"content": json.dumps({"translations": [{"index": 7, "text": "سلام دنیا"}]})}}]}
        with patch.object(module, "post_json_with_retry", return_value=response) as mocked:
            translated = module.translate_ollama(rows, "http://127.0.0.1:11434/v1", "qwen2.5:3b")
        self.assertEqual(translated, {7: "سلام دنیا"})
        self.assertEqual(mocked.call_args.args[2], {"Content-Type": "application/json"})


if __name__ == "__main__":
    unittest.main()
