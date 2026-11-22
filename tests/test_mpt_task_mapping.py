import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_mpt_batch_with_retry import task_output_dirs


class MptTaskMappingTests(unittest.TestCase):
    def test_final_files_are_grouped_by_originating_task_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "task-a"
            second = root / "task-b"
            first.mkdir()
            second.mkdir()
            (first / "final-1.mp4").write_bytes(b"video-a")
            (second / "final-1.mp4").write_bytes(b"video-b")
            (second / "intermediate.mp4").write_bytes(b"not-final")
            result = task_output_dirs(root)
            self.assertEqual(len(result), 2)
            self.assertEqual(len(result[first.resolve()]), 1)
            self.assertEqual(len(result[second.resolve()]), 1)

    def test_missing_task_directory_returns_empty_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "not-created"
            self.assertEqual(task_output_dirs(missing), {})


if __name__ == "__main__":
    unittest.main()
