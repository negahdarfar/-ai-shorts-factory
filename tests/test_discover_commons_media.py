import unittest

from scripts.discover_commons_media import clean_html, license_family, media_extension, page_metadata


class CommonsMediaTests(unittest.TestCase):
    def test_accepts_public_domain_cc0_and_cc_by(self):
        self.assertEqual(license_family("Public domain"), "public-domain")
        self.assertEqual(license_family("CC0 1.0"), "public-domain")
        self.assertEqual(license_family("CC BY 4.0"), "cc-by")

    def test_rejects_nc_nd_sharealike_and_unknown(self):
        for value in ("CC BY-NC 4.0", "CC BY-ND 4.0", "CC BY-SA 4.0", "unknown"):
            with self.subTest(value=value):
                self.assertIsNone(license_family(value))

    def test_strips_html_and_decodes_entities(self):
        self.assertEqual(clean_html("<b>Creator</b> &amp; source<br>name"), "Creator & source name")

    def test_detects_supported_media_extensions(self):
        self.assertEqual(media_extension("https://upload.wikimedia.org/a/photo.jpg"), ".jpg")
        self.assertEqual(media_extension("https://upload.wikimedia.org/a/clip.webm"), ".webm")

    def test_rejects_metadata_with_unclear_license(self):
        page = {
            "title": "File:sample.jpg",
            "imageinfo": [{
                "url": "https://upload.wikimedia.org/sample.jpg",
                "extmetadata": {
                    "LicenseShortName": {"value": "CC BY-NC 4.0"},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-nc/4.0/"},
                },
            }],
        }
        self.assertIsNone(page_metadata(page))

    def test_extracts_complete_cc_by_metadata(self):
        page = {
            "title": "File:sample.jpg",
            "imageinfo": [{
                "url": "https://upload.wikimedia.org/sample.jpg",
                "width": 1200,
                "height": 800,
                "extmetadata": {
                    "LicenseShortName": {"value": "CC BY 4.0"},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                    "Artist": {"value": "<a>Jane Doe</a>"},
                },
            }],
        }
        item = page_metadata(page)
        self.assertEqual(item["license_family"], "cc-by")
        self.assertIn("Jane Doe", item["attribution"])
        self.assertTrue(item["source_url"].startswith("https://commons.wikimedia.org/wiki/"))


if __name__ == "__main__":
    unittest.main()
