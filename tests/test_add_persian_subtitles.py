import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from add_persian_subtitles import parse_expected_count, write_vtt


class ExpectedSubtitleBatchTests(unittest.TestCase):
    def test_writes_webvtt_sidecar_without_modifying_srt(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "captions.fa.srt"
            target = Path(directory) / "captions.fa.vtt"
            source.write_text(
                "1\\n00:00:00,000 --> 00:00:01,000\\nسلام\\n",
                encoding="utf-8",
            )
            write_vtt(source, target)
            rendered = target.read_text(encoding="utf-8")
            self.assertTrue(rendered.startswith("WEBVTT\\n"))
            self.assertIn("00:00:00.000 --> 00:00:01.000", rendered)
            self.assertIn("سلام", rendered)
            self.assertIn("00:00:00,000", source.read_text(encoding="utf-8"))

    def test_default_is_four(self):
        self.assertEqual(parse_expected_count("4"), 4)

    def test_supported_batch_sizes(self):
        for count in range(4, 11):
            with self.subTest(count=count):
                self.assertEqual(parse_expected_count(str(count)), count)

    def test_rejects_counts_outside_supported_range(self):
        for value in ("0", "3", "11", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_expected_count(value)

    def test_rejects_non_integer_count(self):
        with self.assertRaises(ValueError):
            parse_expected_count("four")


if __name__ == "__main__":
    unittest.main()
