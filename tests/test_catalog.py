import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "android-tv-apps-helper"
sys.path.insert(0, str(PLUGIN / "scripts"))

from tv_helper.catalog import CatalogError, eligible_downloads, load_catalog, validate_catalog


class CatalogTests(unittest.TestCase):
    def test_official_direct_requires_publisher_source_and_allowlist(self):
        catalog = {
            "schema_version": 1,
            "apps": [
                {
                    "id": "dangbei-market",
                    "name": "当贝市场",
                    "version": "6.0.7",
                    "distribution": {
                        "mode": "official_direct",
                        "publisher_page": "https://www.dangbei.com/",
                        "resolved_url": "https://app.qingyingyong.net/file.apk",
                        "allowed_hosts": ["www.dangbei.com", "app.qingyingyong.net"],
                        "verification_status": "pending_file_identity"
                    },
                    "assets": []
                }
            ]
        }
        validate_catalog(catalog)
        catalog["apps"][0]["distribution"]["allowed_hosts"] = ["www.dangbei.com"]
        with self.assertRaises(CatalogError):
            validate_catalog(catalog)
    def setUp(self):
        self.catalog_path = PLUGIN / "catalog" / "apps.json"

    def test_repository_catalog_is_valid_and_pending_items_have_no_url(self):
        catalog = load_catalog(self.catalog_path)
        validate_catalog(catalog)
        pending = [app for app in catalog["apps"] if app["distribution"]["mode"].startswith("pending_")]
        self.assertGreaterEqual(len(pending), 1)
        self.assertTrue(all(not app["distribution"].get("url") for app in pending))

    def test_clash_meta_must_stay_on_official_release(self):
        catalog = load_catalog(self.catalog_path)
        clash = next(app for app in catalog["apps"] if app["id"] == "clash-meta")
        clash["assets"][0]["url"] = (
            "https://github.com/HXWfromDJTU/android-tv-apps-helper/releases/download/v0.1.0/cmfa.apk"
        )
        with self.assertRaisesRegex(CatalogError, "official"):
            validate_catalog(catalog)

    def test_project_hosted_asset_requires_permission_and_sha256(self):
        catalog = load_catalog(self.catalog_path)
        smarttube = next(app for app in catalog["apps"] if app["id"] == "smarttube")
        broken = copy.deepcopy(catalog)
        target = next(app for app in broken["apps"] if app["id"] == "smarttube")
        target["distribution"].pop("redistribution_evidence")
        with self.assertRaisesRegex(CatalogError, "redistribution"):
            validate_catalog(broken)

        target = copy.deepcopy(smarttube)
        target["assets"][0]["sha256"] = ""
        broken = {"schema_version": 1, "apps": [target]}
        with self.assertRaisesRegex(CatalogError, "sha256"):
            validate_catalog(broken)

    def test_eligible_downloads_exclude_pending_entries(self):
        catalog = load_catalog(self.catalog_path)
        ids = {app["id"] for app in eligible_downloads(catalog)}
        self.assertEqual(ids, {"clash-meta", "smarttube"})


if __name__ == "__main__":
    unittest.main()
