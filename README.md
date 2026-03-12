# ShooApp

A lightweight Windows system tray app for uninstalling programs — without opening Control Panel.

## What it does

- Sits in the system tray
- **Left-click** → opens a dark floating panel with all installed apps
  - Search bar with live filtering
  - Table view: Application, Version, Installed date
  - Double-click or press Enter to launch the uninstaller
  - Refresh button to update the list
- **Right-click** → Quit
- **Hover** over the tray icon → tooltip refreshes and shows current app count

## Screenshot

> Left-click the tray icon to open the dark app panel.

```
┌─────────────────────────────────────────────┐
│ 🔴 ShooApp                                  │
├─────────────────────────────────────────────┤
│ 210 apps installed                          │
│ 🔍 Search apps...                           │
├──────────────────────┬──────────┬───────────┤
│ Application          │ Version  │ Installed │
├──────────────────────┼──────────┼───────────┤
│ Adobe Acrobat        │ 24.0     │ 01.03.2025│
│ Visual Studio Code   │ 1.87     │ 15.02.2025│
│ ...                  │          │           │
├─────────────────────────────────────────────┤
│ [🔄 Refresh]                                │
└─────────────────────────────────────────────┘
```

## Requirements

- Windows 10 / 11

## Run (from source)

```bash
pip install -r requirements.txt
pythonw shoo.py
```

## Build EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ShooApp --icon=shooapp.ico shoo.py
```

Output: `dist\ShooApp.exe` — no installation needed, runs standalone.
