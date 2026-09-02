"""
DisplayToggle
=============

Every time this runs, it toggles the Windows display mode (Settings > System >
Display > Multiple displays) between:

    - "Extend these displays"
    - "Duplicate these displays"

It detects the actual current mode using the Windows QueryDisplayConfig API,
so it keeps working correctly even if the mode was changed manually between
runs. If detection fails for any reason, it falls back to a small local state
file and simply alternates relative to the last run.
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Windows constants (winuser.h)
# ---------------------------------------------------------------------------

QDC_DATABASE_CURRENT = 0x00000004

DISPLAYCONFIG_TOPOLOGY_INTERNAL = 0x00000001
DISPLAYCONFIG_TOPOLOGY_CLONE = 0x00000002
DISPLAYCONFIG_TOPOLOGY_EXTEND = 0x00000004
DISPLAYCONFIG_TOPOLOGY_EXTERNAL = 0x00000008

ERROR_SUCCESS = 0

# Sizes (in bytes) of the DISPLAYCONFIG_PATH_INFO and DISPLAYCONFIG_MODE_INFO
# structures as reported by Windows (identical on x86 and x64). We don't need
# to parse the contents of these structures, only to give the API a big
# enough memory area to write into.
_PATH_INFO_SIZE = 72
_MODE_INFO_SIZE = 64

_STATE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "DisplayToggle")
_STATE_FILE = os.path.join(_STATE_DIR, "state.txt")

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.GetDisplayConfigBufferSizes.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(wintypes.UINT),
    ctypes.POINTER(wintypes.UINT),
]
user32.GetDisplayConfigBufferSizes.restype = wintypes.LONG

user32.QueryDisplayConfig.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(wintypes.UINT),
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.UINT),
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.UINT),
]
user32.QueryDisplayConfig.restype = wintypes.LONG


def get_current_topology():
    """Return the current display topology id, or None if it can't be read."""
    num_paths = wintypes.UINT(0)
    num_modes = wintypes.UINT(0)

    ret = user32.GetDisplayConfigBufferSizes(
        QDC_DATABASE_CURRENT, ctypes.byref(num_paths), ctypes.byref(num_modes)
    )
    if ret != ERROR_SUCCESS:
        return None

    path_buffer = (ctypes.c_ubyte * (max(num_paths.value, 1) * _PATH_INFO_SIZE))()
    mode_buffer = (ctypes.c_ubyte * (max(num_modes.value, 1) * _MODE_INFO_SIZE))()
    topology_id = wintypes.UINT(0)

    ret = user32.QueryDisplayConfig(
        QDC_DATABASE_CURRENT,
        ctypes.byref(num_paths),
        ctypes.cast(path_buffer, ctypes.c_void_p),
        ctypes.byref(num_modes),
        ctypes.cast(mode_buffer, ctypes.c_void_p),
        ctypes.byref(topology_id),
    )
    if ret != ERROR_SUCCESS:
        return None
    return topology_id.value


def read_last_state():
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def write_last_state(mode):
    try:
        os.makedirs(_STATE_DIR, exist_ok=True)
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(mode)
    except OSError:
        pass


def decide_target_mode():
    """Decide whether to switch to 'extend' or to 'clone'."""
    topology = get_current_topology()

    if topology == DISPLAYCONFIG_TOPOLOGY_CLONE:
        return "extend"
    if topology in (
        DISPLAYCONFIG_TOPOLOGY_EXTEND,
        DISPLAYCONFIG_TOPOLOGY_INTERNAL,
        DISPLAYCONFIG_TOPOLOGY_EXTERNAL,
    ):
        return "clone"

    # Detection failed (topology is None) -> fall back to the state file.
    last = read_last_state()
    if last == "clone":
        return "extend"
    return "clone"


def apply_mode(mode):
    """Apply the display mode using the native DisplaySwitch.exe utility."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    display_switch = os.path.join(windir, "System32", "DisplaySwitch.exe")
    flag = "/extend" if mode == "extend" else "/clone"

    subprocess.run([display_switch, flag], check=False)
    write_last_state(mode)


def show_notification(mode):
    """Show a short, self-closing message box with the mode that was applied."""
    text = {
        "extend": "Display mode: Extend these displays",
        "clone": "Display mode: Duplicate these displays",
    }[mode]

    MB_TOPMOST = 0x00040000
    MB_ICONINFORMATION = 0x00000040
    timeout_ms = 1500

    try:
        # MessageBoxTimeoutW is undocumented, but has been reliably present
        # in user32.dll since Windows 2000; it closes itself automatically.
        user32.MessageBoxTimeoutW(
            None,
            text,
            "DisplayToggle",
            MB_ICONINFORMATION | MB_TOPMOST,
            0,
            timeout_ms,
        )
    except (AttributeError, OSError):
        pass


def main():
    mode = decide_target_mode()
    apply_mode(mode)
    show_notification(mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
