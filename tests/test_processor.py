# tests/test_processor.py
import pytest
from PIL import Image as PilImage
from pathlib import Path
from processor import apply_watermark, apply_frame, save_image, process_batch
from settings import WatermarkConfig, FrameConfig, ExportConfig


def make_test_image(width=800, height=600, color=(100, 149, 237)) -> PilImage.Image:
    return PilImage.new("RGB", (width, height), color)


def test_text_watermark_returns_image():
    img = make_test_image()
    cfg = WatermarkConfig(enabled=True, mode="text", text="test", opacity=80, position="bottom-right")
    result = apply_watermark(img, cfg)
    assert isinstance(result, PilImage.Image)
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

def test_logo_watermark_returns_correct_size(tmp_path):
    img = make_test_image(800, 600)
    logo_path = tmp_path / "logo.png"
    logo = PilImage.new("RGBA", (200, 100), (255, 0, 0, 180))
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
    assert result.size == img.size

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
    border = int(min(800, 600) * 0.05)
    expected_w = 800 + 2 * border
    assert result.width == expected_w
    assert result.height > 600

def test_frame_does_not_modify_original():
    img = make_test_image(800, 600)
    original_size = img.size
    cfg = FrameConfig(enabled=True, style="simple", width_px=10)
    apply_frame(img, cfg)
    assert img.size == original_size

def test_save_image_jpg(tmp_path):
    img = make_test_image(400, 300)
    out = tmp_path / "out.jpg"
    save_image(img, out, "jpg", 85)
    assert out.exists()
    reloaded = PilImage.open(out)
    assert reloaded.format == "JPEG"

def test_save_image_png(tmp_path):
    img = make_test_image(400, 300)
    out = tmp_path / "out.png"
    save_image(img, out, "png", 90)
    assert out.exists()
    reloaded = PilImage.open(out)
    assert reloaded.format == "PNG"

def test_save_image_webp(tmp_path):
    img = make_test_image(400, 300)
    out = tmp_path / "out.webp"
    save_image(img, out, "webp", 80)
    assert out.exists()
    reloaded = PilImage.open(out)
    assert reloaded.format == "WEBP"

def test_process_batch_creates_output_files(tmp_path):
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
