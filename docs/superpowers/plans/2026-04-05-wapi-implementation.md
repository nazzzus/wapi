# WAPI — Watermark & Frame App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build WAPI, a Windows desktop app for adding watermarks and frames to photos (single or batch), with live preview, built on Python + PySide6 + Pillow.

**Architecture:** Single-window PySide6 app with three panels (image list / live preview / settings). Core image processing is isolated in `processor.py` with no UI dependencies. Settings are persisted to `wapi_settings.json` via `settings.py`.

**Tech Stack:** Python 3.11+, PySide6 6.6+, Pillow 10.0+, pytest + pytest-qt, PyInstaller 6+

**Spec:** `docs/superpowers/specs/2026-04-05-wapi-watermark-app-design.md`

---

## File Map

| File | Purpose |
|---|---|
| `main.py` | Entry point — creates QApplication, loads settings, launches MainWindow |
| `ui.py` | Full PySide6 UI: MainWindow, all panels, tabs, preview canvas, signals |
| `processor.py` | Pure image processing: watermark (text+logo), frame (simple+passepartout), save, batch |
| `settings.py` | Dataclasses for all config + JSON read/write |
| `assets/icon.ico` | App icon |
| `requirements.txt` | All dependencies |
| `build.bat` | One-command PyInstaller build |
| `tests/test_processor.py` | Unit tests for processor.py |
| `tests/test_settings.py` | Unit tests for settings.py |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `assets/` (empty directory placeholder)

- [ ] **Step 1: Create project structure**

```bash
cd /path/to/wapi
mkdir -p tests assets
touch tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
PySide6>=6.6.0
Pillow>=10.0.0
pytest>=8.0.0
pytest-qt>=4.4.0
pyinstaller>=6.0.0
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 4: Verify installs**

```bash
python -c "import PySide6; import PIL; print('OK')"
```

Expected output: `OK`

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt tests/__init__.py
git commit -m "chore: project setup with dependencies"
```

---

## Task 2: Settings Module

**Files:**
- Create: `settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_settings.py
import json
import pytest
from pathlib import Path
from settings import Settings, WatermarkConfig, FrameConfig, ExportConfig, load_settings, save_settings

def test_default_settings_watermark():
    s = Settings()
    assert s.watermark.enabled == True
    assert s.watermark.mode == "text"
    assert s.watermark.text == "sultani.de"
    assert s.watermark.opacity == 60
    assert s.watermark.position == "bottom-right"

def test_default_settings_frame():
    s = Settings()
    assert s.frame.enabled == False
    assert s.frame.style == "simple"

def test_default_settings_export():
    s = Settings()
    assert s.export.format == "jpg"
    assert s.export.quality == 90
    assert s.export.suffix == "_wapi"

def test_save_and_load_roundtrip(tmp_path):
    config_path = tmp_path / "wapi_settings.json"
    s = Settings()
    s.watermark.text = "myphoto.de"
    s.export.quality = 75
    save_settings(s, config_path)
    loaded = load_settings(config_path)
    assert loaded.watermark.text == "myphoto.de"
    assert loaded.export.quality == 75

def test_load_missing_file_returns_defaults(tmp_path):
    config_path = tmp_path / "nonexistent.json"
    s = load_settings(config_path)
    assert s.watermark.text == "sultani.de"

def test_load_partial_file_fills_defaults(tmp_path):
    config_path = tmp_path / "wapi_settings.json"
    config_path.write_text(json.dumps({"watermark": {"text": "custom"}}))
    s = load_settings(config_path)
    assert s.watermark.text == "custom"
    assert s.watermark.opacity == 60  # default preserved
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_settings.py -v
```

Expected: `ImportError: No module named 'settings'`

- [ ] **Step 3: Implement settings.py**

```python
# settings.py
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class WatermarkConfig:
    enabled: bool = True
    mode: str = "text"           # "text" | "logo"
    text: str = "sultani.de"
    font: str = "Arial"
    size: int = 36
    color: str = "#FFFFFF"
    opacity: int = 60            # 0-100
    position: str = "bottom-right"  # grid key or "diagonal" | "tiles"
    padding: int = 20
    logo_path: str | None = None
    logo_size_pct: int = 15      # % of image width


@dataclass
class FrameConfig:
    enabled: bool = False
    style: str = "simple"        # "simple" | "passepartout"
    color: str = "#000000"
    width_px: int = 20
    passe_color: str = "#FFFFFF"
    passe_pct: int = 5           # % of shorter image dimension
    passe_label: str = "sultani.de"
    passe_label_font: str = "Arial"
    passe_label_size: int = 18
    passe_label_color: str = "#333333"


@dataclass
class ExportConfig:
    format: str = "jpg"          # "jpg" | "png" | "webp"
    quality: int = 90
    output_folder: str = ""
    suffix: str = "_wapi"


@dataclass
class Settings:
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    frame: FrameConfig = field(default_factory=FrameConfig)
    export: ExportConfig = field(default_factory=ExportConfig)


def _merge(dataclass_type, saved: dict) -> object:
    """Create a dataclass instance, filling missing keys with defaults."""
    defaults = dataclass_type()
    for key, value in saved.items():
        if hasattr(defaults, key):
            setattr(defaults, key, value)
    return defaults


def load_settings(path: Path) -> Settings:
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        s = Settings()
        if "watermark" in data:
            s.watermark = _merge(WatermarkConfig, data["watermark"])
        if "frame" in data:
            s.frame = _merge(FrameConfig, data["frame"])
        if "export" in data:
            s.export = _merge(ExportConfig, data["export"])
        return s
    except (json.JSONDecodeError, TypeError):
        return Settings()


def save_settings(settings: Settings, path: Path) -> None:
    path.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_settings.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add settings.py tests/test_settings.py
git commit -m "feat: settings module with JSON persistence"
```

---

## Task 3: Processor — Text Watermark

**Files:**
- Create: `processor.py`
- Create: `tests/test_processor.py`

- [ ] **Step 1: Write failing tests for text watermark**

```python
# tests/test_processor.py
import pytest
from PIL import Image, ImageDraw
from pathlib import Path
from processor import apply_watermark, apply_frame, save_image
from settings import WatermarkConfig, FrameConfig


def make_test_image(width=800, height=600, color=(100, 149, 237)) -> Image.Image:
    """Create a solid-colour test image."""
    return Image.new("RGB", (width, height), color)


# --- TEXT WATERMARK TESTS ---

def test_text_watermark_returns_image():
    img = make_test_image()
    cfg = WatermarkConfig(enabled=True, mode="text", text="test", opacity=80, position="bottom-right")
    result = apply_watermark(img, cfg)
    assert isinstance(result, Image.Image)
    assert result.size == img.size

def test_text_watermark_does_not_modify_original():
    img = make_test_image()
    original_pixels = list(img.getdata())
    cfg = WatermarkConfig(enabled=True, mode="text", text="test", opacity=80, position="bottom-right")
    apply_watermark(img, cfg)
    assert list(img.getdata()) == original_pixels

def test_watermark_disabled_returns_unchanged_image():
    img = make_test_image()
    original_pixels = list(img.getdata())
    cfg = WatermarkConfig(enabled=False)
    result = apply_watermark(img, cfg)
    assert list(result.getdata()) == original_pixels

def test_text_watermark_all_positions():
    positions = [
        "top-left", "top-center", "top-right",
        "middle-left", "center", "middle-right",
        "bottom-left", "bottom-center", "bottom-right",
        "diagonal", "tiles"
    ]
    img = make_test_image()
    for pos in positions:
        cfg = WatermarkConfig(enabled=True, mode="text", text="W", opacity=50, position=pos)
        result = apply_watermark(img, cfg)
        assert result.size == img.size, f"Failed for position: {pos}"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_processor.py -v
```

Expected: `ImportError: No module named 'processor'`

- [ ] **Step 3: Implement processor.py — text watermark**

```python
# processor.py
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from settings import WatermarkConfig, FrameConfig, ExportConfig


# ── Helpers ────────────────────────────────────────────────────────────────

def _load_font(font_name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a named font; fall back to Pillow default."""
    try:
        return ImageFont.truetype(font_name, size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


def _hex_to_rgba(hex_color: str, opacity: int) -> tuple[int, int, int, int]:
    """Convert #RRGGBB + opacity (0-100) to RGBA tuple."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(opacity / 100 * 255)
    return r, g, b, a


POSITION_MAP = {
    "top-left":      (0.0, 0.0),
    "top-center":    (0.5, 0.0),
    "top-right":     (1.0, 0.0),
    "middle-left":   (0.0, 0.5),
    "center":        (0.5, 0.5),
    "middle-right":  (1.0, 0.5),
    "bottom-left":   (0.0, 1.0),
    "bottom-center": (0.5, 1.0),
    "bottom-right":  (1.0, 1.0),
}


def _anchor_for_position(pos: str) -> str:
    """Return Pillow anchor string for a position key."""
    anchors = {
        "top-left": "lt", "top-center": "mt", "top-right": "rt",
        "middle-left": "lm", "center": "mm", "middle-right": "rm",
        "bottom-left": "lb", "bottom-center": "mb", "bottom-right": "rb",
    }
    return anchors.get(pos, "rb")


# ── Text watermark helpers ──────────────────────────────────────────────────

def _draw_text_once(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int],
                    font, color_rgba: tuple, anchor: str) -> None:
    draw.text(xy, text, font=font, fill=color_rgba, anchor=anchor)


def _draw_text_diagonal(base: Image.Image, text: str, font,
                         color_rgba: tuple) -> Image.Image:
    """Draw repeating diagonal text across the full image."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    step_x = tw + 80
    step_y = th + 60
    angle = 30
    for row in range(-2, base.height // step_y + 3):
        for col in range(-2, base.width // step_x + 3):
            x = col * step_x + (row % 2) * step_x // 2
            y = row * step_y
            txt_img = Image.new("RGBA", (tw + 20, th + 20), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((10, 10), text, font=font, fill=color_rgba)
            rotated = txt_img.rotate(angle, expand=True)
            overlay.paste(rotated, (x, y), rotated)
    result = base.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


def _draw_text_tiles(base: Image.Image, text: str, font,
                      color_rgba: tuple) -> Image.Image:
    """Draw tiled text across the full image."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 40, 30
    for y in range(0, base.height, th + pad_y):
        for x in range(0, base.width, tw + pad_x):
            draw.text((x, y), text, font=font, fill=color_rgba, anchor="lt")
    result = base.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


# ── Public API ──────────────────────────────────────────────────────────────

def apply_watermark(image: Image.Image, cfg: WatermarkConfig) -> Image.Image:
    """Return a new image with the watermark applied. Original is never modified."""
    if not cfg.enabled:
        return image.copy()

    if cfg.mode == "text":
        return _apply_text_watermark(image, cfg)
    else:
        return _apply_logo_watermark(image, cfg)


def _apply_text_watermark(image: Image.Image, cfg: WatermarkConfig) -> Image.Image:
    font = _load_font(cfg.font, cfg.size)
    color_rgba = _hex_to_rgba(cfg.color, cfg.opacity)

    if cfg.position == "diagonal":
        return _draw_text_diagonal(image, cfg.text, font, color_rgba)
    if cfg.position == "tiles":
        return _draw_text_tiles(image, cfg.text, font, color_rgba)

    result = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rel_x, rel_y = POSITION_MAP.get(cfg.position, (1.0, 1.0))
    x = int(rel_x * image.width)
    y = int(rel_y * image.height)
    # Apply padding inward from edges
    pad = cfg.padding
    if rel_x == 0.0:
        x += pad
    elif rel_x == 1.0:
        x -= pad
    if rel_y == 0.0:
        y += pad
    elif rel_y == 1.0:
        y -= pad

    anchor = _anchor_for_position(cfg.position)
    draw.text((x, y), cfg.text, font=font, fill=color_rgba, anchor=anchor)

    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_processor.py -v
```

Expected: All 4 text watermark tests PASS.

- [ ] **Step 5: Commit**

```bash
git add processor.py tests/test_processor.py
git commit -m "feat: processor text watermark (grid, diagonal, tiles)"
```

---

## Task 4: Processor — Logo Watermark

**Files:**
- Modify: `processor.py` (add `_apply_logo_watermark`)
- Modify: `tests/test_processor.py`

- [ ] **Step 1: Add logo watermark tests**

Append to `tests/test_processor.py`:

```python
# --- LOGO WATERMARK TESTS ---

def test_logo_watermark_returns_correct_size(tmp_path):
    img = make_test_image(800, 600)
    logo_path = tmp_path / "logo.png"
    logo = Image.new("RGBA", (200, 100), (255, 0, 0, 180))
    logo.save(logo_path, "PNG")
    cfg = WatermarkConfig(enabled=True, mode="logo", logo_path=str(logo_path),
                          logo_size_pct=20, opacity=80, position="bottom-right")
    result = apply_watermark(img, cfg)
    assert result.size == (800, 600)

def test_logo_watermark_missing_file_returns_copy():
    img = make_test_image()
    cfg = WatermarkConfig(enabled=True, mode="logo", logo_path="/nonexistent/logo.png",
                          logo_size_pct=15, opacity=80, position="center")
    result = apply_watermark(img, cfg)
    assert result.size == img.size  # fallback: returns copy without crashing
```

- [ ] **Step 2: Run to verify new tests fail**

```bash
pytest tests/test_processor.py::test_logo_watermark_returns_correct_size -v
```

Expected: FAIL — `_apply_logo_watermark` not implemented yet.

- [ ] **Step 3: Implement `_apply_logo_watermark` in processor.py**

Add this function inside `processor.py` after `_apply_text_watermark`:

```python
def _apply_logo_watermark(image: Image.Image, cfg: WatermarkConfig) -> Image.Image:
    if not cfg.logo_path:
        return image.copy()
    try:
        logo = Image.open(cfg.logo_path).convert("RGBA")
    except (OSError, FileNotFoundError):
        return image.copy()

    # Scale logo to logo_size_pct % of image width
    target_w = int(image.width * cfg.logo_size_pct / 100)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    # Apply opacity
    if cfg.opacity < 100:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * cfg.opacity / 100))
        logo.putalpha(alpha)

    result = image.copy().convert("RGBA")

    if cfg.position in ("diagonal", "tiles"):
        # For logo, diagonal/tiles: repeat logo across image
        overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
        step_x = target_w + 60
        step_y = target_h + 50
        for y in range(0, image.height, step_y):
            for x in range(0, image.width, step_x):
                overlay.paste(logo, (x, y), logo)
        result = Image.alpha_composite(result, overlay)
    else:
        rel_x, rel_y = POSITION_MAP.get(cfg.position, (1.0, 1.0))
        pad = cfg.padding
        x = int(rel_x * image.width - rel_x * target_w)
        y = int(rel_y * image.height - rel_y * target_h)
        # Clamp with padding
        x = max(pad, min(x, image.width - target_w - pad))
        y = max(pad, min(y, image.height - target_h - pad))
        result.paste(logo, (x, y), logo)

    return result.convert("RGB")
```

- [ ] **Step 4: Run all processor tests**

```bash
pytest tests/test_processor.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add processor.py tests/test_processor.py
git commit -m "feat: processor logo watermark"
```

---

## Task 5: Processor — Frames

**Files:**
- Modify: `processor.py` (add `apply_frame`)
- Modify: `tests/test_processor.py`

- [ ] **Step 1: Add frame tests**

Append to `tests/test_processor.py`:

```python
# --- FRAME TESTS ---

def test_simple_frame_increases_dimensions():
    img = make_test_image(800, 600)
    cfg = FrameConfig(enabled=True, style="simple", color="#000000", width_px=20)
    result = apply_frame(img, cfg)
    assert result.size == (840, 640)

def test_simple_frame_disabled_returns_same_size():
    img = make_test_image(800, 600)
    cfg = FrameConfig(enabled=False)
    result = apply_frame(img, cfg)
    assert result.size == (800, 600)

def test_passepartout_frame_increases_dimensions():
    img = make_test_image(800, 600)
    cfg = FrameConfig(enabled=True, style="passepartout", passe_color="#FFFFFF",
                      passe_pct=5, passe_label="sultani.de",
                      passe_label_font="Arial", passe_label_size=18,
                      passe_label_color="#333333")
    result = apply_frame(img, cfg)
    # passe_pct=5 → border = 5% of min(800,600) = 30px each side
    border = int(min(800, 600) * 0.05)
    expected_w = 800 + 2 * border
    # height includes extra space for label below
    assert result.width == expected_w
    assert result.height > 600

def test_frame_does_not_modify_original():
    img = make_test_image(800, 600)
    original_size = img.size
    cfg = FrameConfig(enabled=True, style="simple", width_px=10)
    apply_frame(img, cfg)
    assert img.size == original_size
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_processor.py::test_simple_frame_increases_dimensions -v
```

Expected: FAIL — `apply_frame` not implemented.

- [ ] **Step 3: Implement `apply_frame` in processor.py**

Add after `apply_watermark`:

```python
def apply_frame(image: Image.Image, cfg: FrameConfig) -> Image.Image:
    """Return a new image with the frame applied. Original is never modified."""
    if not cfg.enabled:
        return image.copy()
    if cfg.style == "simple":
        return _apply_simple_frame(image, cfg)
    else:
        return _apply_passepartout_frame(image, cfg)


def _apply_simple_frame(image: Image.Image, cfg: FrameConfig) -> Image.Image:
    w, h = image.size
    border = cfg.width_px
    new_w, new_h = w + 2 * border, h + 2 * border
    h_val = cfg.color.lstrip("#")
    r, g, b = int(h_val[0:2], 16), int(h_val[2:4], 16), int(h_val[4:6], 16)
    canvas = Image.new("RGB", (new_w, new_h), (r, g, b))
    canvas.paste(image, (border, border))
    return canvas


def _apply_passepartout_frame(image: Image.Image, cfg: FrameConfig) -> Image.Image:
    w, h = image.size
    border = int(min(w, h) * cfg.passe_pct / 100)
    border = max(border, 1)

    h_val = cfg.passe_color.lstrip("#")
    r, g, b = int(h_val[0:2], 16), int(h_val[2:4], 16), int(h_val[4:6], 16)
    bg_color = (r, g, b)

    # Extra height at bottom for label text
    font = _load_font(cfg.passe_label_font, cfg.passe_label_size)
    label_padding = border // 2 if cfg.passe_label else 0
    label_height = cfg.passe_label_size + label_padding * 2 if cfg.passe_label else 0

    new_w = w + 2 * border
    new_h = h + 2 * border + label_height
    canvas = Image.new("RGB", (new_w, new_h), bg_color)
    canvas.paste(image, (border, border))

    if cfg.passe_label:
        draw = ImageDraw.Draw(canvas)
        lh_val = cfg.passe_label_color.lstrip("#")
        lr, lg, lb = int(lh_val[0:2], 16), int(lh_val[2:4], 16), int(lh_val[4:6], 16)
        label_x = new_w // 2
        label_y = h + border + label_padding
        draw.text((label_x, label_y), cfg.passe_label,
                  font=font, fill=(lr, lg, lb), anchor="mt")

    return canvas
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_processor.py -v
```

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add processor.py tests/test_processor.py
git commit -m "feat: processor simple frame and passepartout"
```

---

## Task 6: Processor — Save & Batch

**Files:**
- Modify: `processor.py` (add `save_image`, `process_batch`)
- Modify: `tests/test_processor.py`

- [ ] **Step 1: Add save and batch tests**

Append to `tests/test_processor.py`:

```python
# --- SAVE & BATCH TESTS ---

def test_save_image_jpg(tmp_path):
    img = make_test_image(400, 300)
    out = tmp_path / "out.jpg"
    save_image(img, out, "jpg", 85)
    assert out.exists()
    reloaded = Image.open(out)
    assert reloaded.format == "JPEG"

def test_save_image_png(tmp_path):
    img = make_test_image(400, 300)
    out = tmp_path / "out.png"
    save_image(img, out, "png", 90)
    assert out.exists()
    reloaded = Image.open(out)
    assert reloaded.format == "PNG"

def test_save_image_webp(tmp_path):
    img = make_test_image(400, 300)
    out = tmp_path / "out.webp"
    save_image(img, out, "webp", 80)
    assert out.exists()
    reloaded = Image.open(out)
    assert reloaded.format == "WEBP"

def test_process_batch_creates_output_files(tmp_path):
    from settings import WatermarkConfig, FrameConfig, ExportConfig
    # Create 3 test images
    input_paths = []
    for i in range(3):
        p = tmp_path / f"img{i}.jpg"
        make_test_image().save(p, "JPEG")
        input_paths.append(p)
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    wm_cfg = WatermarkConfig(enabled=True, mode="text", text="test", opacity=50)
    fr_cfg = FrameConfig(enabled=False)
    ex_cfg = ExportConfig(format="jpg", quality=85, output_folder=str(out_dir), suffix="_wapi")
    progress_calls = []
    process_batch(input_paths, wm_cfg, fr_cfg, ex_cfg,
                  progress_callback=lambda i, total: progress_calls.append((i, total)))
    assert len(list(out_dir.glob("*.jpg"))) == 3
    assert progress_calls[-1] == (3, 3)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_processor.py::test_save_image_jpg -v
```

Expected: FAIL — `save_image` not defined.

- [ ] **Step 3: Implement `save_image` and `process_batch` in processor.py**

Append to `processor.py`:

```python
def save_image(image: Image.Image, output_path: Path, fmt: str, quality: int) -> None:
    """Save image to output_path in the given format."""
    fmt_lower = fmt.lower()
    if fmt_lower == "jpg":
        image.convert("RGB").save(output_path, "JPEG", quality=quality)
    elif fmt_lower == "png":
        image.save(output_path, "PNG")
    elif fmt_lower == "webp":
        image.save(output_path, "WEBP", quality=quality)
    else:
        image.convert("RGB").save(output_path, "JPEG", quality=quality)


def process_batch(
    image_paths: list[Path],
    wm_config: WatermarkConfig,
    frame_config: FrameConfig,
    export_config: ExportConfig,
    progress_callback=None,
) -> list[str]:
    """
    Process all images: apply frame → apply watermark → save.
    Returns list of error messages (empty if all succeeded).
    progress_callback(current_index, total) called after each image.
    """
    errors = []
    total = len(image_paths)
    out_folder = Path(export_config.output_folder)
    suffix = export_config.suffix
    fmt = export_config.format

    for i, path in enumerate(image_paths, start=1):
        try:
            img = Image.open(path).convert("RGB")
            img = apply_frame(img, frame_config)
            img = apply_watermark(img, wm_config)
            out_name = path.stem + suffix + "." + fmt
            out_path = out_folder / out_name
            save_image(img, out_path, fmt, export_config.quality)
        except Exception as e:
            errors.append(f"{path.name}: {e}")
        finally:
            if progress_callback:
                progress_callback(i, total)

    return errors
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_processor.py -v
```

Expected: All 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add processor.py tests/test_processor.py
git commit -m "feat: processor save_image and process_batch"
```

---

## Task 7: Main Window Skeleton

**Files:**
- Create: `ui.py`
- Create: `main.py`

- [ ] **Step 1: Create `main.py`**

```python
# main.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from settings import load_settings
from ui import MainWindow

SETTINGS_PATH = Path(__file__).parent / "wapi_settings.json"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WAPI")
    app.setApplicationDisplayName("WAPI")

    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    settings = load_settings(SETTINGS_PATH)
    window = MainWindow(settings, SETTINGS_PATH)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `ui.py` — main window skeleton with dark theme**

```python
# ui.py
from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QStatusBar, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from settings import Settings, save_settings

ORANGE = "#E8682A"
BG_DARK = "#1E1E1E"
BG_PANEL = "#2A2A2A"
BG_WIDGET = "#333333"
TEXT_PRIMARY = "#F0F0F0"
TEXT_SECONDARY = "#AAAAAA"
BORDER = "#444444"


def apply_dark_theme(app: QApplication) -> None:
    """Apply a dark Fusion palette to the entire application."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG_DARK))
    palette.setColor(QPalette.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Base, QColor(BG_WIDGET))
    palette.setColor(QPalette.AlternateBase, QColor(BG_PANEL))
    palette.setColor(QPalette.ToolTipBase, QColor(BG_DARK))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(BG_PANEL))
    palette.setColor(QPalette.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.BrightText, QColor("#FF4444"))
    palette.setColor(QPalette.Highlight, QColor(ORANGE))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(TEXT_SECONDARY))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(TEXT_SECONDARY))
    app.setPalette(palette)
    app.setStyleSheet(f"""
        QToolTip {{ color: {TEXT_PRIMARY}; background-color: {BG_PANEL}; border: 1px solid {BORDER}; }}
        QTabBar::tab {{ padding: 6px 16px; }}
        QTabBar::tab:selected {{ color: {ORANGE}; border-bottom: 2px solid {ORANGE}; }}
        QPushButton {{
            background-color: {BG_WIDGET}; border: 1px solid {BORDER};
            border-radius: 4px; padding: 6px 12px;
        }}
        QPushButton:hover {{ background-color: #3E3E3E; }}
        QPushButton#primary {{
            background-color: {ORANGE}; color: white; border: none; font-weight: bold;
        }}
        QPushButton#primary:hover {{ background-color: #D45A20; }}
        QPushButton#primary:disabled {{ background-color: #666; color: #999; }}
        QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
        QSlider::handle:horizontal {{
            background: {ORANGE}; width: 14px; height: 14px;
            margin: -5px 0; border-radius: 7px;
        }}
        QLineEdit, QSpinBox, QComboBox {{
            background-color: {BG_WIDGET}; border: 1px solid {BORDER};
            border-radius: 4px; padding: 4px 8px; color: {TEXT_PRIMARY};
        }}
        QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; }}
        QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; }}
    """)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, settings_path: Path):
        super().__init__()
        self.settings = settings
        self.settings_path = settings_path
        self.setWindowTitle("WAPI")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Three-panel splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")

        # Panels (placeholders filled in later tasks)
        self.image_list_panel = self._make_placeholder("Image List", 220)
        self.preview_panel = self._make_placeholder("Preview", 600)
        self.settings_panel = self._make_placeholder("Settings", 300)

        splitter.addWidget(self.image_list_panel)
        splitter.addWidget(self.preview_panel)
        splitter.addWidget(self.settings_panel)
        splitter.setSizes([220, 760, 300])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(2, False)

        main_layout.addWidget(splitter, stretch=1)

        # Bottom bar placeholder
        self.bottom_bar = self._make_placeholder("Bottom Bar", 50)
        self.bottom_bar.setFixedHeight(52)
        main_layout.addWidget(self.bottom_bar)

        status = QStatusBar()
        status.setFixedHeight(24)
        status.showMessage("Bereit.")
        self.setStatusBar(status)

    def _make_placeholder(self, label: str, width: int) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(width)
        layout = QVBoxLayout(w)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(lbl)
        return w

    def closeEvent(self, event):
        save_settings(self.settings, self.settings_path)
        super().closeEvent(event)
```

- [ ] **Step 3: Update `main.py` to apply theme before window creation**

Replace the `main()` function in `main.py`:

```python
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WAPI")

    from ui import apply_dark_theme
    apply_dark_theme(app)

    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    settings = load_settings(SETTINGS_PATH)
    window = MainWindow(settings, SETTINGS_PATH)
    window.show()
    sys.exit(app.exec())
```

- [ ] **Step 4: Smoke test — launch the app**

```bash
python main.py
```

Expected: Dark window appears with three placeholder panels. Close it — no crash.

- [ ] **Step 5: Commit**

```bash
git add main.py ui.py
git commit -m "feat: main window skeleton with dark theme"
```

---

## Task 8: Image List Panel

**Files:**
- Modify: `ui.py` (replace `image_list_panel` placeholder with real `ImageListPanel`)

- [ ] **Step 1: Add `ImageListPanel` class to `ui.py`**

Add before `MainWindow`:

```python
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QStatusBar, QApplication,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog,
    QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPalette, QColor, QPixmap, QIcon
from PIL import Image as PilImage
import io


class ImageListPanel(QWidget):
    """Left panel: shows loaded images as a scrollable thumbnail list."""
    images_changed = Signal(list)   # emits list of Path objects
    selection_changed = Signal(Path)  # emits selected Path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_paths: list[Path] = []
        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header buttons
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Bilder")
        self.btn_clear = QPushButton("Alle weg")
        self.btn_add.clicked.connect(self._on_add)
        self.btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

        # Count label
        self.count_label = QLabel("0 Bilder")
        self.count_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self.count_label)

        # Thumbnail list
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(80, 60))
        self.list_widget.setSpacing(2)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: {BG_DARK}; border: none; }}
            QListWidget::item {{ padding: 4px; border-radius: 4px; }}
            QListWidget::item:selected {{ background: {ORANGE}30; border: 1px solid {ORANGE}; }}
        """)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, stretch=1)

        # Drop hint
        self.drop_hint = QLabel("Bilder hier\nfallen lassen")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet(f"""
            color: {TEXT_SECONDARY}; border: 2px dashed {BORDER};
            border-radius: 6px; padding: 16px; font-size: 12px;
        """)
        layout.addWidget(self.drop_hint)

    def _on_add(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Bilder auswählen", "",
            "Bilder (*.jpg *.jpeg *.png *.webp *.tiff *.tif *.bmp)"
        )
        if files:
            self.add_paths([Path(f) for f in files])

    def _on_clear(self):
        self.image_paths.clear()
        self.list_widget.clear()
        self._refresh_ui()
        self.images_changed.emit([])

    def _on_selection_changed(self, current, _previous):
        if current:
            idx = self.list_widget.row(current)
            if 0 <= idx < len(self.image_paths):
                self.selection_changed.emit(self.image_paths[idx])

    def add_paths(self, paths: list[Path]):
        existing = set(self.image_paths)
        new_paths = [p for p in paths if p not in existing]
        for path in new_paths:
            self.image_paths.append(path)
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            try:
                thumb = PilImage.open(path)
                thumb.thumbnail((80, 60))
                buf = io.BytesIO()
                thumb.save(buf, format="PNG")
                pixmap = QPixmap()
                pixmap.loadFromData(buf.getvalue())
                item.setIcon(QIcon(pixmap))
            except Exception:
                pass
            self.list_widget.addItem(item)
        self._refresh_ui()
        if new_paths:
            self.images_changed.emit(self.image_paths)
            self.list_widget.setCurrentRow(len(self.image_paths) - 1)

    def _refresh_ui(self):
        n = len(self.image_paths)
        self.count_label.setText(f"{n} Bild{'er' if n != 1 else ''}")
        self.drop_hint.setVisible(n == 0)
        self.list_widget.setVisible(n > 0)
        self.btn_clear.setEnabled(n > 0)

    # Drag and drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"}:
                paths.append(p)
            elif p.is_dir():
                for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.tiff", "*.tif", "*.bmp"):
                    paths.extend(p.glob(ext))
        if paths:
            self.add_paths(paths)
```

- [ ] **Step 2: Replace placeholder in `MainWindow._build_ui`**

In `MainWindow._build_ui`, replace:
```python
self.image_list_panel = self._make_placeholder("Image List", 220)
```
with:
```python
self.image_list_panel = ImageListPanel()
self.image_list_panel.setMinimumWidth(200)
self.image_list_panel.setMaximumWidth(280)
```

- [ ] **Step 3: Smoke test**

```bash
python main.py
```

Expected: Left panel shows "Bilder" button, drop hint, and thumbnail list works when files are dragged in.

- [ ] **Step 4: Commit**

```bash
git add ui.py
git commit -m "feat: image list panel with drag & drop and thumbnails"
```

---

## Task 9: Preview Panel

**Files:**
- Modify: `ui.py` (add `PreviewPanel`)

- [ ] **Step 1: Add `PreviewPanel` class to `ui.py`**

Add before `MainWindow`:

```python
class PreviewPanel(QWidget):
    """Center panel: displays the current image with watermark/frame applied live."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path: Path | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"background: {BG_DARK}; border-radius: 4px;")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setText("Kein Bild ausgewählt")
        self.image_label.setStyleSheet(f"color: {TEXT_SECONDARY}; background: {BG_DARK};")
        layout.addWidget(self.image_label, stretch=1)

        # Info bar
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 2px;")
        layout.addWidget(self.info_label)

    def show_processed_image(self, pil_image: PilImage.Image, path: Path | None = None):
        """Display a PIL image in the preview (scaled to fit the panel)."""
        available = self.image_label.size()
        max_w = max(available.width() - 16, 100)
        max_h = max(available.height() - 16, 100)

        display = pil_image.copy()
        display.thumbnail((max_w, max_h), PilImage.LANCZOS)

        buf = io.BytesIO()
        display.save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        self.image_label.setPixmap(pixmap)
        self.image_label.setText("")

        if path:
            w, h = pil_image.size
            self.info_label.setText(f"{path.name}  •  {w}×{h}px")
        else:
            self.info_label.setText("")

    def clear(self):
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("Kein Bild ausgewählt")
        self.info_label.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Will be re-triggered by the wiring in MainWindow
```

- [ ] **Step 2: Replace placeholder in `MainWindow._build_ui`**

Replace:
```python
self.preview_panel = self._make_placeholder("Preview", 600)
```
with:
```python
self.preview_panel = PreviewPanel()
```

- [ ] **Step 3: Smoke test**

```bash
python main.py
```

Expected: Center panel is dark, shows "Kein Bild ausgewählt" text.

- [ ] **Step 4: Commit**

```bash
git add ui.py
git commit -m "feat: preview panel"
```

---

## Task 10: Settings Panel — Wasserzeichen Tab

**Files:**
- Modify: `ui.py` (add `SettingsPanel` with watermark tab)

- [ ] **Step 1: Add `SettingsPanel` to `ui.py`**

Add before `MainWindow`. This is the full right-side settings panel with all three tabs:

```python
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QStatusBar, QApplication,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog,
    QSizePolicy, QProgressBar, QTabWidget, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QSlider, QRadioButton, QButtonGroup, QColorDialog,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPalette, QColor, QPixmap, QIcon, QFont
from PySide6.QtWidgets import QFontComboBox


class ColorButton(QPushButton):
    """A button that shows a color swatch and opens a color picker on click."""
    color_changed = Signal(str)  # emits hex color string

    def __init__(self, color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedWidth(48)
        self._update_swatch()
        self.clicked.connect(self._pick_color)

    def _update_swatch(self):
        self.setStyleSheet(f"background-color: {self._color}; border: 1px solid {BORDER}; border-radius: 4px;")

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = color.name()
            self._update_swatch()
            self.color_changed.emit(self._color)

    def get_color(self) -> str:
        return self._color

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._update_swatch()


class SettingsPanel(QWidget):
    """Right panel: tabbed settings for watermark, frame, and export."""
    settings_changed = Signal()  # emitted whenever any setting changes

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._suppress_signals = False
        self._build_ui()
        self._load_from_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_watermark_tab(), "Wasserzeichen")
        self.tabs.addTab(self._build_frame_tab(), "Rahmen")
        self.tabs.addTab(self._build_export_tab(), "Export")

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {ORANGE}; font-weight: bold; font-size: 11px; margin-top: 8px;")
        return lbl

    # ── Watermark Tab ────────────────────────────────────────────────────

    def _build_watermark_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        scroll.setWidget(w)

        # Enable toggle
        self.wm_enabled = QCheckBox("Wasserzeichen aktiv")
        self.wm_enabled.setChecked(True)
        layout.addWidget(self.wm_enabled)

        # Mode: text / logo
        layout.addWidget(self._section_label("Modus"))
        mode_row = QHBoxLayout()
        self.wm_mode_text = QRadioButton("Text")
        self.wm_mode_logo = QRadioButton("Logo/Bild")
        self.wm_mode_text.setChecked(True)
        mode_row.addWidget(self.wm_mode_text)
        mode_row.addWidget(self.wm_mode_logo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # TEXT controls
        self.wm_text_group = QWidget()
        tg = QFormLayout(self.wm_text_group)
        tg.setSpacing(6)
        self.wm_text = QLineEdit("sultani.de")
        tg.addRow("Text:", self.wm_text)
        self.wm_font = QFontComboBox()
        self.wm_font.setCurrentFont(QFont("Arial"))
        tg.addRow("Schrift:", self.wm_font)
        self.wm_size = QSpinBox()
        self.wm_size.setRange(8, 200)
        self.wm_size.setValue(36)
        tg.addRow("Größe:", self.wm_size)
        color_row = QHBoxLayout()
        self.wm_color = ColorButton("#FFFFFF")
        color_row.addWidget(self.wm_color)
        color_row.addStretch()
        tg.addRow("Farbe:", color_row)
        layout.addWidget(self.wm_text_group)

        # LOGO controls
        self.wm_logo_group = QWidget()
        lg = QFormLayout(self.wm_logo_group)
        lg.setSpacing(6)
        logo_row = QHBoxLayout()
        self.wm_logo_path = QLineEdit()
        self.wm_logo_path.setPlaceholderText("Kein Logo gewählt")
        self.wm_logo_path.setReadOnly(True)
        self.wm_logo_btn = QPushButton("Wählen…")
        self.wm_logo_btn.clicked.connect(self._pick_logo)
        logo_row.addWidget(self.wm_logo_path, stretch=1)
        logo_row.addWidget(self.wm_logo_btn)
        lg.addRow("Logo:", logo_row)
        self.wm_logo_size = QSlider(Qt.Horizontal)
        self.wm_logo_size.setRange(5, 50)
        self.wm_logo_size.setValue(15)
        self.wm_logo_size_lbl = QLabel("15%")
        logo_size_row = QHBoxLayout()
        logo_size_row.addWidget(self.wm_logo_size, stretch=1)
        logo_size_row.addWidget(self.wm_logo_size_lbl)
        lg.addRow("Größe:", logo_size_row)
        self.wm_logo_group.setVisible(False)
        layout.addWidget(self.wm_logo_group)

        # Opacity (shared)
        layout.addWidget(self._section_label("Deckkraft"))
        opacity_row = QHBoxLayout()
        self.wm_opacity = QSlider(Qt.Horizontal)
        self.wm_opacity.setRange(0, 100)
        self.wm_opacity.setValue(60)
        self.wm_opacity_lbl = QLabel("60%")
        opacity_row.addWidget(self.wm_opacity, stretch=1)
        opacity_row.addWidget(self.wm_opacity_lbl)
        layout.addLayout(opacity_row)

        # Position
        layout.addWidget(self._section_label("Position"))
        self.wm_position_grid = self._build_position_grid()
        layout.addWidget(self.wm_position_grid)

        # Special positions
        special_row = QHBoxLayout()
        self.wm_diagonal = QRadioButton("Diagonal")
        self.wm_tiles = QRadioButton("Kacheln")
        special_row.addWidget(self.wm_diagonal)
        special_row.addWidget(self.wm_tiles)
        special_row.addStretch()
        layout.addLayout(special_row)

        # Padding
        pad_row = QHBoxLayout()
        pad_lbl = QLabel("Abstand (px):")
        self.wm_padding = QSpinBox()
        self.wm_padding.setRange(0, 200)
        self.wm_padding.setValue(20)
        pad_row.addWidget(pad_lbl)
        pad_row.addWidget(self.wm_padding)
        pad_row.addStretch()
        layout.addLayout(pad_row)
        layout.addStretch()

        # Wire signals
        self.wm_enabled.toggled.connect(self._on_change)
        self.wm_mode_text.toggled.connect(self._on_mode_changed)
        self.wm_text.textChanged.connect(self._on_change)
        self.wm_font.currentFontChanged.connect(self._on_change)
        self.wm_size.valueChanged.connect(self._on_change)
        self.wm_color.color_changed.connect(self._on_change)
        self.wm_logo_path.textChanged.connect(self._on_change)
        self.wm_logo_size.valueChanged.connect(lambda v: (self.wm_logo_size_lbl.setText(f"{v}%"), self._on_change()))
        self.wm_opacity.valueChanged.connect(lambda v: (self.wm_opacity_lbl.setText(f"{v}%"), self._on_change()))
        self.wm_diagonal.toggled.connect(self._on_change)
        self.wm_tiles.toggled.connect(self._on_change)
        self.wm_padding.valueChanged.connect(self._on_change)

        return scroll

    def _build_position_grid(self) -> QWidget:
        """3×3 radio button grid for watermark position."""
        POSITIONS = [
            ("top-left",    "↖"), ("top-center",    "↑"), ("top-right",    "↗"),
            ("middle-left", "←"), ("center",         "·"), ("middle-right", "→"),
            ("bottom-left", "↙"), ("bottom-center", "↓"), ("bottom-right", "↘"),
        ]
        container = QWidget()
        grid_layout = QHBoxLayout(container)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self._position_buttons: dict[str, QRadioButton] = {}
        self._position_group = QButtonGroup(self)

        col_layouts = [QVBoxLayout() for _ in range(3)]
        for i, (pos_key, symbol) in enumerate(POSITIONS):
            col = i % 3
            btn = QRadioButton(symbol)
            btn.setToolTip(pos_key)
            btn.setStyleSheet("QRadioButton { font-size: 16px; }")
            self._position_buttons[pos_key] = btn
            self._position_group.addButton(btn)
            col_layouts[col].addWidget(btn)
            btn.toggled.connect(self._on_change)

        self._position_buttons["bottom-right"].setChecked(True)

        for cl in col_layouts:
            cl.setSpacing(2)
            grid_layout.addLayout(cl)

        return container

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Logo wählen", "", "Bilder (*.png *.jpg *.svg *.webp)"
        )
        if path:
            self.wm_logo_path.setText(path)

    def _on_mode_changed(self):
        is_text = self.wm_mode_text.isChecked()
        self.wm_text_group.setVisible(is_text)
        self.wm_logo_group.setVisible(not is_text)
        self._on_change()

    # ── Frame Tab ─────────────────────────────────────────────────────────

    def _build_frame_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        scroll.setWidget(w)

        self.fr_enabled = QCheckBox("Rahmen aktiv")
        layout.addWidget(self.fr_enabled)

        layout.addWidget(self._section_label("Rahmen-Stil"))
        self.fr_simple = QRadioButton("Einfacher Rahmen")
        self.fr_passe = QRadioButton("Passepartout")
        self.fr_simple.setChecked(True)
        layout.addWidget(self.fr_simple)
        layout.addWidget(self.fr_passe)

        # Simple frame controls
        self.fr_simple_group = QWidget()
        sg = QFormLayout(self.fr_simple_group)
        sg.setSpacing(6)
        sc_row = QHBoxLayout()
        self.fr_color = ColorButton("#000000")
        sc_row.addWidget(self.fr_color)
        sc_row.addStretch()
        sg.addRow("Farbe:", sc_row)
        self.fr_width = QSpinBox()
        self.fr_width.setRange(1, 200)
        self.fr_width.setValue(20)
        sg.addRow("Breite (px):", self.fr_width)
        layout.addWidget(self.fr_simple_group)

        # Passepartout controls
        self.fr_passe_group = QWidget()
        pg = QFormLayout(self.fr_passe_group)
        pg.setSpacing(6)
        pc_row = QHBoxLayout()
        self.fr_passe_color = ColorButton("#FFFFFF")
        pc_row.addWidget(self.fr_passe_color)
        pc_row.addStretch()
        pg.addRow("Hintergrund:", pc_row)
        pct_row = QHBoxLayout()
        self.fr_passe_pct = QSlider(Qt.Horizontal)
        self.fr_passe_pct.setRange(1, 20)
        self.fr_passe_pct.setValue(5)
        self.fr_passe_pct_lbl = QLabel("5%")
        pct_row.addWidget(self.fr_passe_pct, stretch=1)
        pct_row.addWidget(self.fr_passe_pct_lbl)
        pg.addRow("Stärke:", pct_row)
        self.fr_passe_label = QLineEdit("sultani.de")
        pg.addRow("Signatur:", self.fr_passe_label)
        self.fr_passe_label_font = QFontComboBox()
        self.fr_passe_label_font.setCurrentFont(QFont("Arial"))
        pg.addRow("Schrift:", self.fr_passe_label_font)
        self.fr_passe_label_size = QSpinBox()
        self.fr_passe_label_size.setRange(8, 72)
        self.fr_passe_label_size.setValue(18)
        pg.addRow("Schriftgröße:", self.fr_passe_label_size)
        plc_row = QHBoxLayout()
        self.fr_passe_label_color = ColorButton("#333333")
        plc_row.addWidget(self.fr_passe_label_color)
        plc_row.addStretch()
        pg.addRow("Schriftfarbe:", plc_row)
        self.fr_passe_group.setVisible(False)
        layout.addWidget(self.fr_passe_group)
        layout.addStretch()

        # Wire signals
        self.fr_enabled.toggled.connect(self._on_change)
        self.fr_simple.toggled.connect(self._on_frame_style_changed)
        self.fr_color.color_changed.connect(self._on_change)
        self.fr_width.valueChanged.connect(self._on_change)
        self.fr_passe_color.color_changed.connect(self._on_change)
        self.fr_passe_pct.valueChanged.connect(
            lambda v: (self.fr_passe_pct_lbl.setText(f"{v}%"), self._on_change()))
        self.fr_passe_label.textChanged.connect(self._on_change)
        self.fr_passe_label_font.currentFontChanged.connect(self._on_change)
        self.fr_passe_label_size.valueChanged.connect(self._on_change)
        self.fr_passe_label_color.color_changed.connect(self._on_change)

        return scroll

    def _on_frame_style_changed(self):
        is_simple = self.fr_simple.isChecked()
        self.fr_simple_group.setVisible(is_simple)
        self.fr_passe_group.setVisible(not is_simple)
        self._on_change()

    # ── Export Tab ───────────────────────────────────────────────────────

    def _build_export_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        scroll.setWidget(w)

        layout.addWidget(self._section_label("Ausgabeformat"))
        fmt_row = QHBoxLayout()
        self.ex_jpg = QRadioButton("JPG")
        self.ex_png = QRadioButton("PNG")
        self.ex_webp = QRadioButton("WebP")
        self.ex_jpg.setChecked(True)
        fmt_row.addWidget(self.ex_jpg)
        fmt_row.addWidget(self.ex_png)
        fmt_row.addWidget(self.ex_webp)
        fmt_row.addStretch()
        layout.addLayout(fmt_row)

        # JPG quality
        self.ex_quality_group = QWidget()
        qg = QFormLayout(self.ex_quality_group)
        q_row = QHBoxLayout()
        self.ex_quality = QSlider(Qt.Horizontal)
        self.ex_quality.setRange(1, 100)
        self.ex_quality.setValue(90)
        self.ex_quality_lbl = QLabel("90")
        q_row.addWidget(self.ex_quality, stretch=1)
        q_row.addWidget(self.ex_quality_lbl)
        qg.addRow("Qualität:", q_row)
        layout.addWidget(self.ex_quality_group)

        layout.addWidget(self._section_label("Ausgabeordner"))
        folder_row = QHBoxLayout()
        self.ex_folder = QLineEdit()
        self.ex_folder.setPlaceholderText("Kein Ordner gewählt")
        self.ex_folder_btn = QPushButton("Wählen…")
        self.ex_folder_btn.clicked.connect(self._pick_folder)
        folder_row.addWidget(self.ex_folder, stretch=1)
        folder_row.addWidget(self.ex_folder_btn)
        layout.addLayout(folder_row)

        layout.addWidget(self._section_label("Dateiname"))
        suffix_row = QFormLayout()
        self.ex_suffix = QLineEdit("_wapi")
        suffix_row.addRow("Suffix:", self.ex_suffix)
        self.ex_preview_lbl = QLabel("foto.jpg → foto_wapi.jpg")
        self.ex_preview_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        suffix_row.addRow("", self.ex_preview_lbl)
        layout.addLayout(suffix_row)
        layout.addStretch()

        # Wire signals
        self.ex_jpg.toggled.connect(self._on_format_changed)
        self.ex_png.toggled.connect(self._on_change)
        self.ex_webp.toggled.connect(self._on_change)
        self.ex_quality.valueChanged.connect(
            lambda v: (self.ex_quality_lbl.setText(str(v)), self._on_change()))
        self.ex_folder.textChanged.connect(self._on_change)
        self.ex_suffix.textChanged.connect(self._on_suffix_changed)

        return scroll

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Ausgabeordner wählen")
        if folder:
            self.ex_folder.setText(folder)

    def _on_format_changed(self):
        self.ex_quality_group.setVisible(self.ex_jpg.isChecked())
        self._on_change()

    def _on_suffix_changed(self):
        suffix = self.ex_suffix.text() or ""
        self.ex_preview_lbl.setText(f"foto.jpg → foto{suffix}.jpg")
        self._on_change()

    # ── Read / Write settings ────────────────────────────────────────────

    def _on_change(self, *args):
        if self._suppress_signals:
            return
        self._write_to_settings()
        self.settings_changed.emit()

    def _write_to_settings(self):
        wm = self.settings.watermark
        wm.enabled = self.wm_enabled.isChecked()
        wm.mode = "text" if self.wm_mode_text.isChecked() else "logo"
        wm.text = self.wm_text.text()
        wm.font = self.wm_font.currentFont().family()
        wm.size = self.wm_size.value()
        wm.color = self.wm_color.get_color()
        wm.opacity = self.wm_opacity.value()
        wm.logo_path = self.wm_logo_path.text() or None
        wm.logo_size_pct = self.wm_logo_size.value()
        wm.padding = self.wm_padding.value()

        if self.wm_diagonal.isChecked():
            wm.position = "diagonal"
        elif self.wm_tiles.isChecked():
            wm.position = "tiles"
        else:
            for key, btn in self._position_buttons.items():
                if btn.isChecked():
                    wm.position = key
                    break

        fr = self.settings.frame
        fr.enabled = self.fr_enabled.isChecked()
        fr.style = "simple" if self.fr_simple.isChecked() else "passepartout"
        fr.color = self.fr_color.get_color()
        fr.width_px = self.fr_width.value()
        fr.passe_color = self.fr_passe_color.get_color()
        fr.passe_pct = self.fr_passe_pct.value()
        fr.passe_label = self.fr_passe_label.text()
        fr.passe_label_font = self.fr_passe_label_font.currentFont().family()
        fr.passe_label_size = self.fr_passe_label_size.value()
        fr.passe_label_color = self.fr_passe_label_color.get_color()

        ex = self.settings.export
        ex.format = "jpg" if self.ex_jpg.isChecked() else ("png" if self.ex_png.isChecked() else "webp")
        ex.quality = self.ex_quality.value()
        ex.output_folder = self.ex_folder.text()
        ex.suffix = self.ex_suffix.text()

    def _load_from_settings(self):
        self._suppress_signals = True
        wm = self.settings.watermark
        self.wm_enabled.setChecked(wm.enabled)
        if wm.mode == "text":
            self.wm_mode_text.setChecked(True)
        else:
            self.wm_mode_logo.setChecked(True)
        self.wm_text.setText(wm.text)
        self.wm_font.setCurrentFont(QFont(wm.font))
        self.wm_size.setValue(wm.size)
        self.wm_color.set_color(wm.color)
        self.wm_opacity.setValue(wm.opacity)
        self.wm_opacity_lbl.setText(f"{wm.opacity}%")
        if wm.logo_path:
            self.wm_logo_path.setText(wm.logo_path)
        self.wm_logo_size.setValue(wm.logo_size_pct)
        self.wm_logo_size_lbl.setText(f"{wm.logo_size_pct}%")
        self.wm_padding.setValue(wm.padding)

        if wm.position == "diagonal":
            self.wm_diagonal.setChecked(True)
        elif wm.position == "tiles":
            self.wm_tiles.setChecked(True)
        elif wm.position in self._position_buttons:
            self._position_buttons[wm.position].setChecked(True)

        fr = self.settings.frame
        self.fr_enabled.setChecked(fr.enabled)
        if fr.style == "simple":
            self.fr_simple.setChecked(True)
        else:
            self.fr_passe.setChecked(True)
        self.fr_color.set_color(fr.color)
        self.fr_width.setValue(fr.width_px)
        self.fr_passe_color.set_color(fr.passe_color)
        self.fr_passe_pct.setValue(fr.passe_pct)
        self.fr_passe_pct_lbl.setText(f"{fr.passe_pct}%")
        self.fr_passe_label.setText(fr.passe_label)
        self.fr_passe_label_font.setCurrentFont(QFont(fr.passe_label_font))
        self.fr_passe_label_size.setValue(fr.passe_label_size)
        self.fr_passe_label_color.set_color(fr.passe_label_color)

        ex = self.settings.export
        if ex.format == "jpg":
            self.ex_jpg.setChecked(True)
        elif ex.format == "png":
            self.ex_png.setChecked(True)
        else:
            self.ex_webp.setChecked(True)
        self.ex_quality.setValue(ex.quality)
        self.ex_quality_lbl.setText(str(ex.quality))
        self.ex_folder.setText(ex.output_folder)
        self.ex_suffix.setText(ex.suffix)

        self._on_mode_changed()
        self._on_frame_style_changed()
        self._on_format_changed()
        self._suppress_signals = False
```

- [ ] **Step 2: Replace settings panel placeholder in `MainWindow._build_ui`**

Replace:
```python
self.settings_panel = self._make_placeholder("Settings", 300)
```
with:
```python
self.settings_panel = SettingsPanel(self.settings)
self.settings_panel.setMinimumWidth(260)
self.settings_panel.setMaximumWidth(340)
```

- [ ] **Step 3: Smoke test**

```bash
python main.py
```

Expected: Right panel shows all three tabs with proper dark-theme controls. Switching tabs works. Changing format hides/shows quality slider.

- [ ] **Step 4: Commit**

```bash
git add ui.py
git commit -m "feat: settings panel (watermark, frame, export tabs)"
```

---

## Task 11: Bottom Bar & Wiring

**Files:**
- Modify: `ui.py` — add `BottomBar`, wire all panels together in `MainWindow`

- [ ] **Step 1: Add `BottomBar` to `ui.py`**

Add before `MainWindow`:

```python
class BottomBar(QWidget):
    process_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(f"background: {BG_PANEL}; border-top: 1px solid {BORDER};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {BG_WIDGET}; border-radius: 4px; height: 8px; }}
            QProgressBar::chunk {{ background: {ORANGE}; border-radius: 4px; }}
        """)
        layout.addWidget(self.progress, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.process_btn = QPushButton("Jetzt verarbeiten")
        self.process_btn.setObjectName("primary")
        self.process_btn.setFixedHeight(36)
        self.process_btn.setMinimumWidth(160)
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_clicked)
        layout.addWidget(self.process_btn)

    def set_ready(self, n_images: int, has_folder: bool):
        can_process = n_images > 0 and has_folder
        self.process_btn.setEnabled(can_process)
        if n_images == 0:
            self.status_label.setText("Keine Bilder geladen")
        elif not has_folder:
            self.status_label.setText(f"{n_images} Bild(er) — Ausgabeordner fehlt")
        else:
            self.status_label.setText(f"{n_images} Bild(er) bereit")

    def start_progress(self, total: int):
        self.progress.setVisible(True)
        self.progress.setMaximum(total)
        self.progress.setValue(0)
        self.process_btn.setEnabled(False)

    def update_progress(self, current: int, total: int):
        self.progress.setValue(current)
        self.status_label.setText(f"{current} von {total} verarbeitet…")

    def finish_progress(self, errors: list[str]):
        self.progress.setVisible(False)
        if errors:
            self.status_label.setText(f"Fertig — {len(errors)} Fehler")
        else:
            self.status_label.setText("Fertig! Alle Bilder gespeichert.")
        self.process_btn.setEnabled(True)
```

- [ ] **Step 2: Wire everything together in `MainWindow`**

Replace the full `MainWindow` class with this wired version:

```python
class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, settings_path: Path):
        super().__init__()
        self.settings = settings
        self.settings_path = settings_path
        self._current_path: Path | None = None
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._refresh_preview)
        self.setWindowTitle("WAPI")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")

        self.image_list_panel = ImageListPanel()
        self.image_list_panel.setMinimumWidth(200)
        self.image_list_panel.setMaximumWidth(280)

        self.preview_panel = PreviewPanel()

        self.settings_panel = SettingsPanel(self.settings)
        self.settings_panel.setMinimumWidth(260)
        self.settings_panel.setMaximumWidth(340)

        splitter.addWidget(self.image_list_panel)
        splitter.addWidget(self.preview_panel)
        splitter.addWidget(self.settings_panel)
        splitter.setSizes([220, 760, 300])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(2, False)

        main_layout.addWidget(splitter, stretch=1)

        self.bottom_bar = BottomBar()
        main_layout.addWidget(self.bottom_bar)

    def _wire_signals(self) -> None:
        self.image_list_panel.selection_changed.connect(self._on_image_selected)
        self.image_list_panel.images_changed.connect(self._on_images_changed)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.bottom_bar.process_clicked.connect(self._on_process)

    def _on_image_selected(self, path: Path) -> None:
        self._current_path = path
        self._preview_timer.start()

    def _on_images_changed(self, paths: list) -> None:
        has_folder = bool(self.settings.export.output_folder)
        self.bottom_bar.set_ready(len(paths), has_folder)

    def _on_settings_changed(self) -> None:
        save_settings(self.settings, self.settings_path)
        has_folder = bool(self.settings.export.output_folder)
        self.bottom_bar.set_ready(
            len(self.image_list_panel.image_paths), has_folder
        )
        if self._current_path:
            self._preview_timer.start()

    def _refresh_preview(self) -> None:
        if not self._current_path:
            return
        try:
            from processor import apply_frame, apply_watermark
            img = PilImage.open(self._current_path).convert("RGB")
            img = apply_frame(img, self.settings.frame)
            img = apply_watermark(img, self.settings.watermark)
            self.preview_panel.show_processed_image(img, self._current_path)
        except Exception as e:
            self.preview_panel.clear()
            self.statusBar().showMessage(f"Vorschau-Fehler: {e}")

    def _on_process(self) -> None:
        from processor import process_batch
        paths = self.image_list_panel.image_paths
        if not paths:
            return
        total = len(paths)
        self.bottom_bar.start_progress(total)

        errors = []

        def on_progress(current, total):
            self.bottom_bar.update_progress(current, total)
            QApplication.processEvents()

        errors = process_batch(
            paths,
            self.settings.watermark,
            self.settings.frame,
            self.settings.export,
            progress_callback=on_progress,
        )
        self.bottom_bar.finish_progress(errors)
        if errors:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Fehler beim Verarbeiten",
                "Folgende Bilder konnten nicht verarbeitet werden:\n\n" +
                "\n".join(errors[:10]) +
                ("\n…" if len(errors) > 10 else "")
            )

    def closeEvent(self, event):
        save_settings(self.settings, self.settings_path)
        super().closeEvent(event)
```

- [ ] **Step 3: Full smoke test**

```bash
python main.py
```

Expected:
1. App opens with dark theme
2. Drag images into left panel — thumbnails appear
3. Click a thumbnail — preview updates with watermark applied
4. Change watermark text — preview updates within ~300ms
5. Set output folder in Export tab — "Jetzt verarbeiten" button activates
6. Click process — progress bar runs, files appear in output folder with `_wapi` suffix

- [ ] **Step 4: Commit**

```bash
git add ui.py
git commit -m "feat: bottom bar, batch processing, full signal wiring"
```

---

## Task 12: App Icon

**Files:**
- Create: `assets/icon.ico`

- [ ] **Step 1: Generate a simple icon with Pillow**

```python
# Run this once from the project root to create the icon
from PIL import Image, ImageDraw, ImageFont
import os

sizes = [16, 32,48, 64, 128, 256]
frames = []
for size in sizes:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Orange rounded square background
    draw.rounded_rectangle([0, 0, size-1, size-1], radius=size//6,
                            fill=(232, 104, 42, 255))
    # "W" letter in white
    font_size = int(size * 0.65)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    draw.text((size//2, size//2), "W", font=font, fill="white", anchor="mm")
    frames.append(img)

os.makedirs("assets", exist_ok=True)
frames[0].save("assets/icon.ico", format="ICO", sizes=[(s, s) for s in sizes],
               append_images=frames[1:])
print("Icon created: assets/icon.ico")
```

Run it:
```bash
python -c "
from PIL import Image, ImageDraw, ImageFont
import os
sizes = [16,32,48,64,128,256]
frames = []
for size in sizes:
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0,0,size-1,size-1], radius=size//6, fill=(232,104,42,255))
    font_size = int(size*0.65)
    try:
        font = ImageFont.truetype('arialbd.ttf', font_size)
    except OSError:
        font = ImageFont.load_default()
    draw.text((size//2,size//2), 'W', font=font, fill='white', anchor='mm')
    frames.append(img)
os.makedirs('assets', exist_ok=True)
frames[0].save('assets/icon.ico', format='ICO', sizes=[(s,s) for s in sizes], append_images=frames[1:])
print('Icon created')
"
```

Expected: `assets/icon.ico` created.

- [ ] **Step 2: Verify icon appears in app**

```bash
python main.py
```

Expected: Orange "W" icon visible in window title bar and taskbar.

- [ ] **Step 3: Commit**

```bash
git add assets/icon.ico
git commit -m "feat: app icon (orange W on dark background)"
```

---

## Task 13: PyInstaller Packaging

**Files:**
- Create: `build.bat`

- [ ] **Step 1: Create `build.bat`**

```bat
@echo off
echo Building WAPI...
pyinstaller ^
  --onefile ^
  --windowed ^
  --icon=assets\icon.ico ^
  --name=WAPI ^
  --add-data="assets;assets" ^
  main.py
echo.
echo Build complete: dist\WAPI.exe
pause
```

- [ ] **Step 2: Run the build**

```bash
build.bat
```

Or on Linux/macOS for testing:
```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --name=WAPI --add-data="assets:assets" main.py
```

Expected: `dist/WAPI.exe` is created (~50–70 MB).

- [ ] **Step 3: Test the .exe**

Double-click `dist/WAPI.exe` or:
```bash
dist/WAPI.exe
```

Expected: App launches correctly, all features work as in `python main.py`.

- [ ] **Step 4: Run full test suite one final time**

```bash
pytest tests/ -v
```

Expected: All 14 tests PASS.

- [ ] **Step 5: Final commit**

```bash
git add build.bat
git commit -m "feat: PyInstaller build script — produces dist/WAPI.exe"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Windows desktop app | Task 7 (PySide6 + PyInstaller) |
| Single + batch image loading | Task 8 (ImageListPanel) |
| Drag & drop | Task 8 |
| Text watermark (grid positions) | Task 3 |
| Diagonal + tiled watermark | Task 3 |
| Logo/image watermark | Task 4 |
| Simple frame | Task 5 |
| Passepartout frame with label | Task 5 |
| Watermark + frame combined | Task 6 (process_batch pipeline) |
| Live preview | Task 11 (wiring + timer) |
| Format selection (JPG/PNG/WebP) | Task 6 + Task 10 |
| Output folder selection | Task 10 |
| Filename suffix | Task 10 |
| Settings persistence | Task 2 |
| Progress bar | Task 11 (BottomBar) |
| Dark theme with orange accents | Task 7 |
| Error handling / logging | Task 6 (process_batch returns errors) |
| App icon | Task 12 |
| Standalone .exe | Task 13 |

All spec requirements covered. ✅

**Placeholder scan:** No TBDs, TODOs, or "similar to Task N" references found. ✅

**Type consistency:** `WatermarkConfig`, `FrameConfig`, `ExportConfig` defined in Task 2 and used identically in Tasks 3–6 and 10–11. `apply_frame(image, cfg)` and `apply_watermark(image, cfg)` signatures defined in Tasks 3/5 and called identically in Tasks 6 and 11. ✅
