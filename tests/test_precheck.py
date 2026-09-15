import unittest

from tv_helper.precheck import classify_discovered_device, make_precheck_result, run_passive_precheck


class PrecheckTests(unittest.TestCase):
    def test_passive_precheck_runs_only_read_only_commands(self):
        commands = []

        class Result:
            def __init__(self, stdout=""):
                self.returncode = 0
                self.stdout = stdout
                self.stderr = ""

        def runner(command, **kwargs):
            commands.append(tuple(command))
            if command[-1] == "version":
                return Result("Android Debug Bridge version 1.0.41\n")
            if command[-2:] == ["devices", "-l"]:
                return Result("List of devices attached\n")
            return Result("")

        result = run_passive_precheck(adb_path="/tmp/adb", command_runner=runner, network_probe=lambda: "192.168.31.8")

        self.assertEqual(result["status"], "attention")
        flattened = " ".join(" ".join(command) for command in commands)
        self.assertNotIn(" connect ", f" {flattened} ")
        self.assertNotIn("scan", flattened)
        self.assertEqual(result["local_address"], "192.168.31.8")
        self.assertEqual(result["scan_approval"]["scope"], ["192.168.31.0/24"])
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
        self.assertEqual(result["local_address"], "192.0.2.10")

    def test_uncertain_device_is_never_called_a_tv(self):
        label = classify_discovered_device(
            {"serial": "192.0.2.20:5555", "state": "device", "details": []}
        )
        self.assertEqual(label, "可能是电视")

    def test_precheck_table_lists_each_candidate_without_inventing_identity(self):
        result = make_precheck_result(
            adb_available=True,
            adb_version="1.0.41",
            devices=(
                {
                    "serial": "192.0.2.20:5555",
                    "state": "device",
                    "details": ("model:MiTV-ASTP0",),
                },
            ),
            local_address=None,
            wifi_name=None,
        )
        candidate = result["rows"][-1]
        self.assertEqual(candidate["item"], "候选设备 1")
        self.assertIn("MiTV-ASTP0", candidate["result"])


if __name__ == "__main__":
    unittest.main()
