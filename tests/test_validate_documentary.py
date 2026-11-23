import tempfile
import unittest
from pathlib import Path

from scripts.validate_documentary import parse_srt


def write_srt(text):
    tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".srt", delete=False)
    tmp.write(text)
    tmp.close()
    return Path(tmp.name)


VALID = """1
00:00:00,000 --> 00:00:01,000
سلام

2
00:00:01,100 --> 00:00:02,000
این یک آزمون است

3
00:00:02,100 --> 00:00:03,000
زیرنویس فارسی
"""


class DocumentarySrtTests(unittest.TestCase):
    def parse_text(self, text):
        path = write_srt(text)
        try:
            return parse_srt(path)
        finally:
            path.unlink(missing_ok=True)

    def test_accepts_ordered_persian_srt(self):
        cues = self.parse_text(VALID)
        self.assertEqual(len(cues), 3)
        self.assertEqual(cues[0]["start_ms"], 0)

    def test_rejects_minute_overflow(self):
        text = VALID.replace("00:00:01,000", "00:75:01,000", 1)
        with self.assertRaisesRegex(ValueError, "minutes and seconds"):
            self.parse_text(text)

    def test_rejects_second_overflow(self):
        text = VALID.replace("00:00:01,000", "00:00:90,000", 1)
        with self.assertRaisesRegex(ValueError, "minutes and seconds"):
            self.parse_text(text)

    def test_rejects_overlapping_cues(self):
        text = VALID.replace("00:00:01,100 --> 00:00:02,000",
                             "00:00:00,900 --> 00:00:02,000")
        with self.assertRaisesRegex(ValueError, "ordered without overlap"):
            self.parse_text(text)

    def test_rejects_non_persian_caption(self):
        text = VALID.replace("سلام", "Hello")
        with self.assertRaisesRegex(ValueError, "Persian-script"):
            self.parse_text(text)

    def test_requires_at_least_three_cues(self):
        text = VALID.split("\n\n2\n")[0]
        with self.assertRaisesRegex(ValueError, "At least three"):
            self.parse_text(text)


if __name__ == "__main__":
    unittest.main()
