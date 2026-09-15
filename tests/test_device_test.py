import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ghost_builder.device_test import (
    DeviceTestReport,
    PhysicalDeviceVerifier,
    parse_adb_devices,
    save_device_test_report,
)


class DeviceVerificationTests(unittest.TestCase):
    def test_parse_adb_devices_tracks_authorization_state(self):
        text = "List of devices attached\nABC123\tdevice\nXYZ999\tunauthorized\nEMU555\toffline\n"
        items = parse_adb_devices(text)
        self.assertEqual([(x.serial, x.state) for x in items], [
            ("ABC123", "device"),
            ("XYZ999", "unauthorized"),
            ("EMU555", "offline"),
        ])

    def test_physical_device_flow_installs_verifies_and_launches(self):
        with tempfile.TemporaryDirectory() as td:
            apk = Path(td) / "demo.apk"
            apk.write_bytes(b"apk")
            toolchain = mock.Mock()
            toolchain.adb_exe.return_value = Path("adb.exe")
            toolchain.env.return_value = {}
            responses = [
                mock.Mock(returncode=0, stdout="", stderr=""),
                mock.Mock(returncode=0, stdout="List of devices attached\nABC123\tdevice\n", stderr=""),
                mock.Mock(returncode=0, stdout="Success\n", stderr=""),
                mock.Mock(returncode=0, stdout="package:/data/app/demo/base.apk\n", stderr=""),
                mock.Mock(returncode=0, stdout="Status: ok\nActivity: com.swir.demo/.MainActivity\n", stderr=""),
            ]
            with mock.patch("ghost_builder.device_test.subprocess.run", side_effect=responses) as run:
                report = PhysicalDeviceVerifier(toolchain).run(apk, "com.swir.demo", ".MainActivity")
            self.assertTrue(report.passed)
            self.assertEqual(report.serial, "ABC123")
            self.assertEqual(report.package_name, "com.swir.demo")
            self.assertTrue(report.package_path.startswith("package:"))
            self.assertEqual(run.call_count, 5)
            install_args = run.call_args_list[2].args[0]
            self.assertEqual(install_args[:5], ["adb.exe", "-s", "ABC123", "install", "-r"])

    def test_unauthorized_phone_gives_actionable_error(self):
        with tempfile.TemporaryDirectory() as td:
            apk = Path(td) / "demo.apk"
            apk.write_bytes(b"apk")
            toolchain = mock.Mock()
            toolchain.adb_exe.return_value = Path("adb.exe")
            toolchain.env.return_value = {}
            responses = [
                mock.Mock(returncode=0, stdout="", stderr=""),
                mock.Mock(returncode=0, stdout="List of devices attached\nABC123\tunauthorized\n", stderr=""),
            ]
            with mock.patch("ghost_builder.device_test.subprocess.run", side_effect=responses):
                with self.assertRaisesRegex(RuntimeError, "allow USB debugging"):
                    PhysicalDeviceVerifier(toolchain).run(apk, "com.swir.demo", ".MainActivity")

    def test_device_report_is_local_json_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            report = DeviceTestReport(
                passed=True,
                serial="ABC123",
                package_name="com.swir.demo",
                artifact=str(Path(td) / "demo.apk"),
                package_path="package:/data/app/demo/base.apk",
                launch_output="Status: ok",
                timestamp="2026-09-15T20:20:00+00:00",
            )
            target = save_device_test_report(Path(td) / "device_test_last.json", report)
            raw = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(raw["passed"])
            self.assertEqual(raw["serial"], "ABC123")
            self.assertEqual(raw["package_name"], "com.swir.demo")


if __name__ == "__main__":
    unittest.main()
