import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scripts.extract_research_pages import ExtractionError, TextExtractor, extract_candidates, validate_public_url

class ResearchPageTests(unittest.TestCase):
    def test_extracts_article_text_and_metadata(self):
        p=TextExtractor()
        p.feed('<html><head><title>Study title</title><meta name="description" content="Summary"></head><body><nav>menu</nav><article><h1>Heading</h1><p>Evidence paragraph.</p><script>secret()</script></article></body></html>')
        r=p.result()
        self.assertEqual(r["page_title"],"Study title")
        self.assertEqual(r["meta_description"],"Summary")
        self.assertIn("Evidence paragraph.",r["extracted_text"])
        self.assertNotIn("secret()",r["extracted_text"])
        self.assertNotIn("menu",r["extracted_text"])
    def test_blocks_non_https(self):
        with self.assertRaises(ExtractionError): validate_public_url("http://example.org")
    def test_blocks_private_dns(self):
        with patch("scripts.extract_research_pages.socket.getaddrinfo",return_value=[(None,None,None,None,("127.0.0.1",0))]):
            with self.assertRaises(ExtractionError): validate_public_url("https://example.org")
    def test_candidate_failure_is_recorded_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/"in.json"; out=root/"out.json"
            src.write_text(json.dumps({"topic":"test","candidates":[{"url":"https://example.org","title":"x"}]}),encoding="utf-8")
            with patch("scripts.extract_research_pages.fetch_page",side_effect=ExtractionError("blocked")):
                result=extract_candidates(src,out)
            self.assertEqual(result["pages"][0]["extraction_status"],"failed")
            self.assertFalse(result["pages"][0]["fact_checked"])
            self.assertTrue(out.is_file())
if __name__=="__main__": unittest.main()
