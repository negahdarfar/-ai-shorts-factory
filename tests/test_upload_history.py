import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from upload_history import idempotency_key, load_upload_history, save_upload_history, sha256_file


class UploadHistoryTests(unittest.TestCase):
    def test_missing_history_starts_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            history = load_upload_history(Path(directory))
            self.assertEqual(history, {"schema_version": 1, "uploads": {}})

    def test_pending_and_completed_history_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            history = {
                "schema_version": 1,
                "uploads": {
                    "public:" + "a" * 64: {"mode": "public", "status": "pending"},
                    "private:" + "b" * 64: {"mode": "private", "status": "completed", "video_id": "abc"},
                },
            }
            save_upload_history(state, history)
            self.assertEqual(load_upload_history(state), history)

    def test_malformed_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            state.mkdir(exist_ok=True)
            (state / "upload_history.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "malformed"):
                load_upload_history(state)

    def test_idempotency_key_separates_public_and_private_modes(self):
        digest = "a" * 64
        self.assertEqual(idempotency_key("public", digest), "public:" + digest)
        self.assertEqual(idempotency_key("private", digest), "private:" + digest)
        with self.assertRaises(ValueError):
            idempotency_key("scheduled", digest)
        with self.assertRaises(ValueError):
            idempotency_key("public", "not-a-sha")

    def test_sha256_changes_when_file_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "video.mp4"
            path.write_bytes(b"first video")
            first = sha256_file(path)
            path.write_bytes(b"second video")
            second = sha256_file(path)
            self.assertNotEqual(first, second)
            self.assertEqual(len(first), 64)
            self.assertEqual(len(second), 64)


if __name__ == "__main__":
    unittest.main()
