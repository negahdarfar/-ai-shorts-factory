import json
import tempfile
import unittest
from pathlib import Path

from scripts.assemble_storyboard import load_scenes, _image_filter


class StoryboardManifestTests(unittest.TestCase):
    def test_legacy_video_paths_remain_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(["assets/old-clip.mp4"]), encoding="utf-8")
            scenes = load_scenes(path)
        self.assertEqual(scenes[0]["type"], "video")
        self.assertEqual(scenes[0]["start"], 0)

    def test_mixed_image_and_trimmed_video_scenes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps([
                {"path": "assets/photo.jpg", "type": "image", "duration": 9, "motion": "pan_right"},
                {"path": "assets/clip.mp4", "type": "video", "start": 3, "end": 12},
            ]), encoding="utf-8")
            scenes = load_scenes(path)
        self.assertEqual(scenes[0]["duration"], 9)
        self.assertEqual(scenes[0]["motion"], "pan_right")
        self.assertEqual(scenes[1]["end"] - scenes[1]["start"], 9)

    def test_image_extension_is_inferred(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps([{"path": "assets/still.webp", "duration": 5}]), encoding="utf-8")
            self.assertEqual(load_scenes(path)[0]["type"], "image")

    def test_rejects_invalid_image_duration_and_motion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps([{"path": "x.jpg", "type": "image", "duration": 0}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duration"):
                load_scenes(path)
            path.write_text(json.dumps([{"path": "x.jpg", "type": "image", "motion": "spin"}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "motion"):
                load_scenes(path)

    def test_rejects_invalid_video_trim(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps([{"path": "x.mp4", "start": 8, "end": 4}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "end > start"):
                load_scenes(path)

    def test_generates_1080p_motion_filter_for_still(self):
        value = _image_filter({"duration": 6, "motion": "zoom_in"})
        self.assertIn("zoompan", value)
        self.assertIn("1920x1080", value)


if __name__ == "__main__":
    unittest.main()
