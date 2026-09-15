import tempfile
import unittest
from pathlib import Path

from tv_helper.guides import match_device_guide, next_finish_state, validate_wallpaper


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.guides = [
            {"id": "generic", "match": {"scope": "generic"}, "steps": ["通用"]},
            {"id": "xiaomi", "match": {"manufacturer": "Xiaomi"}, "steps": ["小米"]},
            {"id": "astp0", "match": {"manufacturer": "Xiaomi", "model": "MiTV-ASTP0"}, "steps": ["型号"]},
            {"id": "astp0-build", "match": {"manufacturer": "Xiaomi", "model": "MiTV-ASTP0", "build_id": "PKQ1"}, "steps": ["精确"]},
        ]

    def test_guide_match_prefers_exact_identity(self):
        guide = match_device_guide(
            {"manufacturer": "Xiaomi", "model": "MiTV-ASTP0", "build_id": "PKQ1"},
            self.guides,
        )
        self.assertEqual(guide["id"], "astp0-build")

    def test_unknown_device_falls_back_to_generic(self):
        guide = match_device_guide({"manufacturer": "Unknown", "model": "Box"}, self.guides)
        self.assertEqual(guide["id"], "generic")

    def test_wallpaper_validation_locks_invalid_or_missing_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = validate_wallpaper(Path(directory) / "missing.jpg")
            self.assertFalse(missing["valid"])
            invalid = Path(directory) / "bad.jpg"
            invalid.write_bytes(b"not-an-image")
            self.assertFalse(validate_wallpaper(invalid)["valid"])

    def test_finish_after_adb_always_routes_to_safety_question(self):
        self.assertEqual(next_finish_state(adb_used=True), "FINISH-SAFETY-Q1")
        self.assertEqual(next_finish_state(adb_used=False), "END-NO-ADB")


if __name__ == "__main__":
    unittest.main()
