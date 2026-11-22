"""Exercise the actual installed sonyd over an isolated, simulated socket."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location("bridge", Path(__file__).resolve().parents[1] / "bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


@unittest.skipUnless(shutil.which("sonyd"), "sonyd is not installed")
class SimulatedBackendTests(unittest.TestCase):
    def test_supported_commands_round_trip_through_real_backend(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = temporary + "/sony.sock"
            daemon = subprocess.Popen(["sonyd", "--simulated", "--socket", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    try:
                        response = bridge.request("snapshot", {}, path)
                        if response["ok"] and response["data"]["connected"]:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(0.1)
                else:
                    self.fail("Simulated backend did not connect")
                commands = [
                    ("ambient", {"level": 17, "focusOnVoice": True}, "noiseControl", {"mode":"ambient", "ambientLevel":17, "focusOnVoice":True}),
                    ("anc", {"enabled": True}, "noiseControl.mode", "cancelling"),
                    ("anc", {"enabled": False}, "noiseControl.mode", "off"),
                    ("eqCustom", {"clearBass": -2, "bands": [-3,0,3,-2,3]}, "equalizer.bands", [-3,0,3,-2,3]),
                    ("eqPreset", {"preset": 22}, "equalizer.preset", 22),
                    ("dsee", {"enabled": True}, "dsee", True),
                    ("speakToChat", {"enabled": True}, "speakToChat", True),
                    ("adaptiveVolume", {"enabled": True}, "adaptiveVolume", True),
                    ("autoPowerOff", {"index": 5}, "autoPowerOff", 5),
                ]
                for method, params, key, expected in commands:
                    with self.subTest(method=method, params=params):
                        response = bridge.request(method, params, path)
                        self.assertTrue(response["ok"], response)
                        actual = bridge.request("snapshot", {}, path)["data"]
                        for part in key.split("."):
                            actual = actual[part]
                        self.assertEqual(actual, expected)
            finally:
                daemon.terminate()
                daemon.wait(timeout=10)
