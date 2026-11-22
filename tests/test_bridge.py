import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("bridge", Path(__file__).resolve().parents[1] / "bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def test_rejects_unsupported_and_out_of_range_writes(self):
        for method, params in [("powerOff", {}), ("anc", {"enabled": "false"}),
                               ("ambient", {"level": 21, "focusOnVoice": False}),
                               ("eqCustom", {"clearBass": 0, "bands": [0, 0, 0, 0, 99]}),
                               ("eqPreset", {"preset": 255}), ("autoPowerOff", {"index": True})]:
            with self.subTest(method=method, params=params), self.assertRaises(ValueError):
                bridge.validate(method, params)

    def test_validates_socket_round_trip_and_preserves_text_as_data(self):
        result, captured = self.round_trip("snapshot", {})
        self.assertEqual(captured["method"], "snapshot")
        self.assertEqual(result["data"]["name"], '<img src="https://invalid.test/">')

    def test_custom_eq_payload_reaches_backend_unchanged(self):
        params = {"clearBass": -2, "bands": [-3, 0, 3, -2, 3]}
        result, captured = self.round_trip("eqCustom", params)
        self.assertTrue(result["ok"])
        self.assertEqual(captured, {"version": 1, "id": 1, "method": "eqCustom", "params": params})

    def round_trip(self, method, params, response=None):
        with tempfile.TemporaryDirectory() as directory:
            path = directory + "/sony.sock"
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(path)
            os.chmod(path, 0o600)
            server.listen(1)
            server.settimeout(2)
            captured = []
            def serve():
                with server:
                    connection, _ = server.accept()
                    with connection:
                        captured.append(json.loads(connection.makefile().readline()))
                        reply = response if response is not None else {"version": 1, "id": 1, "ok": True, "data": {"name": '<img src="https://invalid.test/">'}}
                        connection.sendall(json.dumps(reply).encode() + b"\n")
            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            result = bridge.request(method, params, path)
            worker.join(2)
            self.assertFalse(worker.is_alive())
            return result, captured[0]

    def test_rejects_incompatible_and_malformed_response_envelopes(self):
        for response in [{"version": 2, "id": 1, "ok": True}, {"version": True, "id": 1, "ok": True},
                         {"version": 1, "id": 2, "ok": True}, {"version": 1, "id": 1, "ok": "true"}]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.round_trip("snapshot", {}, response)

    def test_rejects_oversized_response(self):
        with self.assertRaisesRegex(ValueError, "too large"):
            self.round_trip("snapshot", {}, {"version": 1, "id": 1, "ok": True, "data": "x" * bridge.LIMIT})

    def test_total_deadline_stops_a_backend_sending_partial_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = directory + "/sony.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as endpoint:
                endpoint.bind(path)
                os.chmod(path, 0o600)
                with patch.object(bridge.socket, "socket") as factory, patch.object(bridge.time, "monotonic", side_effect=[0, 0.5, 3.1]):
                    client = factory.return_value.__enter__.return_value
                    client.getsockopt.return_value = bridge.struct.pack("3i", 1, os.getuid(), os.getgid())
                    client.recv.return_value = b"{"
                    with self.assertRaises(TimeoutError):
                        bridge.request("snapshot", {}, path)
                    self.assertEqual(client.recv.call_count, 1)

    def test_rejects_a_symlink_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            path = directory + "/sony.sock"
            os.symlink("/tmp/unrelated.sock", path)
            with self.assertRaises(ValueError):
                bridge.request("snapshot", {}, path)


if __name__ == "__main__":
    unittest.main()
