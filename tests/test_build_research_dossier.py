import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_research_dossier import ResearchError, build_research_dossier


class ResearchDossierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "input.json"
        self.output = self.root / "dossier.json"
        self.report = self.root / "dossier.md"
        self.data = {
            "topic": "Example scientific topic",
            "research_date": "2026-11-22",
            "sources": [
                {"id": "S1", "title": "Primary paper", "publisher": "Institute A", "url": "https://a.example.org/paper", "source_type": "academic", "published_at": "2025-01-01", "accessed_at": "2026-11-20"},
                {"id": "S2", "title": "Official dataset", "publisher": "Agency B", "url": "https://b.example.org/data", "source_type": "primary", "published_at": "2025-02-01", "accessed_at": "2026-11-20"},
                {"id": "S3", "title": "Independent review", "publisher": "Journal C", "url": "https://c.example.org/review", "source_type": "academic", "published_at": "2025-03-01", "accessed_at": "2026-11-21"},
            ],
            "claims": [
                {"id": "C1", "claim": "A carefully worded example claim.", "status": "confirmed", "source_ids": ["S1", "S2"]}
            ],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_dossier(self):
        self.source.write_text(json.dumps(self.data), encoding="utf-8")
        return build_research_dossier(self.source, self.output, self.report)

    def test_builds_dossier_and_markdown_report(self):
        result = self.run_dossier()
        self.assertEqual(result["research_gate"], "passed")
        self.assertEqual(result["distinct_domain_count"], 3)
        self.assertTrue(self.report.is_file())
        self.assertTrue(self.output.is_file())
        self.assertTrue(result["claims"][0]["usable_in_narration"])

    def test_confirmed_claim_needs_two_domains(self):
        self.data["claims"][0]["source_ids"] = ["S1", "S1"]
        self.data["claims"][0]["source_ids"] = ["S1"]
        with self.assertRaisesRegex(ResearchError, "two distinct domains"):
            self.run_dossier()

    def test_unknown_source_reference_is_rejected(self):
        self.data["claims"][0]["source_ids"] = ["S1", "S404"]
        with self.assertRaisesRegex(ResearchError, "unknown source ids"):
            self.run_dossier()

    def test_unverified_claim_blocks_gate(self):
        self.data["claims"][0]["status"] = "unverified"
        self.data["claims"][0]["source_ids"] = ["S1"]
        result = self.run_dossier()
        self.assertEqual(result["research_gate"], "blocked")
        self.assertFalse(result["claims"][0]["usable_in_narration"])

    def test_disputed_claim_requires_note_and_two_domains(self):
        self.data["claims"][0]["status"] = "disputed"
        self.data["claims"][0]["source_ids"] = ["S1", "S2"]
        with self.assertRaisesRegex(ResearchError, "explanation in notes"):
            self.run_dossier()

    def test_requires_distinct_domains(self):
        self.data["sources"][1]["url"] = "https://a.example.org/another"
        self.data["sources"][2]["url"] = "https://a.example.org/third"
        with self.assertRaisesRegex(ResearchError, "distinct domains"):
            self.run_dossier()

    def test_rejects_non_https_source(self):
        self.data["sources"][0]["url"] = "http://a.example.org/paper"
        with self.assertRaisesRegex(ResearchError, "HTTPS"):
            self.run_dossier()


if __name__ == "__main__":
    unittest.main()
