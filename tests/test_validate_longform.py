import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from validate_longform import validate_longform
from koroush_core.quality import QualityError


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class LongformValidationTests(unittest.TestCase):
    def make_video(self, path, size="1280x720", duration="2", audio=True):
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", f"color=c=black:s={size}:d={duration}"]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
                    "-shortest", "-c:a", "aac"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
        subprocess.run(cmd, check=True, capture_output=True)

    def test_accepts_hd_16x9_with_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.mp4"
            self.make_video(path)
            result = validate_longform(str(path), min_duration=1)
            self.assertEqual(result["quality_gate"], "passed")
            self.assertTrue(result["has_audio"])

    def test_rejects_vertical_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vertical.mp4"
            self.make_video(path, size="720x1280")
            with self.assertRaises(QualityError):
                validate_longform(str(path), min_duration=1)

    def test_rejects_video_without_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "silent.mp4"
            self.make_video(path, audio=False)
            with self.assertRaises(QualityError):
                validate_longform(str(path), min_duration=1)

    def test_rejects_duration_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "short.mp4"
            self.make_video(path)
            with self.assertRaises(QualityError):
                validate_longform(str(path), min_duration=10)


if __name__ == "__main__":
    unittest.main()
