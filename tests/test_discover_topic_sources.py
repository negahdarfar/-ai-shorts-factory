import unittest
from scripts.discover_topic_sources import secure_url


class TopicSourceDiscoveryTests(unittest.TestCase):
    def test_only_credential_free_https_urls_are_accepted(self):
        self.assertEqual(secure_url("https://example.org/article"), "https://example.org/article")
        self.assertEqual(secure_url("http://example.org/article"), "")
        self.assertEqual(secure_url("https://user:pass@example.org/article"), "")
        self.assertEqual(secure_url("javascript:alert(1)"), "")


if __name__ == "__main__":
    unittest.main()
