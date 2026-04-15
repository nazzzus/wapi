# processor.py
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from settings import WatermarkConfig, FrameConfig, ExportConfig

# ── Optional HEIF/HEIC support ─────────────────────────────────────────────
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # pillow-heif not installed — .heic/.heif files will fail gracefully

# ── Supported input extensions ─────────────────────────────────────────────
SUPPORTED_INPUT_EXTS: frozenset[str] = frozenset({
    # JPEG family
    ".jpg", ".jpeg", ".jfif", ".jpe",
    # PNG
    ".png",
    # WebP
    ".webp",
    # TIFF
    ".tif", ".tiff",
    # BMP
    ".bmp",
    # GIF (first frame)
    ".gif",
    # ICO
    ".ico",
    # Photoshop (read-only, merged composite)
    ".psd",
    # Portable bitmap family
    ".ppm", ".pgm", ".pbm", ".pnm",
    # PCX, TGA, SGI
    ".pcx", ".tga", ".sgi", ".rgb",
    # JPEG 2000
    ".jp2", ".j2k", ".jpx",
    # AVIF (Pillow ≥ 9.1 with libavif)
    ".avif",
    # HEIF/HEIC (requires pillow-heif)
    ".heic", ".heif",
})


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
    for row in range(-2, base.height // max(step_y, 1) + 3):
        for col in range(-2, base.width // max(step_x, 1) + 3):
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


def _apply_logo_watermark(image: Image.Image, cfg: WatermarkConfig) -> Image.Image:
    if not cfg.logo_path:
        return image.copy()
    try:
        logo = Image.open(cfg.logo_path).convert("RGBA")
    except (OSError, FileNotFoundError):
        return image.copy()

    target_w = int(image.width * cfg.logo_size_pct / 100)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    if cfg.opacity < 100:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * cfg.opacity / 100))
        logo.putalpha(alpha)

    result = image.copy().convert("RGBA")

    if cfg.position in ("diagonal", "tiles"):
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
        x = max(pad, min(x, image.width - target_w - pad))
        y = max(pad, min(y, image.height - target_h - pad))
        result.paste(logo, (x, y), logo)

    return result.convert("RGB")


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


def save_image(image: Image.Image, output_path: Path, fmt: str, quality: int) -> None:
    """Save image to output_path in the given format.

    fmt values: "jpg", "png", "webp", "tiff", "bmp"
    quality (1-100) applies only to JPG and WebP; ignored for lossless formats.
    """
    fmt_lower = fmt.lower()
    if fmt_lower == "jpg":
        image.convert("RGB").save(output_path, "JPEG", quality=quality, optimize=True)
    elif fmt_lower == "png":
        image.save(output_path, "PNG", optimize=True)
    elif fmt_lower == "webp":
        image.save(output_path, "WEBP", quality=quality)
    elif fmt_lower == "tiff":
        image.convert("RGB").save(output_path, "TIFF", compression="lzw")
    elif fmt_lower == "bmp":
        image.convert("RGB").save(output_path, "BMP")
    else:
        image.convert("RGB").save(output_path, "JPEG", quality=quality, optimize=True)


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
