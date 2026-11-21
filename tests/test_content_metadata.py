import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_metadata import classify_hook, extract_hook


class ContentMetadataTests(unittest.TestCase):
    def test_extracts_first_sentence_only(self):
        hook = extract_hook("Why do stars twinkle? The atmosphere bends their light.")
        self.assertEqual(hook, "Why do stars twinkle?")

    def test_classifies_question_hook(self):
        self.assertEqual(classify_hook("Why do stars twinkle?"), "question")

    def test_classifies_scenario_hook(self):
        self.assertEqual(classify_hook("Imagine standing on Mars."), "scenario")

    def test_classifies_contrarian_hook(self):
        self.assertEqual(classify_hook("Most people think deserts are lifeless."), "contrarian")

    def test_classifies_number_hook(self):
        self.assertEqual(classify_hook("Three facts explain the mystery."), "number_or_fact")

    def test_classifies_default_curiosity_hook(self):
        self.assertEqual(classify_hook("A hidden detail changed everything."), "curiosity")


if __name__ == "__main__":
    unittest.main()
