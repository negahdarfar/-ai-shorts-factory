import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from validate_documentary import inspect_documentary, parse_srt
class DocumentaryQualityTests(unittest.TestCase):
    def test_persian_srt_requires_ordered_nonempty_cues(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"captions.srt"; p.write_text("1\n00:00:00,000 --> 00:00:02,000\nسلام دنیا\n\n2\n00:00:02,100 --> 00:00:04,000\nخوش آمدید\n\n3\n00:00:04,100 --> 00:00:06,000\nاین یک آزمایش است\n",encoding="utf-8")
            self.assertEqual(len(parse_srt(p)),3)
    def test_rejects_english_only_subtitles(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"captions.srt"; p.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,100 --> 00:00:04,000\nWorld\n\n3\n00:00:04,100 --> 00:00:06,000\nAgain\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Persian-script"): parse_srt(p)
    def test_rejects_missing_audio(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"doc.mp4"; p.write_bytes(b"x"*600000)
            payload={"streams":[{"codec_type":"video","width":1920,"height":1080}],"format":{"duration":"700"}}
            class R: stdout=json.dumps(payload)
            with patch("validate_documentary.subprocess.run",return_value=R()):
                with self.assertRaisesRegex(ValueError,"both video and audio"): inspect_documentary(p,600)
    def test_accepts_valid_landscape_documentary(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"doc.mp4"; p.write_bytes(b"x"*600000)
            payload={"streams":[{"codec_type":"video","width":1920,"height":1080,"codec_name":"h264"},{"codec_type":"audio","codec_name":"aac"}],"format":{"duration":"620"}}
            class R: stdout=json.dumps(payload)
            with patch("validate_documentary.subprocess.run",return_value=R()): report=inspect_documentary(p,600)
            self.assertEqual(report["status"],"passed"); self.assertEqual(report["resolution"],"1920x1080")
if __name__=="__main__": unittest.main()
