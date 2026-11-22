import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scripts.collect_research_sources import FeedError, collect, parse_feed
RSS=b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>New NASA Mars mission discovery</title><link>https://nasa.gov/story</link><description>Mars research</description><pubDate>Sun, 22 Nov 2026 10:00:00 GMT</pubDate></item>
<item><title>Unrelated cooking news</title><link>https://food.example/news</link></item>
<item><title>Unsafe link</title><link>http://bad.example/story</link></item></channel></rss>"""
class ResearchFeedTests(unittest.TestCase):
    def test_topic_filter_https_and_date(self):
        rows=parse_feed(RSS,"https://nasa.gov/rss.xml","NASA","Mars mission")
        self.assertEqual(len(rows),1); self.assertEqual(rows[0]["url"],"https://nasa.gov/story")
        self.assertTrue(rows[0]["discovery_only"]); self.assertEqual(rows[0]["published_at"],"2026-11-22")
    def test_rejects_non_https_feed(self):
        from scripts.collect_research_sources import safe_feed_url
        with self.assertRaises(FeedError): safe_feed_url("http://example.org/rss")
    def test_empty_config_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/"feeds.json"; out=root/"out.json"
            cfg.write_text(json.dumps({"feeds":[]}),encoding="utf-8")
            result=collect(cfg,"Mars",out); self.assertEqual(result["candidate_count"],0); self.assertTrue(out.is_file())
    def test_collects_candidate(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,size): return RSS
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/"feeds.json"
            cfg.write_text(json.dumps({"feeds":[{"url":"https://nasa.gov/rss.xml","publisher":"NASA"}]}),encoding="utf-8")
            with patch("scripts.collect_research_sources.urllib.request.urlopen",return_value=Response()):
                result=collect(cfg,"Mars",root/"out.json")
            self.assertEqual(result["candidate_count"],1)
    def test_adds_curated_sources_even_when_feed_list_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/"feeds.json"; research=root/"research.json"; out=root/"out.json"
            cfg.write_text(json.dumps({"feeds":[]}),encoding="utf-8")
            research.write_text(json.dumps({"sources":[
                {"id":"S1","title":"Primary study","publisher":"Lab","url":"https://lab.example/study","published_at":"2026-01-01"},
                {"id":"S2","title":"Official data","publisher":"Agency","url":"https://agency.example/data"}
            ]}),encoding="utf-8")
            result=collect(cfg,"climate",out,research_input=research)
            self.assertEqual(result["curated_source_count"],2)
            self.assertEqual({x["source_id"] for x in result["candidates"]},{"S1","S2"})
            self.assertEqual(result["candidate_count"],2)

    def test_curated_source_requires_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/"feeds.json"; research=root/"research.json"
            cfg.write_text(json.dumps({"feeds":[]}),encoding="utf-8")
            research.write_text(json.dumps({"sources":[{"id":"S1","url":"http://bad.example/a"}]}),encoding="utf-8")
            result=collect(cfg,"topic",root/"out.json",research_input=research)
            self.assertEqual(result["candidate_count"],0)
            self.assertTrue(result["feed_errors"])

    def test_invalid_xml(self):
        with self.assertRaises(FeedError): parse_feed(b"<broken","https://example.org/rss","Example","topic")
if __name__=="__main__": unittest.main()
