import unittest
from scripts.generate_longform_plan import build_prompt, confirmed_claims, validate_plan


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.dossier = {
            "topic": "Sample documentary",
            "sources": [
                {"id": "S1", "url": "https://one.example.org/a"},
                {"id": "S2", "url": "https://two.example.org/b"},
                {"id": "S3", "url": "https://three.example.org/c"}],
            "claims": [
                {"id": "C1", "claim": "Verified fact one.", "status": "confirmed", "source_ids": ["S1", "S2"]},
                {"id": "C2", "claim": "Verified fact two.", "status": "confirmed", "source_ids": ["S2", "S3"]},
                {"id": "C4", "claim": "Verified fact three.", "status": "confirmed", "source_ids": ["S1", "S3"]},
                {"id": "C3", "claim": "Unverified fact.", "status": "unverified", "source_ids": ["S1", "S2"]}]}

    def plan(self, chapters=6):
        narration = " ".join(["Carefully sourced evidence explains this important historical development."] * 25)
        return {"title": "Sample title", "logline": "A careful story.", "chapters": [
            {"id": f"CH{i}", "title": f"Chapter {i}", "narration": narration,
             "claim_ids": ["C1", "C2"], "scenes": [
                 {"visual_query": "archival laboratory research interior", "media_type": "image", "duration_seconds": 8},
                 {"visual_query": "documentary field research footage", "media_type": "video", "duration_seconds": 10}]}
            for i in range(chapters)]}

    def test_only_confirmed_claims_with_two_domains(self):
        self.assertEqual({x["id"] for x in confirmed_claims(self.dossier)}, {"C1", "C2", "C4"})

    def test_prompt_excludes_unverified_claim(self):
        prompt = build_prompt(self.dossier, 480)
        self.assertIn("Verified fact one.", prompt)
        self.assertNotIn("Unverified fact.", prompt)

    def test_valid_plan_and_review_flag(self):
        result = validate_plan(self.plan(), self.dossier, 480)
        self.assertGreaterEqual(result["narration_word_count"], 960)
        self.assertIn("REQUIRES_SOURCE_AND_EDITORIAL_REVIEW", result["editorial_status"])

    def test_rejects_unknown_claim_ids(self):
        candidate = self.plan()
        candidate["chapters"][0]["claim_ids"] = ["C999"]
        with self.assertRaisesRegex(ValueError, "unapproved claim IDs"):
            validate_plan(candidate, self.dossier, 480)

    def test_rejects_too_few_chapters(self):
        with self.assertRaisesRegex(ValueError, "5-30"):
            validate_plan(self.plan(4), self.dossier, 480)


if __name__ == "__main__":
    unittest.main()
