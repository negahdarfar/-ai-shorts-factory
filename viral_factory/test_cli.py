import unittest
import tempfile
from pathlib import Path

from cli import allowed_license, score, select, write_clip_srt


class ViralFactoryTests(unittest.TestCase):
    def test_allowed_licenses_are_explicit_and_sharealike_is_fail_closed(self):
        self.assertTrue(allowed_license("CC0"))
        self.assertTrue(allowed_license("CC BY 4.0"))
        self.assertTrue(allowed_license("Public domain"))
        self.assertFalse(allowed_license("CC BY-SA 4.0"))
        self.assertFalse(allowed_license("CC BY-NC-SA 4.0"))
        self.assertFalse(allowed_license("CC BY-ND 4.0"))
        self.assertFalse(allowed_license("unknown"))

    def test_hook_score_rewards_question_and_hook(self):
        self.assertGreater(
            score("Why is this amazing discovery so surprising?"),
            score("A quiet landscape video"),
        )

    def test_clip_selection_returns_non_overlapping_long_windows(self):
        transcript = [
            {"start": 0, "end": 65, "text": "Why is this discovery amazing? " * 12},
            {"start": 65, "end": 130, "text": "The surprising result changed everything. " * 12},
            {"start": 180, "end": 245, "text": "Here is another incredible discovery! " * 12},
            {"start": 245, "end": 310, "text": "This is the reason why it matters. " * 12},
        ]
        clips = select(transcript, 320, 3)
        self.assertTrue(clips)
        self.assertTrue(all(120 <= clip["duration"] <= 600 for clip in clips))
        for i, left in enumerate(clips):
            for right in clips[i + 1:]:
                self.assertTrue(
                    left["end"] <= right["start"] or right["end"] <= left["start"]
                )

    def test_fallback_clips_are_non_overlapping_and_in_range(self):
        clips = select([], 360, 3)
        self.assertEqual(len(clips), 3)
        for left, right in zip(clips, clips[1:]):
            self.assertLessEqual(left["end"], right["start"])
        self.assertTrue(all(120 <= clip["duration"] <= 600 for clip in clips))
        self.assertLessEqual(clips[-1]["end"], 360)

    def test_fallback_clips_cover_uneven_source_without_overlap(self):
        clips = select([], 600, 4)
        self.assertEqual(len(clips), 4)
        for left, right in zip(clips, clips[1:]):
            self.assertLessEqual(left["end"], right["start"])
        self.assertTrue(all(120 <= clip["duration"] <= 600 for clip in clips))
        self.assertLessEqual(clips[-1]["end"], 600)

    def test_short_sources_are_not_downgraded_to_short_shorts(self):
        self.assertEqual(select([], 119.9, 4), [])

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
