import unittest
import tempfile
from pathlib import Path

from cli import allowed_license, score, select, srt_to_vtt, validate_subtitle_file, write_clip_srt


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

    def test_does_not_create_arbitrary_fallback_windows(self):
        self.assertEqual(select([], 360, 3), [])
        self.assertEqual(select([], 600, 4), [])

    def test_short_sources_are_not_downgraded_to_short_shorts(self):
        self.assertEqual(select([], 119.9, 4), [])

    def test_srt_to_vtt_creates_selectable_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "clip.fa.srt"
            target = Path(directory) / "clip.fa.vtt"
            source.write_text("1\n00:00:00,000 --> 00:00:01,000\nسلام\n", encoding="utf-8")
            srt_to_vtt(source, target)
            rendered = target.read_text(encoding="utf-8")
            self.assertTrue(rendered.startswith("WEBVTT\n"))
            self.assertIn("00:00:00.000 --> 00:00:01.000", rendered)
            self.assertIn("سلام", rendered)

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

    def test_subtitle_validator_accepts_valid_persian_srt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fa.srt"
            path.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nسلام\n\n"
                "2\n00:00:01,100 --> 00:00:02,000\nخوبی\n\n"
                "3\n00:00:02,100 --> 00:00:03,000\nدنیا\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_subtitle_file(path, 3.0), 3)

    def test_subtitle_validator_rejects_overlap_and_out_of_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fa.srt"
            overlap = (
                "1\n00:00:00,000 --> 00:00:02,000\nسلام\n\n"
                "2\n00:00:01,000 --> 00:00:02,500\nخوبی\n\n"
                "3\n00:00:02,600 --> 00:00:03,000\nدنیا\n"
            )
            path.write_text(overlap, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overlaps"):
                validate_subtitle_file(path, 3.0)
            path.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nسلام\n\n"
                "2\n00:00:01,100 --> 00:00:02,000\nخوبی\n\n"
                "3\n00:00:02,100 --> 00:00:04,000\nدنیا\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "overlaps"):
                validate_subtitle_file(path, 3.0)

    def test_subtitle_validator_rejects_minute_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fa.srt"
            path.write_text(
                "1\n00:60:00,000 --> 00:60:01,000\nسلام\n\n"
                "2\n00:60:01,100 --> 00:60:02,000\nخوبی\n\n"
                "3\n00:60:02,100 --> 00:60:03,000\nدنیا\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "overflow"):
                validate_subtitle_file(path, 4000.0)


if __name__ == "__main__":
    unittest.main()
