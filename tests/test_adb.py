import os
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PLUGIN_SCRIPTS = (
    Path(__file__).parents[1]
    / "plugins"
    / "android-tv-apps-helper"
    / "scripts"
)
sys.path.insert(0, str(PLUGIN_SCRIPTS))

from tv_helper.adb import AdbError, AdbRunner, parse_devices


class AdbTests(unittest.TestCase):
    def test_parse_devices_preserves_authorization_states(self):
        output = textwrap.dedent(
            """
            List of devices attached
            192.168.31.170:5555 device product:mitv model:MiTV4_ANSM0 transport_id:1
            192.168.31.157:5555 unauthorized transport_id:2
            emulator-5554 offline transport_id:3
            """
        )
        devices = parse_devices(output)
        self.assertEqual(
            [(item.serial, item.state) for item in devices],
            [
                ("192.168.31.170:5555", "device"),
                ("192.168.31.157:5555", "unauthorized"),
                ("emulator-5554", "offline"),
            ],
        )

    def test_device_commands_are_bound_to_verified_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "args.log"
            adb = root / "adb"
            adb.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$ADB_TEST_LOG\"\nprintf 'ok\\n'\n",
                encoding="utf-8",
            )
            adb.chmod(adb.stat().st_mode | stat.S_IXUSR)
            old = os.environ.get("ADB_TEST_LOG")
            os.environ["ADB_TEST_LOG"] = str(log)
            try:
                runner = AdbRunner(adb)
                runner.shell("192.168.31.170:5555", ["getprop", "ro.product.model"])
            finally:
                if old is None:
                    os.environ.pop("ADB_TEST_LOG", None)
                else:
                    os.environ["ADB_TEST_LOG"] = old
            self.assertEqual(
                log.read_text(encoding="utf-8").splitlines(),
                ["-s", "192.168.31.170:5555", "shell", "getprop", "ro.product.model"],
            )

    def test_install_rejects_unverified_target_state(self):
        runner = AdbRunner(Path("/missing/adb"))
        with self.assertRaisesRegex(AdbError, "device"):
            runner.install("192.168.31.170:5555", Path("app.apk"), state="unauthorized")


if __name__ == "__main__":
    unittest.main()
