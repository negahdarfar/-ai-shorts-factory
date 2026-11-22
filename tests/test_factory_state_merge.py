import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from merge_factory_state import merge_topics, merge_uploads, main


class FactoryStateMergeTests(unittest.TestCase):
    def test_topics_merge_case_insensitively(self):
        self.assertEqual(
            merge_topics(["Solar storms"], ["solar STORMS", "Ocean currents"], "topics"),
            ["Solar storms", "Ocean currents"],
        )

    def test_completed_upload_beats_pending_record(self):
        completed = {
            "public:abc": {
                "mode": "public",
                "status": "completed",
                "completed_at": "2026-11-20T12:00:00+00:00",
                "video_id": "video123",
            }
        }
        pending = {
            "public:abc": {
                "mode": "public",
                "status": "pending",
                "started_at": "2026-11-21T12:00:00+00:00",
            }
        }
        self.assertEqual(merge_uploads(completed, pending)["public:abc"]["status"], "completed")

    def test_new_completed_upload_replaces_pending(self):
        pending = {"public:abc": {"mode": "public", "status": "pending", "started_at": "2026-11-20"}}
        completed = {"public:abc": {"mode": "public", "status": "completed", "completed_at": "2026-11-20"}}
        self.assertEqual(merge_uploads(pending, completed)["public:abc"]["status"], "completed")

    def test_both_directories_receive_merged_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            durable = root / "durable"
            runtime = root / "runtime"
            durable.mkdir()
            runtime.mkdir()
            (durable / "seen_topics.json").write_text(json.dumps(["Solar storms"]), encoding="utf-8")
            (runtime / "seen_topics.json").write_text(json.dumps(["Ocean currents"]), encoding="utf-8")
            (durable / "published_topics.json").write_text("[]", encoding="utf-8")
            (runtime / "published_topics.json").write_text("[]", encoding="utf-8")
            (durable / "upload_history.json").write_text(json.dumps({"schema_version": 1, "uploads": {}}), encoding="utf-8")
            (runtime / "upload_history.json").write_text(json.dumps({"schema_version": 1, "uploads": {
                "public:abc": {"mode": "public", "status": "completed", "topic": "Ocean currents"}
            }}), encoding="utf-8")
            sys.argv = ["merge_factory_state.py", "--runtime", str(runtime), "--durable", str(durable), "--direction", "both"]
            main()
            for folder in (durable, runtime):
                topics = json.loads((folder / "seen_topics.json").read_text(encoding="utf-8"))
                self.assertEqual(topics, ["Solar storms", "Ocean currents"])
                ledger = json.loads((folder / "upload_history.json").read_text(encoding="utf-8"))
                self.assertIn("public:abc", ledger["uploads"])


if __name__ == "__main__":
    unittest.main()
