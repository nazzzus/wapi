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
