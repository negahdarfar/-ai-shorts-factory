import unittest
from scripts.api_intelligence import parse_catalogue, rank_entry, public_https_url

class ApiIntelligenceTests(unittest.TestCase):
    def test_parse_category_table(self):
        markdown = """
### Cryptocurrency
| API | Description | Auth | HTTPS | CORS |
|---|---|---|---|---|
| [CoinCap](https://docs.example.org) | Market data | No | Yes | Yes |
### Animals
| [Cat Facts](https://cats.example.org) | Facts | No | Yes | Yes |
"""
        rows = parse_catalogue(markdown)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "CoinCap")
        self.assertEqual(rows[0]["category"], "Cryptocurrency")
        self.assertEqual(rows[1]["category"], "Animals")

    def test_free_https_priority_scores_higher(self):
        free = {"category": "Blockchain", "auth": "No", "https": "yes", "cors": "yes"}
        keyed = {"category": "Blockchain", "auth": "apiKey", "https": "yes", "cors": "yes"}
        self.assertGreater(rank_entry(free), rank_entry(keyed))

    def test_non_https_is_rejected_without_network(self):
        allowed, reason = public_https_url("http://example.org")
        self.assertFalse(allowed)
        self.assertEqual(reason, "HTTPS URL required")

    def test_localhost_is_rejected_without_network(self):
        allowed, reason = public_https_url("https://localhost")
        self.assertFalse(allowed)
        self.assertEqual(reason, "local host blocked")

if __name__ == "__main__":
    unittest.main()
