import unittest

from tv_helper.precheck import classify_discovered_device, make_precheck_result


class PrecheckTests(unittest.TestCase):
    def test_no_devices_is_attention_and_not_proof_adb_is_disabled(self):
        result = make_precheck_result(
            adb_available=True,
            adb_version="1.0.41",
            devices=(),
            local_address="192.0.2.10",
            wifi_name=None,
        )

        self.assertEqual(result["status"], "attention")
        self.assertIn("不能证明电视未开启 ADB", result["blocker"])
        self.assertFalse(result["active_scan_performed"])

    def test_uncertain_device_is_never_called_a_tv(self):
        label = classify_discovered_device(
            {"serial": "192.0.2.20:5555", "state": "device", "details": []}
        )
        self.assertEqual(label, "可能是电视")


if __name__ == "__main__":
    unittest.main()
