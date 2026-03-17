from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path, prepend: Path | None = None):
    if prepend is not None and str(prepend) not in sys.path:
        sys.path.insert(0, str(prepend))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MAGICIAN_UTILS = _load_module("magician_utils", ROOT / "magician" / "utils.py")
MG400_UTILS = _load_module("mg400_utils_module", ROOT / "mg400" / "utils_mg400.py", ROOT / "mg400")
CONNECTIVITY = _load_module(
    "connectivity_check_module",
    ROOT / "mg400" / "00_connectivity_check.py",
    ROOT / "mg400",
)


class TestMagicianPortFallback(unittest.TestCase):
    def test_dobot_port_env_override(self) -> None:
        with patch.dict(MAGICIAN_UTILS.os.environ, {"DOBOT_PORT": "COM7"}, clear=False):
            self.assertEqual(MAGICIAN_UTILS.find_port(), "COM7")

    def test_prefers_usb_com_port_on_windows(self) -> None:
        ports = [
            SimpleNamespace(device="COM1", description="Communications Port", hwid="ACPI", vid=None),
            SimpleNamespace(
                device="COM4",
                description="USB Serial Device",
                hwid="USB VID:PID=10C4:EA60",
                vid=0x10C4,
            ),
        ]
        selected = MAGICIAN_UTILS._select_fallback_port(ports, platform_name="win32")
        self.assertEqual(selected.device, "COM4")

    def test_avoids_ttys_when_usb_device_exists_on_linux(self) -> None:
        ports = [
            SimpleNamespace(device="/dev/ttyS0", description="Standard serial", hwid="PNP0501", vid=None),
            SimpleNamespace(
                device="/dev/ttyUSB0",
                description="Silicon Labs CP210x",
                hwid="USB VID:PID=10C4:EA60",
                vid=0x10C4,
            ),
        ]
        selected = MAGICIAN_UTILS._select_fallback_port(ports, platform_name="linux")
        self.assertEqual(selected.device, "/dev/ttyUSB0")


class TestConnectivityHelpers(unittest.TestCase):
    def test_resolve_target_ip_uses_env_override(self) -> None:
        with patch.dict(MG400_UTILS.os.environ, {"DOBOT_MG400_IP": "192.168.2.77"}, clear=False):
            self.assertEqual(MG400_UTILS.resolve_target_ip(), "192.168.2.77")

    def test_resolve_target_ip_prefers_robot_argument(self) -> None:
        self.assertEqual(MG400_UTILS.resolve_target_ip(ip="192.168.2.55", robot=2), "192.168.2.10")

    def test_add_target_arguments_keeps_robot_optional(self) -> None:
        parser = argparse.ArgumentParser(add_help=False)
        MG400_UTILS.add_target_arguments(parser, default_ip="192.168.2.10")
        args = parser.parse_args([])
        self.assertEqual(args.ip, "192.168.2.10")
        self.assertIsNone(args.robot)

    def test_direct_connect_help_mentions_windows_helper(self) -> None:
        text = MG400_UTILS.format_direct_connect_help("192.168.2.7", platform_name="win32")
        self.assertIn("Set-MG400StaticIp.ps1", text)
        self.assertIn("DOBOT_MG400_IP", text)
        self.assertIn("-Apply", text)

    @patch.object(MG400_UTILS, "_load_windows_direct_connect_lines", side_effect=AssertionError("unexpected windows import"))
    def test_linux_help_does_not_require_windows_helper(self, _loader) -> None:
        text = MG400_UTILS.format_direct_connect_help("192.168.2.7", platform_name="linux")
        self.assertIn("Linux/macOS:", text)
        self.assertNotIn("Set-MG400StaticIp.ps1", text)

    def test_query_dashboard_version_uses_method_when_available(self) -> None:
        dashboard = SimpleNamespace(GetVersion=lambda: "0,{v1.2.3},GetVersion();")
        self.assertEqual(MG400_UTILS.query_dashboard_version(dashboard), "0,{v1.2.3},GetVersion();")

    def test_query_dashboard_version_falls_back_to_send_recv(self) -> None:
        dashboard = SimpleNamespace(sendRecvMsg=lambda _cmd: "0,{v1.2.3},GetVersion();")
        self.assertEqual(MG400_UTILS.query_dashboard_version(dashboard), "0,{v1.2.3},GetVersion();")

    def test_query_dashboard_version_raises_on_error_status(self) -> None:
        dashboard = SimpleNamespace(sendRecvMsg=lambda _cmd: "-10000,{},GetVersion();")
        with self.assertRaises(ValueError):
            MG400_UTILS.query_dashboard_version(dashboard)

    def test_build_ping_command_windows(self) -> None:
        self.assertEqual(
            CONNECTIVITY._build_ping_command("127.0.0.1", count=1, timeout=2, platform_name="win32"),
            ["ping", "-n", "1", "-w", "2000", "127.0.0.1"],
        )

    def test_build_ping_command_posix(self) -> None:
        self.assertEqual(
            CONNECTIVITY._build_ping_command("127.0.0.1", count=1, timeout=2, platform_name="linux"),
            ["ping", "-c", "1", "-W", "2", "127.0.0.1"],
        )

    @patch.object(CONNECTIVITY.subprocess, "run", side_effect=FileNotFoundError)
    def test_posix_local_connections_note_when_ss_missing(self, _run) -> None:
        connections, note = CONNECTIVITY._check_local_connections_posix("192.168.2.7")
        self.assertEqual(connections, [])
        self.assertIn("ss", note)

    @patch.object(CONNECTIVITY.subprocess, "run")
    def test_windows_local_connections_parses_netstat(self, run_mock) -> None:
        run_mock.side_effect = [
            subprocess.CompletedProcess(
                args=["netstat"],
                returncode=0,
                stdout=(
                    "  Proto  Local Address          Foreign Address        State           PID\n"
                    "  TCP    192.168.2.100:51538    192.168.2.7:29999      ESTABLISHED     4321\n"
                    "  TCP    127.0.0.1:5000         127.0.0.1:5001         ESTABLISHED     9000\n"
                ),
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["tasklist"],
                returncode=0,
                stdout='"python.exe","4321","Console","1","12,000 K"\n',
                stderr="",
            ),
        ]

        connections, note = CONNECTIVITY._check_local_connections_windows("192.168.2.7")

        self.assertEqual(
            connections,
            ["192.168.2.100:51538 -> 192.168.2.7:29999 pid=4321 proc=python.exe"],
        )
        self.assertIsNone(note)

    @patch.object(MG400_UTILS.socket, "create_connection", side_effect=TimeoutError("timed out"))
    def test_connect_with_diagnostics_preflight_handles_unreachable_host(self, _create_connection) -> None:
        with self.assertRaises(ConnectionError) as ctx:
            MG400_UTILS.connect_with_diagnostics("192.168.2.7")

        message = str(ctx.exception)
        self.assertIn("Cannot reach MG400 at 192.168.2.7", message)
        self.assertIn("29999", message)
        if MG400_UTILS.sys.platform == "win32":
            self.assertIn("Set-MG400StaticIp.ps1", message)
        else:
            self.assertIn("Linux/macOS:", message)

    @patch.object(MG400_UTILS, "connect_with_diagnostics", return_value=("dashboard", "move", "feed"))
    def test_connect_from_args_or_exit_returns_resolved_ip_first(self, connect_mock) -> None:
        result = MG400_UTILS.connect_from_args_or_exit(SimpleNamespace(ip="192.168.2.44", robot=None))
        self.assertEqual(result, ("192.168.2.44", "dashboard", "move", "feed"))
        connect_mock.assert_called_once_with("192.168.2.44")

    @patch.object(MG400_UTILS, "connect", side_effect=Exception("vendor failure"))
    @patch.object(
        MG400_UTILS.socket,
        "create_connection",
        return_value=SimpleNamespace(close=lambda: None),
    )
    def test_connect_with_diagnostics_wraps_vendor_exception(self, _create_connection, _connect) -> None:
        with self.assertRaises(ConnectionError) as ctx:
            MG400_UTILS.connect_with_diagnostics("192.168.2.7")

        message = str(ctx.exception)
        self.assertIn("MG400 connection setup failed at 192.168.2.7", message)
        self.assertIn("vendor failure", message)


if __name__ == "__main__":
    unittest.main()
