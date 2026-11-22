import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from koroush_core.quality import QualityError, inspect_media, validate_media

class QualityTests(unittest.TestCase):
    def test_missing_file_is_rejected(self):
        with self.assertRaises(QualityError):
            inspect_media("this-file-does-not-exist.mp4")

    def test_empty_file_is_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "empty.mp4"
            path.touch()
            with self.assertRaises(QualityError):
                inspect_media(path)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg toolchain unavailable")
    def test_valid_vertical_audio_video_passes_quality_gate(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=navy:s=360x640:d=2",
                "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(path)
            ], check=True, timeout=60)
            report = validate_media(path, min_duration=1, max_duration=3,
                                    aspect="9:16", require_audio=True)
            self.assertTrue(report["has_audio"])
            self.assertGreater(report["height"], report["width"])
            self.assertGreater(report["size_bytes"], 0)

if __name__ == "__main__":
    unittest.main()
