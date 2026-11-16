import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class SeoPipelineTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        data=[{"topic":"Solar storms","metadata":{"title":"Solar storms explained","description":"Learn about solar storms.","primary_keyword":"solar storms","tags":["space","science"],"hashtags":["space"]}}]
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"seo.json"; f.write_text(json.dumps(data),encoding="utf-8")
            result=subprocess.run([sys.executable,str(ROOT/"scripts/validate_seo_metadata.py"),"--input",str(f),"--expected-count","1"],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_duplicate_topics_fail(self):
        row={"topic":"Solar storms","metadata":{"title":"Solar storms","description":"Solar storms","primary_keyword":"Solar storms","tags":[],"hashtags":[]}}
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"seo.json"; f.write_text(json.dumps([row,row]),encoding="utf-8")
            result=subprocess.run([sys.executable,str(ROOT/"scripts/validate_seo_metadata.py"),"--input",str(f),"--expected-count","2"],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
    def test_chapter_validator_accepts_ordered_chapters(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"chapters.txt"; f.write_text("00:00 Opening\n02:10 Background\n05:30 Conclusion\n",encoding="utf-8")
            result=subprocess.run([sys.executable,str(ROOT/"scripts/validate_chapters.py"),str(f)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
if __name__=="__main__": unittest.main()
