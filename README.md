# ShooApp

A lightweight Windows system tray app for uninstalling programs — without opening Control Panel.

## What it does

- Sits in the system tray
- **Left-click** → browse all installed apps grouped by publisher
- Hover over a publisher to see its apps
- Click **Remove AppName** to uninstall it
- **Right-click** → Refresh list / Quit

## Screenshot

> Left-click the tray icon to open the app list grouped by publisher.

```
▶ Adobe Inc.
      Remove  Adobe Acrobat  24.0
▶ Microsoft Corporation
      Remove  Visual Studio Code  1.87
▶ (Other)
      Remove  SomeApp  1.0
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
