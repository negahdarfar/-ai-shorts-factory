import unittest

from cli import allowed_license, score, select


class ViralFactoryTests(unittest.TestCase):
    def test_allowed_creative_commons_licenses(self):
        self.assertTrue(allowed_license("CC0"))
        self.assertTrue(allowed_license("CC BY 4.0"))
        self.assertFalse(allowed_license("CC BY-SA 4.0"))
        self.assertTrue(allowed_license("Public domain"))

    def test_restricted_licenses_are_rejected(self):
        self.assertFalse(allowed_license("CC BY-NC 4.0"))
        self.assertFalse(allowed_license("CC BY-ND 4.0"))

    def test_hook_score_rewards_question_and_hook(self):
        self.assertGreater(score("Why is this amazing discovery so surprising?"), score("A quiet landscape video"))

    def test_clip_selection_returns_non_overlapping_windows(self):
        transcript = [
            {"start": 0, "end": 12, "text": "Why is this discovery amazing?"},
            {"start": 12, "end": 25, "text": "The surprising result changed everything."},
            {"start": 60, "end": 72, "text": "Here is another incredible discovery!"},
            {"start": 72, "end": 88, "text": "This is the reason why it matters."},
        ]
        clips = select(transcript, 100, 3)
        self.assertTrue(clips)
        for i, left in enumerate(clips):
            for right in clips[i + 1:]:
                self.assertTrue(left["end"] <= right["start"] or right["end"] <= left["start"])


if __name__ == "__main__":
    unittest.main()
