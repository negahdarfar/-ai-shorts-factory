import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "visual_uniqueness", ROOT / "scripts" / "validate_visual_uniqueness.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VisualUniquenessTests(unittest.TestCase):
    def test_identical_hashes_have_zero_distance(self):
        self.assertEqual(MODULE.hamming_distance(0x1234567890ABCDEF, 0x1234567890ABCDEF), 0)

    def test_one_bit_difference_is_detected(self):
        self.assertEqual(MODULE.hamming_distance(0b1010, 0b1011), 1)

    def test_repeated_frames_are_matched_once_each(self):
        left = [0b0000, 0b1111, 0b1010]
        right = [0b0001, 0b1110, 0b0101]
        matches = MODULE.matched_frame_pairs(left, right, 1)
        self.assertEqual(len(matches), 2)
        self.assertEqual(len({row["left_frame"] for row in matches}), 2)
        self.assertEqual(len({row["right_frame"] for row in matches}), 2)

    def test_different_frames_do_not_match(self):
        matches = MODULE.matched_frame_pairs([0], [255], 5)
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
