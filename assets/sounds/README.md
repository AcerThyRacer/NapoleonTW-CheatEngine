# Napoleon TW Cheat Engine — Sound Assets

This directory holds sound effects for the Napoleon control panel.

## Required Sound Files

| File                  | Description                             |
|-----------------------|-----------------------------------------|
| `cheat_activate.wav`  | Played when a cheat is activated        |
| `cheat_deactivate.wav`| Played when a cheat is deactivated      |
| `victory_fanfare.wav` | Played on mass cheat activation / win   |

Place `.wav` files (PCM, 44.1 kHz, 16-bit) in this directory.
The `SoundEffectPlayer` in `src/gui/animated_components.py` will discover
them automatically at runtime.
