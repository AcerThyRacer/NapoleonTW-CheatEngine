# Linux Setup Guide

This project supports two Linux play styles for **Napoleon: Total War**:

- **Native Linux / Feral port**: the trainer prefers the direct `/proc/<pid>/mem` backend.
- **Steam Proton / Wine**: the trainer prefers the Windows-oriented backends first, then falls back to `/proc`.

## Supported Linux Environments

- Ubuntu / Debian
- Fedora
- Arch Linux
- Steam installed natively or through Flatpak
- X11 and XWayland sessions

Wayland is supported for launching the app and scanning memory, but **global hotkeys are still limited by Wayland security rules**. For the best trainer experience, use an **X11 session** or run the game through **XWayland**.

## 1. Install System Packages

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-pyqt6 python3-psutil
```

### Fedora

```bash
sudo dnf install python3 python3-pip python3-qt6 python3-psutil
```

### Arch Linux

```bash
sudo pacman -S python python-pip python-pyqt6 python-psutil
```

## 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[gui,memory]"
```

If you also want the repository test/build tools:

```bash
pip install -e ".[dev,gui,memory]"
```

## 3. Run the Cheat Engine

### GUI

```bash
napoleon-cheat --gui
```

### CLI

```bash
napoleon-cheat --cli
```

### Trainer-only mode

```bash
napoleon-cheat --trainer
```

## 4. Linux Memory Access Permissions

Linux memory tools usually need one of these:

1. **Run as root** for the session:

   ```bash
   sudo napoleon-cheat --gui
   ```

2. **Grant `CAP_SYS_PTRACE`** to the Python interpreter or packaged executable:

   ```bash
   sudo setcap cap_sys_ptrace=eip "$(readlink -f "$(which python3)")"
   ```

   If you build a standalone binary, apply the capability to that binary instead.

3. **Temporarily relax `ptrace_scope`** on a personal gaming machine:

   ```bash
   echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope
   ```

   This is less secure than using `CAP_SYS_PTRACE`, so do not leave it enabled on shared or hardened systems.

## 5. Steam / Game Detection Notes

The project looks for Napoleon in common Linux locations, including:

- `~/.local/share/Steam`
- `~/.steam/steam`
- `~/.steam/steamapps`
- `~/.var/app/com.valvesoftware.Steam/.local/share/Steam` (Flatpak Steam)
- `/run/host/home/<user>/.local/share/Steam` (Flatpak host mapping)

It also supports:

- **Feral native save/config paths**
- **Proton compatdata paths** for Steam App ID `34030`

## 6. Wayland Hotkey Notes

The trainer uses `pynput` for global hotkeys.

- **X11 / XWayland**: full global hotkey support is expected.
- **Wayland**: hotkey capture may be partial or unavailable because Wayland blocks system-wide key interception for security reasons.

If hotkeys do not trigger under Wayland, switch to an **X11 session** or launch the game in an environment that uses **XWayland**.

## 7. Quick Validation

After setup, you can verify the repository tests:

```bash
python -m pytest tests/ -q
```
