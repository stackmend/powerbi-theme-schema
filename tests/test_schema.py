import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pbitheme.schema import ROOT, check_schema, errors_for, load_live, load_local, version_key
from pbitheme.server import validate_theme
from pbitheme.sync import sync


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata, cls.schema = load_local()
        cls.raw = (ROOT / cls.metadata["archive_path"]).read_bytes()

    def test_numeric_versions(self):
        self.assertGreater(version_key("reportThemeSchema-2.159.json"), version_key("reportThemeSchema-2.99.json"))

    def test_real_examples_and_negative_cases(self):
        for path in (ROOT / "examples").glob("*.json"):
            self.assertEqual(errors_for(self.schema, json.loads(path.read_text())), [])
        for bad in ({}, {"name": "Bad", "invented": True}, {"name": "Bad", "dataColors": "blue"}):
            self.assertTrue(errors_for(self.schema, bad))
        chart = json.loads((ROOT / "examples/chart-defaults.json").read_text())
        chart["visualStyles"]["clusteredColumnChart"]["*"]["legend"][0]["position"] = "SomewhereImaginary"
        self.assertTrue(errors_for(self.schema, chart))

    def test_missing_ref_rejected(self):
        schema = copy.deepcopy(self.schema)
        schema["properties"]["name"] = {"$ref": "#/definitions/does-not-exist"}
        with self.assertRaises(KeyError):
            check_schema(json.dumps(schema))

    def test_fallback_is_explicit(self):
        with patch("pbitheme.schema.fetch", side_effect=OSError("offline")):
            metadata, _, status = load_live()
        self.assertTrue(status["fallback"])
        self.assertEqual(metadata["sha256"], self.metadata["sha256"])

    def test_live_discovery_and_source_restriction(self):
        with patch("pbitheme.schema.fetch", side_effect=[json.dumps(self.metadata).encode(), self.raw]):
            _, _, status = load_live()
        self.assertFalse(status["fallback"])
        bad = {**self.metadata, "upstream_url": "https://example.com/not-microsoft.json"}
        with patch("pbitheme.schema.fetch", side_effect=[json.dumps(bad).encode(), self.raw]) as get:
            _, _, status = load_live()
        self.assertTrue(status["fallback"])
        self.assertEqual(get.call_args.args[0], self.metadata["upstream_url"])

    def test_validation_provenance_and_selection(self):
        digest = self.metadata["sha256"]
        self.assertFalse(validate_theme(digest, {"name": "Needs provenance"})["valid"])
        self.assertTrue(validate_theme(digest, {"name": "Valid", "$schema": self.metadata["upstream_url"]})["valid"])
        with self.assertRaises(ValueError):
            validate_theme("stale", {"name": "Stale"})

    def fake_upstream(self, raw=None, version="2.159"):
        raw = self.raw if raw is None else raw
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        def get(url):
            if "/commits/" in url:
                return json.dumps({"sha": "a" * 40}).encode()
            if "/contents/" in url:
                return json.dumps([{"name": f"reportThemeSchema-{version}.json", "sha": blob, "type": "file"}]).encode()
            if url.endswith(".json"):
                return raw
            return b"Official text fixture"
        return get

    def test_sync_noop_and_failure_preserve_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(sync(root, self.fake_upstream())["changed"])
            before = (root / "latest.json").read_bytes()
            self.assertFalse(sync(root, self.fake_upstream())["changed"])
            self.assertEqual((root / "latest.json").read_bytes(), before)
            with self.assertRaises(Exception):
                sync(root, self.fake_upstream(b"not json", "2.160"))
            self.assertEqual((root / "latest.json").read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "archived version changed"):
                sync(root, self.fake_upstream(self.raw + b"\n"))
            self.assertEqual((root / "latest.json").read_bytes(), before)

    def test_downgrade_and_checksum_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync(root, self.fake_upstream())
            with self.assertRaisesRegex(ValueError, "downgrade"):
                sync(root, self.fake_upstream(version="2.158"))
            path = root / "schemas/reportThemeSchema-2.159.json"
            path.write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_local(root)


if __name__ == "__main__":
    unittest.main()
