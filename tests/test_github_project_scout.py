import unittest
from scripts.github_project_scout import normalize, score

class GitHubProjectScoutTests(unittest.TestCase):
    def test_normalize_handles_missing_metadata(self):
        item = normalize({"full_name": "owner/project", "stargazers_count": 1200}, "video")
        self.assertEqual(item["name"], "owner/project")
        self.assertEqual(item["license"], "UNKNOWN")
        self.assertFalse(item["archived"])

    def test_archived_project_is_penalized(self):
        active = {"stars": 10000, "license": "MIT", "pushed_at": "2026-01-01", "archived": False, "fork": False}
        archived = dict(active, archived=True)
        self.assertGreater(score(active), score(archived))

    def test_license_adds_confidence_points(self):
        known = {"stars": 1000, "license": "MIT", "pushed_at": "", "archived": False, "fork": False}
        unknown = dict(known, license="UNKNOWN")
        self.assertGreater(score(known), score(unknown))

if __name__ == "__main__":
    unittest.main()
