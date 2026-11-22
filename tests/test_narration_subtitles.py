import unittest
from scripts.generate_narration_audio import split_cues, srt_timestamp
from scripts.translate_subtitles_free import parse_srt


class NarrationSubtitleTests(unittest.TestCase):
    def test_sentence_cues_are_split_into_readable_chunks(self):
        rows = split_cues("This is a short sentence. " + " ".join(["word"] * 30))
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(all(len(row.split()) <= 13 for row in rows))

    def test_timestamp_format(self):
        self.assertEqual(srt_timestamp(3661.234), "01:01:01,234")

    def test_parse_srt_preserves_cue_numbers_and_times(self):
        rows = parse_srt("1\n00:00:00,000 --> 00:00:02,500\nHello world.\n\n2\n00:00:02,500 --> 00:00:04,000\nSecond line.")
        self.assertEqual([row["index"] for row in rows], [1, 2])
        self.assertEqual(rows[1]["time"], "00:00:02,500 --> 00:00:04,000")

    def test_rejects_malformed_srt(self):
        with self.assertRaises(ValueError):
            parse_srt("not an srt")


if __name__ == "__main__":
    unittest.main()
