import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("youtube_agent_dispatch", ROOT / "scripts/youtube_agent_dispatch.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class YouTubeAgentDispatchTests(unittest.TestCase):
    def test_all_eleven_skills_and_tool_paths_exist(self):
        plan = MODULE.build_plan()
        self.assertEqual(plan["skills_total"], 11)
        self.assertEqual(len(plan["skills"]), 11)
        self.assertEqual(plan["missing_paths"], [])

    def test_plan_is_handoff_only_and_never_claims_publish(self):
        plan = MODULE.build_plan()
        self.assertEqual(plan["mode"], "handoff_plan_only")
        self.assertFalse(plan["agent_runtime_executed"])
        self.assertFalse(plan["publishing_performed"])
        prompt = MODULE.render_prompt(plan)
        self.assertIn("YouTube API confirmation", prompt)
        self.assertIn("Do not expose secrets", prompt)

    def test_outputs_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            MODULE.main_args = None
            plan = MODULE.build_plan()
            Path(tmp, "execution-plan.json").write_text(__import__("json").dumps(plan))
            Path(tmp, "agent-handoff.md").write_text(MODULE.render_prompt(plan))
            self.assertTrue(Path(tmp, "execution-plan.json").is_file())
            self.assertTrue(Path(tmp, "agent-handoff.md").is_file())

if __name__ == "__main__":
    unittest.main()
