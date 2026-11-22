import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_rights_ledger import RightsError, validate_rights_ledger


class RightsLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "clips.json"
        self.ledger = self.root / "rights.json"
        self.manifest.write_text(json.dumps(["assets/clip-a.mp4"]), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write_ledger(self, rows):
        self.ledger.write_text(json.dumps(rows), encoding="utf-8")

    def valid_entry(self, **changes):
        row = {
            "asset": "assets/clip-a.mp4",
            "source_url": "https://example.org/source",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "attribution": "Creator Name / source title",
        }
        row.update(changes)
        return row

    def test_accepts_complete_cc_by_record(self):
        self.write_ledger([self.valid_entry()])
        result = validate_rights_ledger(self.manifest, self.ledger)
        self.assertEqual(result["rights_gate"], "passed")
        self.assertEqual(result["assets_checked"], 1)

    def test_rejects_missing_asset_record(self):
        self.write_ledger([])
        with self.assertRaisesRegex(RightsError, "Missing rights records"):
            validate_rights_ledger(self.manifest, self.ledger)

    def test_rejects_noncommercial_or_unknown_license(self):
        self.write_ledger([self.valid_entry(license="CC BY-NC 4.0")])
        with self.assertRaisesRegex(RightsError, "Unsupported or unclear license"):
            validate_rights_ledger(self.manifest, self.ledger)

    def test_rejects_missing_attribution(self):
        self.write_ledger([self.valid_entry(attribution="")])
        with self.assertRaisesRegex(RightsError, "requires attribution"):
            validate_rights_ledger(self.manifest, self.ledger)

    def test_cc_by_sa_requires_share_alike_confirmation(self):
        self.write_ledger([self.valid_entry(license="CC BY-SA 4.0")])
        with self.assertRaisesRegex(RightsError, "ShareAlike"):
            validate_rights_ledger(self.manifest, self.ledger)

    def test_owned_asset_requires_rights_holder(self):
        self.write_ledger([self.valid_entry(license="owned")])
        with self.assertRaisesRegex(RightsError, "rights_holder"):
            validate_rights_ledger(self.manifest, self.ledger)

    def test_rejects_http_source_url(self):
        self.write_ledger([self.valid_entry(source_url="http://example.org/source")])
        with self.assertRaisesRegex(RightsError, "HTTPS source_url"):
            validate_rights_ledger(self.manifest, self.ledger)


if __name__ == "__main__":
    unittest.main()
