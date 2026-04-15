# WAPI — Watermark & Frame Desktop App
**Design Spec** | 2026-04-05

---

## Overview

**WAPI** is a Windows desktop application for adding watermarks and/or decorative frames to photos — single images or in batch. It is built with Python + PySide6 (Qt6) for the UI and Pillow for image processing. The result is a standalone `wapi.exe` with no installation required.

**Target user:** Nazir Sultani (sultani.de) — for branding photos before publishing online.

---

## Architecture

Four Python modules with clean separation of concerns:

| File | Responsibility |
|---|---|
| `main.py` | Entry point — creates QApplication, loads settings, launches MainWindow |
| `ui.py` | All PySide6 UI code: MainWindow, panels, thumbnail list, preview canvas, settings tabs |
| `processor.py` | Pure image processing via Pillow: apply watermark (text/logo), apply frame, save output |
| `settings.py` | Read/write `wapi_settings.json` — persists all user preferences between sessions |

Packaged via **PyInstaller** into a single `wapi.exe` (~40–60 MB).

---

## UI Layout

Three-column layout inside a single resizable window. Dark professional theme (dark grey background, white text, orange accent color).

```
┌──────────────────────────────────────────────────────────┐
│  WAPI                                          [_ □ ✕]   │
├─────────────┬──────────────────────┬─────────────────────┤
│ IMAGE LIST  │    LIVE PREVIEW      │  SETTINGS PANEL     │
│             │                      │  [Wasserzeichen]    │
│ [+ Bilder]  │   ┌──────────────┐   │  [Rahmen]           │
│ [Alle weg]  │   │              │   │  [Export]           │
│             │   │   Vorschau   │   │                     │
│ thumb1.jpg  │   │              │   │  ... controls ...   │
│ thumb2.jpg  │   └──────────────┘   │                     │
│ thumb3.jpg  │  800×600 | foto.jpg  │                     │
│    ...      │                      │                     │
├─────────────┴──────────────────────┴─────────────────────┤
│  [████████████░░░░░░] 12/47 Bilder    [Jetzt verarbeiten]│
└──────────────────────────────────────────────────────────┘
```

**Left panel — Image List (fixed width ~200px):**
- "Bilder hinzufügen" button (opens file dialog, multi-select, JPG/PNG/WebP/TIFF)
- "Alle entfernen" button
- Drag & drop zone for files and folders
- Scrollable thumbnail list; clicking a thumbnail shows it in the preview
- Each item shows filename and resolution

**Center panel — Live Preview (flexible width):**
- Displays the currently selected image with watermark/frame applied in real time
- Updates within ~300ms of any settings change (debounced)
- Shows image dimensions and filename below the preview

**Right panel — Settings (fixed width ~280px):**
- Three tabs: `Wasserzeichen` | `Rahmen` | `Export`

**Bottom bar:**
- Progress bar (hidden when idle, visible during batch export)
- "Jetzt verarbeiten" button (disabled when no images loaded or no output folder selected)
- Status label: "12 von 47 Bildern verarbeitet…" or "Fertig."

---

## Settings Panel — Tab 1: Wasserzeichen

Toggle to enable/disable watermark entirely.

**Two sub-modes (radio buttons):**

*Text-Modus:*
- Text input field (default: `sultani.de`)
- Font family dropdown (populated from installed Windows fonts)
- Font size (spinbox, 8–200pt)
- Font color (color picker)
- Opacity slider (0–100%)

*Logo-Modus:*
- "Logo-Datei wählen" button (loads PNG/SVG)
- Logo size as % of image width (slider, 5–50%)
- Opacity slider (0–100%)

**Position (shared for both modes):**
- 3×3 anchor grid (top-left, top-center, top-right, middle-left, center, middle-right, bottom-left, bottom-center, bottom-right)
- Extra options: "Diagonal" (text/logo repeated diagonally across entire image at ~30° angle) and "Kacheln" (tiled pattern across entire image)
- Padding offset from edge (spinbox, px)

---

## Settings Panel — Tab 2: Rahmen

Toggle to enable/disable frame entirely.

**Frame style (radio buttons):**

*Einfacher Rahmen:*
- Color picker
- Border width (spinbox, 1–200px)

*Passepartout-Stil:*
- Outer color (white or black or custom)
- Border thickness as % of image dimension (slider, 1–20%)
- Optional text label below image (e.g. `sultani.de` as a signature)
  - Font, size, color for label text

**Note:** Watermark and frame can be active simultaneously.

---

## Settings Panel — Tab 3: Export

- Output format: JPG | PNG | WebP (radio buttons)
- JPG quality slider (1–100, visible only when JPG selected, default 90)
- Output folder: text field + "Ordner wählen" button
- Filename suffix: input field (default: `_wapi`), result preview shown: `foto.jpg → foto_wapi.jpg`

---

## Processor Module (`processor.py`)

Pure functions — no UI dependencies, fully testable.

```python
def apply_watermark(image: Image, config: WatermarkConfig) -> Image: ...
def apply_frame(image: Image, config: FrameConfig) -> Image: ...
def save_image(image: Image, output_path: Path, format: str, quality: int) -> None: ...
def process_batch(image_paths: list[Path], wm_config, frame_config, export_config, progress_callback) -> None: ...
```

Processing pipeline per image: load → apply frame → apply watermark → save. Order matters: frame first, watermark on top.

For diagonal/tiled watermarks, the text/logo is drawn onto a transparent overlay layer the size of the image, then composited onto the photo. Rotation via Pillow's `Image.rotate()` with expand=False.

---

## Settings Persistence (`settings.py`)

Saved to `wapi_settings.json` in the same directory as the `.exe`. Contains all watermark, frame, and export settings. Loaded on startup; saved on every settings change (debounced 1s) and on app close.

```json
{
  "watermark": {
    "enabled": true,
    "mode": "text",
    "text": "sultani.de",
    "font": "Arial",
    "size": 36,
    "color": "#FFFFFF",
    "opacity": 60,
    "position": "bottom-right",
    "padding": 20,
    "logo_path": null,
    "logo_size_pct": 15
  },
  "frame": {
    "enabled": false,
    "style": "simple",
    "color": "#000000",
    "width_px": 20,
    "passe_color": "#FFFFFF",
    "passe_pct": 5,
    "passe_label": "sultani.de",
    "passe_label_font": "Arial",
    "passe_label_size": 18,
    "passe_label_color": "#333333"
  },
  "export": {
    "format": "jpg",
    "quality": 90,
    "output_folder": "",
    "suffix": "_wapi"
  }
}
```

---

## Error Handling

- Corrupt or unreadable images: skipped during batch, shown with error icon in thumbnail list
- Missing logo file: warning shown, watermark mode falls back to text
- Output folder not writable: error dialog before processing starts
- Processing errors per image: logged to `wapi_errors.log` next to the exe, processing continues for remaining images

---

## Packaging

```
wapi/
  main.py
  ui.py
  processor.py
  settings.py
  assets/
    icon.ico          # App icon
    default_logo.png  # Placeholder logo
  requirements.txt    # PySide6, Pillow, pyinstaller
  build.bat           # One-command build: pyinstaller --onefile --windowed --icon=assets/icon.ico main.py
```

Output: `dist/wapi.exe` — single file, no installation needed.

---

## Dependencies

| Package | Version | License |
|---|---|---|
| PySide6 | ≥6.6 | LGPL v3 |
| Pillow | ≥10.0 | HPND (free) |
| PyInstaller | ≥6.0 | GPL + bootloader exception (free for commercial use) |

All free, no cost, no subscription.
