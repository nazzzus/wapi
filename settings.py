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
