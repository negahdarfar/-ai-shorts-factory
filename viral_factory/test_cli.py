import unittest
import tempfile
from pathlib import Path

from cli import allowed_license, score, select, write_clip_srt


class ViralFactoryTests(unittest.TestCase):
    def test_allowed_creative_commons_licenses(self):
        self.assertTrue(allowed_license("CC0"))
        self.assertTrue(allowed_license("CC BY 4.0"))
        self.assertFalse(allowed_license("CC BY-SA 4.0"))
        self.assertTrue(allowed_license("Public domain"))

    def test_restricted_licenses_are_rejected(self):
        self.assertFalse(allowed_license("CC BY-NC 4.0"))
        self.assertFalse(allowed_license("CC BY-ND 4.0"))

    def test_hook_score_rewards_question_and_hook(self):
        self.assertGreater(score("Why is this amazing discovery so surprising?"), score("A quiet landscape video"))

    def test_clip_selection_returns_non_overlapping_windows(self):
        transcript = [
            {"start": 0, "end": 12, "text": "Why is this discovery amazing?"},
            {"start": 12, "end": 25, "text": "The surprising result changed everything."},
            {"start": 60, "end": 72, "text": "Here is another incredible discovery!"},
            {"start": 72, "end": 88, "text": "This is the reason why it matters."},
        ]
        clips = select(transcript, 100, 3)
        self.assertTrue(clips)
        for i, left in enumerate(clips):
            for right in clips[i + 1:]:
                self.assertTrue(left["end"] <= right["start"] or right["end"] <= left["start"])

    def test_clip_srt_uses_relative_timestamps(self):
        segments = [
            {"start": 10.0, "end": 11.0, "text": "Hello"},
            {"start": 11.0, "end": 12.0, "text": "world"},
            {"start": 12.0, "end": 13.0, "text": "again"},
        ]
        clip = {"start": 10.5, "end": 13.0}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "clip.en.srt"
            count = write_clip_srt(segments, clip, output)
            self.assertEqual(count, 3)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 --> 00:00:00,500", rendered)
            self.assertIn("00:00:01,500 --> 00:00:02,500", rendered)


if __name__ == "__main__":
    unittest.main()
