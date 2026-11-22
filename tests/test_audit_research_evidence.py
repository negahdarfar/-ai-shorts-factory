import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_research_evidence import audit_research_evidence, normalize_url


class ResearchEvidenceAuditTests(unittest.TestCase):
    def test_normalizes_www_and_trailing_slash(self):
        self.assertEqual(normalize_url("https://www.example.org/story/"), "https://example.org/story")

    def test_matches_claim_to_exact_source_url_and_preserves_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dossier = root / "dossier.json"
            extracts = root / "extracts.json"
            out = root / "audit.json"
            md = root / "audit.md"
            dossier.write_text(json.dumps({
                "topic": "test",
                "sources": [{"id": "S1", "url": "https://www.example.org/study/"}],
                "claims": [{"id": "C1", "claim": "Solar energy reduces carbon emissions significantly.",
                           "status": "confirmed", "source_ids": ["S1"]}]
            }), encoding="utf-8")
            extracts.write_text(json.dumps({"pages": [{
                "requested_url": "https://example.org/study",
                "extraction_status": "needs_editorial_review",
                "page_title": "Solar study",
                "extracted_text": "The study reports that solar energy reduces carbon emissions significantly across the region."
            }]}), encoding="utf-8")
            result = audit_research_evidence(dossier, extracts, out, md)
            self.assertEqual(result["claims"][0]["audit_status"], "matching_text_found")
            self.assertEqual(result["claims"][0]["existing_status_unchanged"], "confirmed")
            self.assertTrue(result["claims"][0]["source_results"][0]["excerpts"])
            self.assertTrue(out.is_file())
            self.assertTrue(md.is_file())

    def test_reports_missing_extraction_without_promoting_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dossier = root / "d.json"
            extracts = root / "e.json"
            dossier.write_text(json.dumps({
                "topic": "test", "sources": [{"id": "S1", "url": "https://example.org/a"}],
                "claims": [{"id": "C1", "claim": "A useful factual claim", "status": "unverified", "source_ids": ["S1"]}]
            }), encoding="utf-8")
            extracts.write_text(json.dumps({"pages": []}), encoding="utf-8")
            result = audit_research_evidence(dossier, extracts, root / "o.json", root / "o.md")
            self.assertEqual(result["claims"][0]["source_results"][0]["status"], "source_not_extracted")
            self.assertEqual(result["claims"][0]["existing_status_unchanged"], "unverified")


if __name__ == "__main__":
    unittest.main()
