import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class SeoPipelineTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        data=[{"topic":"Solar storms","metadata_source":"gemini_batch","content_source":"gemini_batch","video_script":"Solar storms begin with activity on the Sun. Powerful magnetic fields can twist and reconnect, releasing energy and sometimes sending charged particles toward Earth. When those particles interact with Earth’s magnetic field, they can create auroras and, in stronger events, disrupt satellites or radio communications. Scientists monitor solar activity to understand these risks and improve forecasts. The key point is that solar storms are natural space-weather events, but their effects depend on their strength and direction.","video_terms":["solar storms","solar flare","Sun surface","space weather","solar activity"],"metadata":{"title":"Solar Storms: What Happens When the Sun Erupts?","description":"Learn how solar storms form, how solar flares affect Earth, and why space weather matters.","primary_keyword":"solar storms","tags":["solar storms","space weather","solar flare","Sun activity","Earth magnetosphere"],"hashtags":["space","science"]}}]
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

    def test_generator_uses_one_gemini_request_for_four_topics(self):
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("seo_generator", ROOT / "scripts/generate_seo_metadata.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fields = {
            "primary_keyword":"solar storms","secondary_keywords":["space weather"],
            "title":"Solar storms explained","description":"Learn about solar storms.",
            "hashtags":["space"],"tags":["space","science"],
            "pinned_comment":"What do you think?","thumbnail_concept":"The Sun releasing a flare",
            "search_intent":"Understand solar storms"
        }
        response_data = {"candidates":[{"content":{"parts":[{"text":json.dumps({
            "items":[{"index":i,"metadata":dict(fields),"video_script":"This is a clear narrated explanation of the topic. It introduces the main question, explains why context matters, and shows viewers how to separate evidence from assumptions. It avoids unsupported claims and ends with a practical takeaway for understanding the subject more carefully. The goal is not to rush to a conclusion. It is to understand the subject using clear language and reliable context.","video_terms":["solar storms","solar flare","Sun surface","space weather","solar activity"]} for i in range(1,5)]
        })}]}}]}
        mocked = patch("urllib.request.urlopen")
        with mocked as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(response_data).encode()
            result = module.generate_batch(["Topic 1","Topic 2","Topic 3","Topic 4"],"English","gemini-test","test-key")
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(len(result), 4)

    def test_quota_fallback_is_blocked_before_publish(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "topics.json"
            output = root / "seo.json"
            source.write_text(json.dumps([
                {"video_subject": f"Topic {i}"} for i in range(1,5)
            ]), encoding="utf-8")
            env = os.environ.copy()
            env.pop("GEMINI_API_KEY", None)
            result = subprocess.run(
                [sys.executable, str(ROOT/"scripts/generate_seo_metadata.py"),
                 "--input", str(source), "--output", str(output)],
                capture_output=True, text=True, env=env
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            records = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(records), 4)
            self.assertTrue(all(x["metadata_source"] == "local_template_fallback" for x in records))
            validation = subprocess.run(
                [sys.executable, str(ROOT/"scripts/validate_seo_metadata.py"),
                 "--input", str(output), "--expected-count", "4"],
                capture_output=True, text=True
            )
            self.assertNotEqual(validation.returncode, 0, "Fallback content must never pass public-publishing validation.")
            self.assertIn("AI content was not generated", validation.stderr)


    def test_batch_runner_injects_prebuilt_script_and_terms(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mpt_runner", ROOT / "scripts/run_mpt_batch_with_retry.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            records = [{
                "topic": "Solar storms",
                "video_script": "This is a clear narrated explanation of the topic. It introduces the main question, explains why context matters, and shows viewers how to separate evidence from assumptions. It avoids unsupported claims and ends with a practical takeaway for understanding the subject more carefully. The goal is not to rush to a conclusion. It is to understand the subject using clear language and reliable context.",
                "video_terms": ["solar storms", "solar flare", "Sun surface", "space weather", "solar activity"],
                "content_source": "gemini_batch"
            }]
            manifest = root / "seo_metadata.json"
            manifest.write_text(json.dumps(records), encoding="utf-8")
            batch = [{"video_subject": "Solar storms", "video_language": "en-US"}]
            result = module.attach_prebuilt_content(batch, manifest)
            self.assertEqual(result[0]["video_script"], records[0]["video_script"])
            self.assertEqual(result[0]["video_terms"], records[0]["video_terms"])

    def test_chapter_validator_accepts_ordered_chapters(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"chapters.txt"; f.write_text("00:00 Opening\n02:10 Background\n05:30 Conclusion\n",encoding="utf-8")
            result=subprocess.run([sys.executable,str(ROOT/"scripts/validate_chapters.py"),str(f)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_generator_aligns_primary_keyword_with_description(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("seo_generator_keyword", ROOT / "scripts/generate_seo_metadata.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        metadata = {
            "primary_keyword": "ancient desert cities",
            "secondary_keywords": ["history"],
            "title": "A forgotten civilization",
            "description": "Discover a remarkable place and its past.",
            "hashtags": ["history"], "tags": ["history"],
            "pinned_comment": "What surprised you?",
            "thumbnail_concept": "An ancient city",
            "search_intent": "Learn about ancient places"
        }
        row = {
            "metadata": metadata,
            "video_script": "This is a clear narrated explanation of the topic. It introduces the main question, explains why context matters, and shows viewers how to separate evidence from assumptions. It avoids unsupported claims and ends with a practical takeaway for understanding the subject more carefully. The goal is not to rush to a conclusion. It is to understand the subject using clear language and reliable context.",
            "video_terms": ["ancient city", "desert ruins", "stone walls", "archaeology site", "historic settlement"]
        }
        normalized = module.normalize_item(row, "Ancient desert cities")
        self.assertIn("ancient desert cities", normalized["metadata"]["description"].casefold())




    def test_visual_search_terms_must_be_distinct_between_videos(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mpt_runner_visuals", ROOT / "scripts/run_mpt_batch_with_retry.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        batch = [
            {"video_subject": "Topic A", "video_terms": ["desert summer climate", "Las Vegas skyline", "monsoon rain storm", "Mojave desert landscape", "weather forecast map"]},
            {"video_subject": "Topic B", "video_terms": ["ballet rehearsal studio", "Australian actress portrait", "film camera closeup", "red carpet event", "theatre stage lighting"]},
            {"video_subject": "Topic C", "video_terms": ["ceramic ocarina instrument", "retro game controller", "three dimensional game design", "pixel art landscape", "video game history"]},
            {"video_subject": "Topic D", "video_terms": ["professional tennis court", "tennis serve practice", "Danish flag stadium", "tennis racket closeup", "hard court tournament"]},
        ]
        module.validate_distinct_visual_terms(batch)
        batch[1]["video_terms"] = list(batch[0]["video_terms"])
        with self.assertRaises(SystemExit):
            module.validate_distinct_visual_terms(batch)

if __name__ == "__main__":
    unittest.main()
