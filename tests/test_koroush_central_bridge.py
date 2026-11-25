from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "koroush_central_bridge.py"
SPEC = importlib.util.spec_from_file_location("koroush_central_bridge", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class EvidenceContractTests(unittest.TestCase):
    def test_accepts_valid_evidence_array(self):
        rows = bridge.load_evidence(None, '[{"source_id":"s1","text":"source text"}]')
        self.assertEqual(rows[0]["source_id"], "s1")

    def test_rejects_duplicate_source_ids(self):
        raw = '[{"source_id":"s1","text":"one"},{"source_id":"s1","text":"two"}]'
        with self.assertRaisesRegex(ValueError, "unique"):
            bridge.load_evidence(None, raw)

    def test_rejects_more_than_eight_items(self):
        raw = [{"source_id": f"s{i}", "text": "x"} for i in range(9)]
        import json
        with self.assertRaisesRegex(ValueError, "1 to 8"):
            bridge.load_evidence(None, json.dumps(raw))

    def test_rejects_oversized_combined_evidence(self):
        raw = [{"source_id": f"s{i}", "text": "x" * 5000} for i in range(5)]
        import json
        with self.assertRaisesRegex(ValueError, "20,000"):
            bridge.load_evidence(None, json.dumps(raw))

    def test_rejects_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            bridge.load_evidence(None, '[{"source_id":"s1","text":"x","command":"run"}]')


class DiscoveryTests(unittest.TestCase):
    @patch.object(bridge, "request_json")
    def test_resolves_builtin_youtube_profile(self, request):
        request.side_effect = [
            {"version": 1},
            {"integrations": [{"id": "koroush.youtube", "status": "enabled-research"}], "registered_connectors": []},
        ]
        route, profile = bridge.resolve_integration("https://central.example", {}, "youtube")
        self.assertEqual(route, "youtube")
        self.assertEqual(profile["id"], "koroush.youtube")

    @patch.object(bridge, "request_json")
    def test_discovers_new_registered_connector_without_code_change(self, request):
        request.side_effect = [
            {"version": 1},
            {"integrations": [], "registered_connectors": [{
                "id": "koroush.video-research", "status": "active",
                "domains": ["general"], "capabilities": ["research.workflow.v1"],
            }]},
        ]
        route, profile = bridge.resolve_integration("https://central.example", {}, "koroush.video-research")
        self.assertEqual(route, "koroush.video-research")
        self.assertEqual(profile["status"], "active")

    @patch.object(bridge, "request_json")
    def test_rejects_inactive_or_incompatible_connector(self, request):
        request.side_effect = [
            {"version": 1},
            {"integrations": [], "registered_connectors": [{
                "id": "koroush.video-research", "status": "inactive",
                "domains": ["general"], "capabilities": ["research.workflow.v1"],
            }]},
        ]
        with self.assertRaisesRegex(RuntimeError, "not active/compatible"):
            bridge.resolve_integration("https://central.example", {}, "koroush.video-research")


if __name__ == "__main__":
    unittest.main()
