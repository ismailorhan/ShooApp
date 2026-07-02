# ShooApp

A lightweight Windows system tray app for uninstalling programs — without opening Control Panel.

## What it does

- Sits in the system tray
- **Left-click** → opens a dark floating panel with all installed apps
  - Search bar with live filtering
  - Table view: Application, Version, Installed date
  - **Checkbox column** for selecting multiple apps at once
  - Double-click or press Enter to uninstall a single app
- **Right-click** → menu with auto-start toggle and Quit
- **Hover** over the tray icon → tooltip refreshes and shows current app count

### Uninstalling

- Each uninstall tries a **silent `winget uninstall`** first. If winget can't
  handle it, ShooApp falls back to the app's own uninstaller (including
  ClickOnce → sibling-MSI handling for Windows 11).
- **Multi-select:** check any number of rows, then hit the red **Uninstall (N)**
  button. Checked apps are removed **one at a time** (sequential — never two
  installers at once) and progress is shown right on the tray icon (a count
  badge) plus start/finish toast notifications.

### Keyboard & panel behaviour

- **Space** — toggle the checkbox on the focused row
- **↓ (from search)** — jump into the list; arrows move, Space checks
- **F5** — refresh the list and return focus to the search box
- **Tab** — cycles between the search box and the bottom buttons
- **Esc** or the **✕** button — always close the panel
- Clicking outside keeps the panel open when a search query is typed or rows
  are checked, so nothing is lost by accident
- The panel anchors to the work-area bottom-right, like standard tray flyouts

## Screenshot

> Left-click the tray icon to open the dark app panel.

```
┌─────────────────────────────────────────────────────┐
│ 🗑️ ShooApp                                       ✕ │
├─────────────────────────────────────────────────────┤
│ 210 apps installed                                  │
│ 🔍 Search apps...                                   │
├───┬──────────────────────┬──────────┬───────────────┤
│   │ Application          │ Version  │ Installed     │
├───┼──────────────────────┼──────────┼───────────────┤
│ ☑ │ Adobe Acrobat        │ 24.0     │ 01.03.2025    │
│ ☐ │ Visual Studio Code   │ 1.87     │ 15.02.2025    │
│ ☑ │ ...                  │          │               │
├─────────────────────────────────────────────────────┤
│ [🗑️ Uninstall (2)]  [🔄 Refresh]  [🧩 Prog. & Feat.]│
└─────────────────────────────────────────────────────┘
```

## Requirements

- Windows 10 / 11
- Admin rights (uninstallers usually need them). The compiled exe ships with
  a `requireAdministrator` manifest, so Windows triggers UAC automatically.

## Install (end users)

Use the installer produced by `installer.iss`:

```
dist\ShooAppSetup.exe
```

The wizard offers two optional tasks:

- **Start automatically when Windows starts** — creates a per-user Startup
  shortcut. Checked by default.
- **Create a desktop shortcut** — off by default.

Auto-start can also be toggled later from the tray icon's right-click menu
(**Windows başladığında başlat**).

## Run (from source — dev)

```bash
pip install -r requirements.txt
pythonw shoo.py
```

## Build EXE

```bat
build.bat
```

`build.bat` installs PyInstaller, cleans previous artefacts, and produces
`dist\ShooApp.exe` with the admin manifest embedded (`--uac-admin`).

## Build Installer

1. Run `build.bat` to produce `dist\ShooApp.exe`.
2. Open `installer.iss` in Inno Setup Compiler (or run `iscc installer.iss`).
3. Output: `dist\ShooAppSetup.exe`.

## Configuration

The auto-start preference is stored at
`%APPDATA%\ShooApp\config.json`.
