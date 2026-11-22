# QA report — community beta 1.1.0

Checked 2026-11-21 on Arch Linux / Omarchy 4.5.0-3, Quickshell
0.3.2.r7.g2b4501a-1, Python 3.14.8, Node.js 22.23.3,
Sony Device Center 0.1.6-1, and WH-1000XM5 firmware 2.5.1.
The installed GUI and this plugin use the shared `sonyd` IPC backend.

## Outcome

Ready for community beta testing on the tested configuration. No unresolved
plugin errors were found in the final runtime checks. This is not a claim that
every Sony model, firmware, bar orientation, or Omarchy version is supported.
Screenshots show the horizontal top bar at 125% monitor scaling.

## Automated evidence

- **11 Python tests passed:** socket round trips, strict command bounds,
  incompatible or malformed replies, response-size limits, total deadlines,
  symlink rejection, a clean install under a path containing spaces,
  upgrade backups, and actual `sonyd --simulated` command round trips.
- **9 JavaScript tests passed:** tooltip markup safety, bounded text, invalid
  readings, valid false/zero states, ambient preference preservation,
  device identity changes, auto-off code mapping, and official firmware URLs.
- **Isolated QML integration passed:** real Omarchy components, failed and
  rejected EQ saves retaining drafts, successful saves, fresh device drafts,
  preset and auto-off bindings following backend state, disconnected controls,
  and the real Service/Process/Python/sonyd command path for success and failure.
- `omarchy plugin validate .` and Python compilation passed.
- The extracted release's installer, Python tests, JavaScript tests, and QML
  checks passed again in a clean temporary configuration. Deterministic ZIP
  rebuilding and archive-content checks passed. The release uses an explicit
  file allowlist; caches, backups, logs, personal Bluetooth addresses and personal
  paths are absent. Fake device addresses appear only in test fixtures.

## Physical headset evidence

All seven exercises returned a subsequent fresh device reading matching the
requested state, not just the command response:

| Exercise | Result |
| --- | --- |
| ANC | Passed |
| Noise control Off | Passed |
| Ambient level 17 with Focus on Voice | Passed |
| Custom five-band EQ | Passed |
| DSEE toggle | Passed |
| Speak-to-Chat toggle | Passed |
| Disable automatic power-off | Passed |

All original settings were restored and checked again after refresh. No
restoration errors occurred. Adaptive Volume remained unreadable and was not
changed; its control is disabled in the UI.

The physical daemon was stopped briefly: the panel showed an unavailable error
and gated device controls. Restarting it restored the connection automatically.
No application restart was required. The RØDE USB microphone remained the
default input throughout QA; the plugin never changes audio routing.

Noise, Equalizer and Features pages were inspected on the installed build.
The screenshots contain the panel only. The live shell had no plugin
TypeError/ReferenceError/binding-loop failures after the final reload.
Omarchy's usual duplicate IPC-target warnings for multiple monitor widgets
also occur for built-in panels; one shared Sony backend service is used.

## Corrections made during QA

- Preserve ambient level and voice preference when switching through ANC/Off.
- Retain an EQ draft when sending fails, and clear it for a different device.
- Restore dropdown bindings after selection, so failed writes and later
  updates cannot leave an incorrect selected value stuck on screen.
- Disable controls when a supposedly valid reading contains malformed data.
- Bound the entire local socket read, not just each individual receive call.
- Add slider keyboard access and qualify the shared color namespace.
- Correct backend V2 auto-off labels inherited from the upstream GUI.
- Add an installer with backups and an explicit source release file list.
- Add firmware guidance using fixed official Sony URLs, without an updater.

## Limits and remaining manual checks

- Physical readback does not establish the audible ANC/EQ/DSEE effect. Subjective
  listening and comparison with Sony Sound Connect were not performed.
- Only the WH-1000XM5 listed above was physically tested. Other models are
  experimental; ten-band EQ is intentionally unavailable.
- This build does not flash firmware, fetch firmware files, or check latest
  versions automatically. Updates are installed through Sony Sound Connect
  on a phone. The official support link was reviewed; there was no firmware flash.
- Adaptive Volume is unavailable on this tested headset/backend combination.
- Full keyboard interaction, RTL languages, vertical bars, clean reboot/login,
  long suspend cycles and sustained Bluetooth range-loss testing remain useful
  community follow-up. Native kit components provide theming and popup behavior;
  this is not a complete cross-desktop compatibility certification.
- The installer was tested in an isolated user configuration on this system,
  not a fresh Arch virtual machine. The AUR/backend package is a separate dependency.

Reproduce the automated checks with the commands in README.md. The optional
hardware script requires `--exercise-settings` before it changes a device.
