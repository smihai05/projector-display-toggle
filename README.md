# Proiector (DisplayToggle)

> *I bought a projector, and then I got too lazy to change my monitor settings every time after connecting it to my PC.*

A tiny Windows utility that toggles the display mode between **"Extend these displays"** and **"Duplicate these displays"** (Settings > System > Display > Multiple displays) every time you run it. No dialogs to click through, no dropdowns to open — just double-click the executable.

## How it works

- On each run, it reads the **actual current display topology** from Windows via the `QueryDisplayConfig` API.
- If the current mode is **Duplicate**, it switches to **Extend**. Otherwise, it switches to **Duplicate**.
- Because it checks the real system state instead of just remembering its own last run, it stays correct even if you changed the display mode manually (e.g. through Windows Settings) in between runs.
- If that detection ever fails for some reason, it falls back to a small state file at `%LOCALAPPDATA%\DisplayToggle\state.txt` and simply alternates relative to its own last run.
- The actual mode switch is performed with Windows' own `DisplaySwitch.exe` utility (the same one behind the `Win + P` shortcut).
- A small message box confirms which mode was applied, then closes itself automatically after ~1.5 seconds.

## Project layout

Everything lives in a single Python file, plus its icon:

```
display_toggle.py   # the entire application
projector.ico        # application icon
Proiector.spec        # PyInstaller build spec (generated)
dist/Proiector.exe     # the built executable
```

No third-party Python packages are required — it only uses the standard library (`ctypes`, `subprocess`, `os`, `sys`).

## Requirements

- Windows 10 or later
- Python 3.8+ (only needed to build the executable, not to run it)
- [PyInstaller](https://pyinstaller.org/) (only needed to build the executable)

## Building the executable

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=projector.ico --name Proiector display_toggle.py
```

The resulting executable is created at `dist/Proiector.exe`. It's fully self-contained — it can be copied to any Windows machine without needing Python installed.

To rebuild later from the generated spec file:

```powershell
pyinstaller Proiector.spec
```

## Usage

Just run `Proiector.exe`:

- **1st run** → switches to Duplicate
- **2nd run** → switches back to Extend
- **3rd run** → Duplicate again, and so on

You can pin it to your taskbar or Start menu for a one-click toggle whenever you plug in your projector.

## Notes

- Switching to Duplicate may rearrange windows that were on a second monitor (this is normal Windows behavior, not something this app controls). Windows don't automatically snap back to their previous position when you switch back to Extend.
- `MessageBoxTimeoutW`, used for the self-closing confirmation popup, is an undocumented but long-stable Windows API (present since Windows 2000). If it's ever unavailable, the app silently skips the popup — the display mode still gets switched.
