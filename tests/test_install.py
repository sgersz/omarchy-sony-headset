import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_clean_install_is_portable_and_copies_only_release_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "a home with spaces/.config"
            destination, backup = installer.install(ROOT, config)
            self.assertIsNone(backup)
            copied = {str(path.relative_to(destination)) for path in destination.rglob("*") if path.is_file()}
            self.assertEqual(copied, set(installer.FILES))
            self.assertEqual((destination / "Panel.qml").read_bytes(), (ROOT / "Panel.qml").read_bytes())

    def test_update_keeps_a_backup_of_user_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary)
            destination, _ = installer.install(ROOT, config)
            (destination / "Panel.qml").write_text("local customizations")
            _, backup = installer.install(ROOT, config)
            self.assertEqual((backup / "Panel.qml").read_text(), "local customizations")
            self.assertEqual((destination / "Panel.qml").read_bytes(), (ROOT / "Panel.qml").read_bytes())

    def test_symlink_targets_are_rejected_before_any_files_are_changed(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config"
            destination = config / "omarchy/plugins" / installer.PLUGIN_ID
            destination.mkdir(parents=True)
            other = Path(temporary) / "other"
            other.mkdir()
            (destination / "i18n").symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError):
                installer.install(ROOT, config)
            self.assertFalse((destination / "Panel.qml").exists())
            self.assertFalse(any(other.iterdir()))
