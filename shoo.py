"""
ShooApp - System tray uninstaller.
Click the tray icon to browse installed apps and uninstall them directly from the menu.
"""

import subprocess
import threading

import winreg

import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw
import pystray


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

_REG_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

_apps_cache: list[dict] = []
_cache_lock = threading.Lock()


def _load_apps() -> list[dict]:
    apps: list[dict] = []
    seen: set[str] = set()

    for hive, key_path in _REG_PATHS:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_name) as sub:
                            try:
                                name = winreg.QueryValueEx(sub, "DisplayName")[0].strip()
                                if not name or name in seen:
                                    continue
                                uninstall = winreg.QueryValueEx(sub, "UninstallString")[0].strip()
                                if not uninstall:
                                    continue
                                version = ""
                                try:
                                    version = winreg.QueryValueEx(sub, "DisplayVersion")[0].strip()
                                except OSError:
                                    pass
                                publisher = ""
                                try:
                                    publisher = winreg.QueryValueEx(sub, "Publisher")[0].strip()
                                except OSError:
                                    pass
                                seen.add(name)
                                apps.append({
                                    "name": name,
                                    "version": version,
                                    "uninstall": uninstall,
                                    "publisher": publisher,
                                })
                            except OSError:
                                pass
                    except OSError:
                        pass
        except OSError:
            pass

    apps.sort(key=lambda x: x["name"].lower())
    return apps


def _refresh_cache() -> None:
    global _apps_cache
    apps = _load_apps()
    with _cache_lock:
        _apps_cache = apps


def _get_apps() -> list[dict]:
    with _cache_lock:
        return list(_apps_cache)


# ---------------------------------------------------------------------------
# Confirmation dialog (no persistent window — temporary Tk per call)
# ---------------------------------------------------------------------------

def _confirm_uninstall(app: dict) -> bool:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    result = messagebox.askyesno(
        "ShooApp — Uninstall",
        f"Uninstall \"{app['name']}\"?\n\nThe app's own uninstaller will open.",
        icon="warning",
        parent=root,
    )
    root.destroy()
    return result


def _show_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showerror("ShooApp", message, parent=root)
    root.destroy()


# ---------------------------------------------------------------------------
# Uninstall action
# ---------------------------------------------------------------------------

def _run_uninstall(app: dict, icon: pystray.Icon) -> None:
    if not _confirm_uninstall(app):
        return
    try:
        subprocess.Popen(app["uninstall"], shell=True)
    except Exception as exc:
        _show_error(f"Could not launch uninstaller:\n{exc}")
        return
    # Refresh app list after a short delay so the uninstalled app disappears
    threading.Timer(4.0, lambda: _force_refresh(icon)).start()


# ---------------------------------------------------------------------------
# Menu builders
# ---------------------------------------------------------------------------

def _build_app_items(icon: pystray.Icon) -> list:
    apps = _get_apps()

    if not apps:
        return [pystray.MenuItem("No apps found", None, enabled=False)]

    # Group by publisher
    groups: dict[str, list[dict]] = {}
    for app in apps:
        pub = app["publisher"] or "(Other)"
        groups.setdefault(pub, []).append(app)

    def make_uninstall(a):
        def _fn(icon, item):
            threading.Thread(
                target=_run_uninstall, args=(a, icon), daemon=True
            ).start()
        return _fn

    items = []
    for pub in sorted(groups, key=str.lower):
        app_items = []
        for app in sorted(groups[pub], key=lambda x: x["name"].lower()):
            label = f"Remove  {app['name']}"
            if app["version"]:
                label += f"  {app['version']}"
            app_items.append(pystray.MenuItem(label, make_uninstall(app)))
        items.append(pystray.MenuItem(pub, pystray.Menu(*app_items)))

    return items


def _build_app_menu(icon: pystray.Icon) -> pystray.Menu:
    return pystray.Menu(*_build_app_items(icon))


def _build_action_menu(icon: pystray.Icon) -> pystray.Menu:
    def refresh_fn(icon, item):
        threading.Thread(target=_force_refresh, args=(icon,), daemon=True).start()

    count = len(_get_apps())
    label = f"{count} apps installed" if count else "Loading…"

    return pystray.Menu(
        pystray.MenuItem(label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Refresh", refresh_fn),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
    )


def _force_refresh(icon: pystray.Icon) -> None:
    _refresh_cache()
    icon._left_menu  = _build_app_menu(icon)
    icon._right_menu = _build_action_menu(icon)
    icon.menu        = icon._right_menu
    count = len(_get_apps())
    icon.title = f"ShooApp — {count} apps"


# ---------------------------------------------------------------------------
# Tray icon image
# ---------------------------------------------------------------------------

def _create_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=12, fill=(40, 40, 40, 230))

    m = 14
    lw = 6
    draw.rectangle([m, m, size - m, size - m], outline=(220, 80, 60), width=3)
    inner = m + 8
    draw.line([inner, inner, size - inner, size - inner], fill=(220, 80, 60), width=lw)
    draw.line([size - inner, inner, inner, size - inner], fill=(220, 80, 60), width=lw)

    return img


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Load apps before first menu build
    _refresh_cache()

    icon = pystray.Icon(
        name="ShooApp",
        icon=_create_icon_image(),
        title=f"ShooApp \u2014 {len(_get_apps())} apps",
    )

    icon._left_menu  = _build_app_menu(icon)
    icon._right_menu = _build_action_menu(icon)
    icon.menu        = icon._right_menu

    def setup(icon):
        icon.visible = True
        icon.notify("Left-click to browse apps, right-click for options.", "ShooApp ready")

        import ctypes
        import ctypes.wintypes

        WM_LBUTTONUP    = 0x0202
        WM_RBUTTONUP    = 0x0205
        NIN_SELECT      = 0x0400
        TPM_RIGHTALIGN  = 0x0008
        TPM_BOTTOMALIGN = 0x0020
        TPM_RETURNCMD   = 0x0100

        def _show_menu_for(menu):
            icon.menu = menu
            icon._update_menu()
            mh = getattr(icon, '_menu_handle', None)
            if not mh:
                return
            ctypes.windll.user32.SetForegroundWindow(icon._hwnd)
            point = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            hmenu, descriptors = mh
            index = ctypes.windll.user32.TrackPopupMenuEx(
                hmenu,
                TPM_RIGHTALIGN | TPM_BOTTOMALIGN | TPM_RETURNCMD,
                point.x, point.y,
                icon._menu_hwnd,
                None,
            )
            if index > 0:
                descriptors[index - 1](icon)

        def _patched_on_notify(wparam, lparam):
            if lparam in (WM_LBUTTONUP, NIN_SELECT):
                _show_menu_for(icon._left_menu)
            elif lparam == WM_RBUTTONUP:
                _show_menu_for(icon._right_menu)

        icon._on_notify = _patched_on_notify
        from pystray._util import win32 as _win32
        icon._message_handlers[_win32.WM_NOTIFY] = _patched_on_notify

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
