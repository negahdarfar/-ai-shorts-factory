import unittest
from unittest.mock import patch

from scripts.validate_longform import validate_longform
from koroush_core.quality import QualityError


class LongformValidationTests(unittest.TestCase):
    def report(self, **overrides):
        value = {
            "width": 1920,
            "height": 1080,
            "duration_seconds": 720.0,
            "has_audio": True,
            "video_codec": "h264",
            "audio_codec": "aac",
        }
        value.update(overrides)
        return value

    def test_accepts_hd_16x9_with_audio_in_duration_range(self):
        with patch("scripts.validate_longform.validate_media", return_value=self.report()) as media:
            result = validate_longform("documentary.mp4", min_duration=600)
        self.assertEqual(result["quality_gate"], "passed")
        media.assert_called_once_with(
            "documentary.mp4",
            min_duration=600,
            max_duration=1800,
            aspect="16:9",
            require_audio=True,
        )

    def test_rejects_minimum_below_ten_minutes(self):
        with self.assertRaisesRegex(QualityError, "between 600 and 1800"):
            validate_longform("documentary.mp4", min_duration=480)

    def test_rejects_minimum_above_thirty_minutes(self):
        with self.assertRaisesRegex(QualityError, "between 600 and 1800"):
            validate_longform("documentary.mp4", min_duration=1801)

    def test_rejects_vertical_video(self):
        with patch("scripts.validate_longform.validate_media", return_value=self.report(width=720, height=1280)):
            with self.assertRaisesRegex(QualityError, "at least 1280x720"):
                validate_longform("vertical.mp4", min_duration=600)

    def test_rejects_video_without_audio(self):
        with patch("scripts.validate_longform.validate_media", side_effect=QualityError("Audio stream is required but missing.")):
            with self.assertRaisesRegex(QualityError, "Audio stream"):
                validate_longform("silent.mp4", min_duration=600)

    def test_rejects_output_over_thirty_minutes(self):
        with patch("scripts.validate_longform.validate_media", side_effect=QualityError("Duration exceeds maximum (1800s).")):
            with self.assertRaisesRegex(QualityError, "exceeds maximum"):
                validate_longform("too-long.mp4", min_duration=600)


if __name__ == "__main__":
    unittest.main()
