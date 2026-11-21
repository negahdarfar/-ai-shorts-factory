import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_seo_metadata import main


def valid_record(words=200):
    topic = "Solar storms"
    return {
        "topic": topic,
        "metadata_source": "gemini_batch",
        "content_source": "gemini_batch",
        "video_script": " ".join(["solar"] * words),
        "video_terms": ["solar flare", "aurora sky", "sun surface", "magnetic field", "space weather"],
        "metadata": {
            "title": "Solar Storms and Their Surprising Effects",
            "description": "Solar storms can affect satellites and radio signals. Solar storms are the focus of this short documentary.",
            "primary_keyword": "Solar storms",
            "tags": ["solar storms", "space weather", "solar flare", "aurora", "satellites"],
            "hashtags": ["solarstorms"],
        },
    }


class SeoDurationValidationTests(unittest.TestCase):
    def run_validator(self, record, expected_count=4):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seo.json"
            batch = []
            for index in range(expected_count):
                item = valid_record(len(record["video_script"].split()))
                topic = f"Solar storms topic {index + 1}"
                item["topic"] = topic
                item["metadata"]["title"] = f"Solar storms topic {index + 1} and their effects"
                item["metadata"]["description"] = f"{topic} can affect satellites and radio signals."
                item["metadata"]["primary_keyword"] = topic
                batch.append(item)
            path.write_text(json.dumps(batch), encoding="utf-8")
            with patch.object(sys, "argv", ["validate_seo_metadata.py", "--input", str(path),
                                            "--expected-count", str(expected_count)]):
                main()

    def test_200_word_script_passes_60_to_120_second_gate(self):
        self.run_validator(valid_record(200))

    def test_140_word_script_fails_duration_gate(self):
        with self.assertRaises(SystemExit):
            self.run_validator(valid_record(140))

    def test_batch_count_above_ten_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_validator(valid_record(200), expected_count=11)


if __name__ == "__main__":
    unittest.main()
