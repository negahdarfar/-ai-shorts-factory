import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from topic_history import (
    ensure_new_topics,
    load_published_topics,
    load_seen_topics,
    record_published_topic,
    record_seen_topics,
)


class TopicHistoryTests(unittest.TestCase):
    def test_published_topics_are_loaded_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            record_published_topic(state, "Solar storms")
            self.assertIn("solar storms", load_published_topics(state))

    def test_publication_guard_blocks_reused_topic(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            record_published_topic(state, "Solar storms")
            with self.assertRaisesRegex(RuntimeError, "PUBLIC_PUBLISH_BLOCKED_DUPLICATE_TOPICS"):
                ensure_new_topics(state, ["solar STORMS", "New topic"])

    def test_new_topics_pass_publication_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            record_published_topic(state, "Solar storms")
            ensure_new_topics(state, ["Ocean currents", "Deep sea bioluminescence"])

    def test_seen_history_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            record_seen_topics(state, ["Solar storms", "Ocean currents"])
            self.assertEqual(load_seen_topics(state), {"solar storms", "ocean currents"})

    def test_malformed_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "published_topics.json").write_text('{"bad":"shape"}', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "malformed"):
                load_published_topics(state)


if __name__ == "__main__":
    unittest.main()
