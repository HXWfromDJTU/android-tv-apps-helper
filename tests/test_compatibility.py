import unittest

from tv_helper.compatibility import compatibility_rows, match_compatibility


class CompatibilityTests(unittest.TestCase):
    def test_wallpaper_and_home_key_are_classified_independently(self):
        records = [
            {
                "manufacturer": "Xiaomi",
                "model": "MiTV-ASTP0",
                "actions": {"wallpaper": "verified_supported", "home_key": "high_risk"},
                "evidence": "two observed sessions",
            }
        ]
        match = match_compatibility(
            {"manufacturer": "Xiaomi", "model": "MiTV-ASTP0"}, records
        )
        rows = compatibility_rows(match, ("wallpaper", "home_key"))

        self.assertEqual([row["risk"] for row in rows], ["verified_supported", "high_risk"])
        self.assertIn("几天后", rows[0]["message"])
        self.assertIn("大概率无法", rows[1]["message"])

    def test_unknown_compatibility_does_not_invent_probability(self):
        rows = compatibility_rows(None, ("wallpaper", "home_key"))
        self.assertTrue(all(row["risk"] == "unknown" for row in rows))
        self.assertTrue(all("可靠兼容性证据" in row["message"] for row in rows))
        self.assertTrue(all("大概率" not in row["message"] for row in rows))


if __name__ == "__main__":
    unittest.main()
