#!/usr/bin/env python3
"""Optional hardware readback QA. --exercise-settings briefly changes settings."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

spec = importlib.util.spec_from_file_location("bridge", Path(__file__).resolve().parents[1] / "bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def call(method="snapshot", params=None):
    response = bridge.request(method, params or {})
    if not response["ok"]:
        raise RuntimeError(response.get("error", {}).get("message", "Backend command failed"))
    return response["data"]


def run(method, params, feature, predicate):
    start = call(method, params)
    stamp = start["features"][feature]["lastSuccessMs"]
    deadline = time.monotonic() + 22
    while time.monotonic() < deadline:
        state = call()
        reading = state["features"][feature]
        if reading["availability"] == "valid" and reading["lastSuccessMs"] > stamp:
            if not predicate(state):
                raise RuntimeError("Fresh device readback differs from requested value")
            return
        time.sleep(0.2)
    raise RuntimeError("No fresh device readback within 22 seconds")


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--exercise-settings", action="store_true", help="Opt in to reversible hardware writes; original values are restored in finally")
parser.add_argument("--report", type=Path, help="Write a report without device addresses or personal paths")
args = parser.parse_args()
original = call()
if not original["connected"]:
    sys.exit("Connect and power on the headset first")
report = {"model": original["name"], "firmware": original["firmware"],
          "transport": "shared sonyd IPC", "tests": [], "subjective_listening": "not tested"}
if args.exercise_settings:
    if original["name"] not in {"WH-1000XM5", "WH-1000XM5SA"} or len(original["equalizer"]["bands"]) != 5:
        sys.exit("Hardware write QA is scoped to five-band WH-1000XM5 headsets")
    noise = original["noiseControl"]
    eq = original["equalizer"]
    changed_bands = list(eq["bands"])
    changed_bands[0] += -1 if changed_bands[0] >= 10 else 1
    cases = [
        ("ANC", "anc", {"enabled": True}, "noiseControl", lambda s: s["noiseControl"]["mode"] == "cancelling"),
        ("Noise off", "anc", {"enabled": False}, "noiseControl", lambda s: s["noiseControl"]["mode"] == "off"),
        ("Ambient + Focus on Voice", "ambient", {"level": 17, "focusOnVoice": True}, "noiseControl", lambda s: s["noiseControl"] == {"mode":"ambient", "ambientLevel":17, "focusOnVoice":True}),
        ("Custom EQ", "eqCustom", {"clearBass":eq["clearBass"], "bands":changed_bands}, "equalizer", lambda s: s["equalizer"]["bands"] == changed_bands),
        ("DSEE", "dsee", {"enabled": not original["dsee"]}, "dsee", lambda s: s["dsee"] != original["dsee"]),
        ("Speak-to-Chat", "speakToChat", {"enabled": not original["speakToChat"]}, "speakToChat", lambda s: s["speakToChat"] != original["speakToChat"]),
        ("Auto power-off disabled", "autoPowerOff", {"index":0}, "autoPowerOff", lambda s: s["autoPowerOff"] == 0),
    ]
    try:
        for name, method, params, feature, predicate in cases:
            if original["features"].get(feature, {}).get("availability") != "valid":
                report["tests"].append({"name":name, "result":"skipped unavailable"})
                continue
            try:
                run(method, params, feature, predicate)
                result = "fresh device readback passed"
            except (OSError, ValueError, RuntimeError) as error:
                result = str(error)
            report["tests"].append({"name":name, "result":result})
            print(name + ": " + result, flush=True)
    finally:
        restoration = [
            ("eqCustom", {"clearBass":eq["clearBass"], "bands":eq["bands"]}),
            ("dsee", {"enabled":original["dsee"]}),
            ("speakToChat", {"enabled":original["speakToChat"]}),
            ("autoPowerOff", {"index":original["autoPowerOff"]}),
            ("ambient", {"level":noise["ambientLevel"], "focusOnVoice":noise["focusOnVoice"]}) if noise["mode"] == "ambient"
                else ("anc", {"enabled":noise["mode"] == "cancelling"}),
        ]
        if eq["preset"] != 160:
            restoration.insert(1, ("eqPreset", {"preset":eq["preset"]}))
        errors = []
        for method, params in restoration:
            try:
                call(method, params)
            except (OSError, ValueError, RuntimeError) as error:
                errors.append(f"{method}: {error}")
        report["restore_errors"] = errors
        if errors:
            print("RESTORE ERRORS: " + json.dumps(errors), flush=True)
        else:
            print("Original settings restored; awaiting final refresh.", flush=True)
            time.sleep(7)
            final = call()
            fields = ["noiseControl", "equalizer", "dsee", "speakToChat", "autoPowerOff"]
            report["restored"] = all(final[field] == original[field] for field in fields)
            print("Restoration readback: " + str(report["restored"]), flush=True)
if args.report:
    args.report.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
