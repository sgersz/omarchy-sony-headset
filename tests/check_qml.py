#!/usr/bin/env python3
"""Run real panel logic in an isolated, invisible Wayland Quickshell engine."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
with tempfile.TemporaryDirectory(prefix="sony-qml-qa-") as temporary:
    config = Path(temporary)
    for directory in shell.iterdir():
        if directory.is_dir():
            (config / directory.name).symlink_to(directory, target_is_directory=True)
    (config / "Plugin").symlink_to(ROOT, target_is_directory=True)
    (config / "shell.qml").write_text((ROOT / "tests/panel.qml.in").read_text().replace("@PLUGIN@", "Plugin"))
    runtime = config / "runtime"
    runtime.mkdir(mode=0o700)
    wayland = os.environ.get("WAYLAND_DISPLAY", "wayland-1")
    if not wayland.startswith("/"):
        wayland = str(Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / wayland)
    environment = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QUICK_BACKEND="software",
                       XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY=wayland)
    spec = importlib.util.spec_from_file_location("bridge", ROOT / "bridge.py")
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    path = str(runtime / "sony-device-center.sock")
    daemon = subprocess.Popen(["sonyd", "--simulated", "--socket", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for attempt in range(100):
            try:
                if bridge.request("snapshot", {}, path)["data"]["connected"]:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("Simulated backend did not become ready")
        result = subprocess.run(["qs", "--path", str(config)], env=environment, capture_output=True, text=True, timeout=25)
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)
    output = result.stdout + result.stderr
    print(output)
    if result.returncode or "SONY_PANEL_QA_PASS" not in output or any(word in output for word in ["SONY_PANEL_QA_FAIL", "TypeError", "ReferenceError", "Failed to load configuration"]):
        raise SystemExit(1)
