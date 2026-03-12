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
                                install_date = ""
                                try:
                                    raw = winreg.QueryValueEx(sub, "InstallDate")[0].strip()
                                    if len(raw) == 8 and raw.isdigit():
                                        install_date = f"{raw[6:]}.{raw[4:6]}.{raw[:4]}"
                                except OSError:
                                    pass
                                seen.add(name)
                                apps.append({
                                    "name": name,
                                    "version": version,
                                    "uninstall": uninstall,
                                    "publisher": publisher,
                                    "install_date": install_date,
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

    all_apps = [a for g in groups.values() for a in g]
    max_ver = max((len(a["version"]) for a in all_apps if a["version"]), default=10)

    items = []
    for pub in sorted(groups, key=str.lower):
        app_items = []
        for app in sorted(groups[pub], key=lambda x: x["name"].lower()):
            ver  = app["version"].ljust(max_ver) if app["version"] else " " * max_ver
            date = app["install_date"] if app["install_date"] else " " * 10
            right = f"{ver}    {date}"
            label = f"Remove \u2192  {app['name']}\t{right}"
            app_items.append(pystray.MenuItem(label, make_uninstall(app)))
        items.append(pystray.MenuItem(pub, pystray.Menu(*app_items)))

    return items


def _build_app_menu(icon: pystray.Icon) -> pystray.Menu:
    return pystray.Menu(*_build_app_items(icon))


def _show_panel(icon: pystray.Icon) -> None:
    BG       = "#1e1e1e"
    BG2      = "#2a2a2a"
    ENTRY_BG = "#2d2d2d"
    FG       = "#ffffff"
    FG2      = "#aaaaaa"
    ACCENT   = "#d23228"
    BTN_BG   = "#2d2d2d"
    BTN_HV   = "#3d3d3d"
    W        = 340

    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.configure(bg=BG)
    win.attributes("-topmost", True)

    # ── Header ──────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=BG, padx=14, pady=10)
    hdr.pack(fill="x")
    tk.Label(hdr, text="🗑  ShooApp", bg=BG, fg=FG,
             font=("Segoe UI", 12, "bold")).pack(side="left")

    # ── Separator ────────────────────────────────────────────────────────────
    tk.Frame(win, bg="#333333", height=1).pack(fill="x")

    # ── Count label ──────────────────────────────────────────────────────────
    count_var = tk.StringVar(value=f"{len(_get_apps())} apps installed")
    tk.Label(win, textvariable=count_var, bg=BG, fg=FG2,
             font=("Segoe UI", 9), padx=14, pady=6).pack(anchor="w")

    # ── Search ───────────────────────────────────────────────────────────────
    sf = tk.Frame(win, bg=BG2, padx=10, pady=6)
    sf.pack(fill="x", padx=10, pady=(0, 6))
    tk.Label(sf, text="🔍", bg=BG2, fg=FG2, font=("Segoe UI", 9)).pack(side="left")
    search_var = tk.StringVar()
    entry = tk.Entry(sf, textvariable=search_var, bg=BG2, fg=FG,
                     insertbackground=FG, relief="flat",
                     font=("Segoe UI", 10), bd=0)
    entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

    PLACEHOLDER = "Search apps…"
    entry.insert(0, PLACEHOLDER)
    entry.config(fg=FG2)

    def on_focus_in(e):
        if entry.get() == PLACEHOLDER:
            entry.delete(0, "end")
            entry.config(fg=FG)

    def on_focus_out_entry(e):
        if not entry.get():
            entry.insert(0, PLACEHOLDER)
            entry.config(fg=FG2)

    entry.bind("<FocusIn>",  on_focus_in)
    entry.bind("<FocusOut>", on_focus_out_entry)

    # ── Separator ────────────────────────────────────────────────────────────
    tk.Frame(win, bg="#333333", height=1).pack(fill="x", padx=0, pady=(4, 0))

    # ── Buttons ──────────────────────────────────────────────────────────────
    bf = tk.Frame(win, bg=BG, padx=10, pady=10)
    bf.pack(fill="x")

    def make_btn(parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=BTN_BG, fg=FG, activebackground=BTN_HV,
                      activeforeground=FG, relief="flat", bd=0,
                      font=("Segoe UI", 9), padx=12, pady=6, cursor="hand2")
        b.pack(side="left", padx=(0, 6))
        return b

    def do_refresh():
        count_var.set("Refreshing…")
        def _r():
            _refresh_cache()
            icon._left_menu = _build_app_menu(icon)
            icon.title = f"ShooApp \u2014 {len(_get_apps())} apps"
            count_var.set(f"{len(_get_apps())} apps installed")
        threading.Thread(target=_r, daemon=True).start()

    def do_quit():
        win.destroy()
        root.destroy()
        icon.stop()

    make_btn(bf, "🔄  Refresh", do_refresh)
    make_btn(bf, "✕  Quit",    do_quit)

    # ── Position near cursor, above taskbar ──────────────────────────────────
    win.update_idletasks()
    h = win.winfo_reqheight()
    import ctypes
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = min(pt.x, sw - W - 4)
    y = max(pt.y - h - 4, 0)
    win.geometry(f"{W}x{h}+{x}+{y}")

    # Close on focus loss
    def on_focus_out(e):
        if e.widget is win:
            win.destroy()
            root.destroy()

    win.bind("<FocusOut>", on_focus_out)
    win.focus_force()
    entry.focus_set()
    root.mainloop()


def _force_refresh(icon: pystray.Icon) -> None:
    _refresh_cache()
    icon._left_menu = _build_app_menu(icon)
    icon.menu       = icon._left_menu
    count = len(_get_apps())
    icon.title = f"ShooApp \u2014 {count} apps"


# ---------------------------------------------------------------------------
# Tray icon image
# ---------------------------------------------------------------------------

def _create_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Solid red full-fill background
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=10, fill=(210, 50, 40, 255))

    # Bold white X filling most of the icon
    m = 10
    lw = 10
    draw.line([m, m, size - m, size - m], fill=(255, 255, 255, 255), width=lw)
    draw.line([size - m, m, m, size - m], fill=(255, 255, 255, 255), width=lw)

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

    icon._left_menu = _build_app_menu(icon)
    icon.menu       = icon._left_menu

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
                _refresh_cache()
                icon._left_menu = _build_app_menu(icon)
                icon.title = f"ShooApp \u2014 {len(_get_apps())} apps"
                _show_menu_for(icon._left_menu)
            elif lparam == WM_RBUTTONUP:
                threading.Thread(target=_show_panel, args=(icon,), daemon=True).start()

        icon._on_notify = _patched_on_notify
        from pystray._util import win32 as _win32
        icon._message_handlers[_win32.WM_NOTIFY] = _patched_on_notify

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
