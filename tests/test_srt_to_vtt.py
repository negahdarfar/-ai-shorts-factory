import tempfile
import unittest
from pathlib import Path

from scripts.srt_to_vtt import convert_srt_to_vtt


class SrtToVttTests(unittest.TestCase):
    def test_converts_persian_and_english_cues(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "captions.fa.srt"
            target = Path(directory) / "captions.fa.vtt"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:01,200\nسلام\n\n"
                "2\n00:00:01,300 --> 00:00:02,000\nOpenAI\n",
                encoding="utf-8",
            )
            count = convert_srt_to_vtt(source, target)
            result = target.read_text(encoding="utf-8")
            self.assertEqual(count, 2)
            self.assertTrue(result.startswith("WEBVTT\n"))
            self.assertIn("00:00:00.000 --> 00:00:01.200", result)
            self.assertIn("سلام", result)
            self.assertIn("OpenAI", result)

    def test_rejects_bad_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.srt"
            target = Path(directory) / "bad.vtt"
            source.write_text("1\n00:90:00,000 --> 00:00:01,000\nBad\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid minute/second"):
                convert_srt_to_vtt(source, target)

    def test_rejects_empty_cue(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "empty.srt"
            target = Path(directory) / "empty.vtt"
            source.write_text("1\n00:00:00,000 --> 00:00:01,000\n\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Malformed|Empty"):
                convert_srt_to_vtt(source, target)


if __name__ == "__main__":
    unittest.main()
