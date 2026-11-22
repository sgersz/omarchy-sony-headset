#!/usr/bin/env python3
"""Install the local plugin only; no downloads, package installs, or root access."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PLUGIN_ID = "steve.sony"
FILES = ("manifest.json", "Panel.qml", "Service.qml", "Model.js", "PlainText.qml",
         "HeadsetSlider.qml", "bridge.py", "README.md", "LICENSE", "NOTICE", "i18n/en.json")


def install(source, config_home):
    """Copy an explicit file list, backing up an existing user installation."""
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest["id"] != PLUGIN_ID:
        raise ValueError("Plugin id does not match this installer")
    for name in FILES:
        if not (source / name).is_file() or (source / name).is_symlink():
            raise ValueError(f"Missing or unexpected release file: {name}")
    destination = config_home / "omarchy/plugins" / PLUGIN_ID
    if destination.is_symlink():
        raise ValueError("Refusing to replace a symlink installation")
    for name in FILES:
        target = destination / name
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError("Refusing to write through a symlink in the installation")
    backup = None
    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = config_home / "omarchy/plugin-backups" / f"{PLUGIN_ID}-{stamp}"
        shutil.copytree(destination, backup)
    for name in FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    return destination, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check files and dependencies without changing anything")
    parser.add_argument("--no-enable", action="store_true", help="Copy files only; leave daemon and bar configuration alone")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your desktop user, without sudo")
    source = Path(__file__).resolve().parent
    required = ["omarchy", "omarchy-shell", "sonyd", "sony-device-center", "systemctl", "python3"]
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        parser.error("Missing dependencies: " + ", ".join(missing) + ". See README.md")
    for name in FILES:
        if not (source / name).is_file():
            parser.error("Incomplete release: " + name)
    subprocess.run(["omarchy", "plugin", "validate", str(source)], check=True)
    if args.check:
        print("Files and dependencies OK. No changes made.")
        return
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))).expanduser().resolve()
    destination, backup = install(source, config_home)
    print("Installed:", destination)
    if backup:
        print("Previous installation:", backup)
    if not args.no_enable:
        shell_config = config_home / "omarchy/shell.json"
        placed = False
        if shell_config.is_file():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            backup_config = config_home / "omarchy/plugin-backups" / f"shell-before-{PLUGIN_ID}-{stamp}.json"
            backup_config.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(shell_config, backup_config)
            layout = json.loads(shell_config.read_text()).get("bar", {}).get("layout", {})
            placed = any(isinstance(entries, list) and any(isinstance(entry, dict) and entry.get("id") == PLUGIN_ID for entry in entries)
                         for entries in layout.values())
        subprocess.run(["systemctl", "--user", "enable", "--now", "sonyd.service"], check=True)
        subprocess.run(["omarchy-shell", "shell", "rescanPlugins"], check=True)
        subprocess.run(["omarchy", "plugin", "enable", PLUGIN_ID] + ([] if placed else ["--section", "right"]), check=True)
        print("Enabled in your bar. Close/reopen the panel after updating.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"Installation stopped: {error}")
