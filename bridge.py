"""Bounded local client for Sony Device Center's versioned sonyd interface."""
import json
import os
import socket
import stat
import struct
import sys
import time

LIMIT = 65536
PRESETS = {0, 16, 17, 18, 19, 20, 21, 22, 23, 160}


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Setting is outside its supported range")
    return value


def validate(method, params):
    if not isinstance(params, dict):
        raise ValueError("Settings must be an object")
    if method == "snapshot" and not params:
        return
    if method in {"anc", "dsee", "speakToChat", "adaptiveVolume"}:
        if set(params) == {"enabled"} and type(params["enabled"]) is bool:
            return
    elif method == "ambient":
        if set(params) == {"level", "focusOnVoice"} and type(params["focusOnVoice"]) is bool:
            integer(params["level"], 1, 20)
            return
    elif method == "eqPreset" and set(params) == {"preset"}:
        if integer(params["preset"], 0, 255) in PRESETS:
            return
    elif method == "eqCustom" and set(params) == {"clearBass", "bands"}:
        integer(params["clearBass"], -10, 10)
        bands = params["bands"]
        if isinstance(bands, list) and len(bands) == 5:
            for band in bands:
                integer(band, -10, 10)
            return
    elif method == "autoPowerOff" and set(params) == {"index"}:
        integer(params["index"], 0, 5)
        return
    raise ValueError("Unsupported command or invalid settings")


def request(method, params, path=None):
    validate(method, params)
    if path is None:
        runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        path = os.path.join(runtime, "sony-device-center.sock")
    parent = os.lstat(os.path.dirname(path))
    endpoint = os.lstat(path)
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError("Sony backend directory has unsafe permissions")
    if not stat.S_ISSOCK(endpoint.st_mode) or endpoint.st_uid != os.getuid() or endpoint.st_mode & 0o077:
        raise ValueError("Sony backend socket has unsafe permissions")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        timeout = 8 if method != "snapshot" else 3
        deadline = time.monotonic() + timeout
        client.settimeout(timeout)
        client.connect(path)
        _, uid, _ = struct.unpack("3i", client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.getuid():
            raise ValueError("Sony backend belongs to a different user")
        client.sendall(json.dumps({"version": 1, "id": 1, "method": method, "params": params}).encode() + b"\n")
        data = bytearray()
        while b"\n" not in data:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Sony backend request timed out")
            client.settimeout(remaining)
            chunk = client.recv(4096)
            if not chunk:
                raise ValueError("Sony backend closed the connection")
            data.extend(chunk)
            if len(data) > LIMIT:
                raise ValueError("Sony backend response is too large")
    result = json.loads(data.split(b"\n", 1)[0])
    if not isinstance(result, dict) or type(result.get("version")) is not int or result["version"] != 1 or type(result.get("id")) is not int or result["id"] != 1:
        raise ValueError("Sony backend returned an incompatible response")
    if type(result.get("ok")) is not bool:
        raise ValueError("Sony backend returned an invalid response")
    return result


if __name__ == "__main__":
    try:
        if not 2 <= len(sys.argv) <= 3:
            raise ValueError("Expected a command and optional JSON settings")
        result = request(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) == 3 else {})
    except (OSError, ValueError, RecursionError) as error:
        message = "Sony backend is not running" if isinstance(error, FileNotFoundError) else str(error)
        result = {"ok": False, "error": {"message": message[:240]}}
    print(json.dumps(result, separators=(",", ":")))
