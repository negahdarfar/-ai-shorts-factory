import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from koroush_core.quality import QualityError, inspect_media

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

if __name__ == "__main__":
    unittest.main()
