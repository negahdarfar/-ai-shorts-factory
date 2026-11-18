import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_avgen_batch import build_jobs


def sample_record(index, source="multi_provider_individual", words=125):
    script = " ".join(
        f"Sentence {number} explains the subject with useful context and clear evidence."
        for number in range(words // 10)
    )
    # Adjust to a deterministic valid word count.
    tokens = script.split()
    script = " ".join((tokens + ["context"] * words)[:words])
    return {
        "topic": f"Topic {index}",
        "content_source": source,
        "metadata": {"title": f"Documentary title {index}"},
        "video_script": script,
        "video_terms": [
            "historic archive", "scientific laboratory", "city skyline",
            "research documents", "field investigation",
        ],
    }


class ExportAvgenBatchTests(unittest.TestCase):
    def test_exports_four_vertical_jobs_and_preserves_spoken_words(self):
        records = [sample_record(i) for i in range(1, 5)]
        jobs = build_jobs(records)
        self.assertEqual(len(jobs), 4)
        self.assertTrue(all(job["orientation"] == "portrait" for job in jobs))
        self.assertTrue(all(job["language"] == "english" for job in jobs))
        for source, job in zip(records, jobs):
            spoken = " ".join(
                line for line in job["script"].splitlines()
                if not line.startswith("[Visual:")
            )
            self.assertEqual(spoken.split(), source["video_script"].split())
            self.assertIn("[Visual:", job["script"])

    def test_rejects_local_template_fallback(self):
        records = [sample_record(i) for i in range(1, 5)]
        records[2]["content_source"] = "local_template_fallback"
        with self.assertRaisesRegex(ValueError, "not approved AI content"):
            build_jobs(records)

    def test_rejects_missing_source_and_out_of_range_script(self):
        records = [sample_record(i) for i in range(1, 5)]
        records[0]["content_source"] = ""
        with self.assertRaisesRegex(ValueError, "not approved AI content"):
            build_jobs(records)
        records = [sample_record(i) for i in range(1, 5)]
        records[0]["video_script"] = "too short"
        with self.assertRaisesRegex(ValueError, "120-145 words"):
            build_jobs(records)

    def test_rejects_duplicate_topics_and_insufficient_visual_terms(self):
        records = [sample_record(i) for i in range(1, 5)]
        records[1]["topic"] = records[0]["topic"]
        with self.assertRaisesRegex(ValueError, "Duplicate topic"):
            build_jobs(records)
        records = [sample_record(i) for i in range(1, 5)]
        records[0]["video_terms"] = ["only one"]
        with self.assertRaisesRegex(ValueError, "5-8 distinct"):
            build_jobs(records)

    def test_requires_exact_batch_size(self):
        with self.assertRaisesRegex(ValueError, "exactly 4"):
            build_jobs([sample_record(1)])


if __name__ == "__main__":
    unittest.main()
