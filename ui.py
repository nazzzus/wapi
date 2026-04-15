# ui.py
from __future__ import annotations
import io
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QStatusBar, QApplication,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog,
    QSizePolicy, QProgressBar, QTabWidget, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QSlider, QRadioButton, QButtonGroup, QColorDialog,
    QScrollArea, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPalette, QColor, QPixmap, QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import QFontComboBox
from PIL import Image as PilImage

from settings import Settings, save_settings
from processor import SUPPORTED_INPUT_EXTS

# ── Build file-dialog filter string from SUPPORTED_INPUT_EXTS ──────────────
_EXTS_GLOB = " ".join(f"*{e}" for e in sorted(SUPPORTED_INPUT_EXTS))
INPUT_FILE_FILTER = f"Alle Bilder ({_EXTS_GLOB});;JPEG (*.jpg *.jpeg *.jfif *.jpe);;PNG (*.png);;WebP (*.webp);;TIFF (*.tif *.tiff);;HEIC/HEIF (*.heic *.heif);;GIF (*.gif);;Alle Dateien (*.*)"

# ── Theme constants ────────────────────────────────────────────────────────
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
        QTabBar::tab {{ padding: 6px 16px; background: {BG_PANEL}; color: {TEXT_SECONDARY}; border: none; }}
        QTabBar::tab:selected {{ color: {ORANGE}; border-bottom: 2px solid {ORANGE}; background: {BG_DARK}; }}
        QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}
        QTabWidget::pane {{ border: none; }}
        QPushButton {{
            background-color: {BG_WIDGET}; border: 1px solid {BORDER};
            border-radius: 4px; padding: 6px 12px; color: {TEXT_PRIMARY};
        }}
        QPushButton:hover {{ background-color: #3E3E3E; }}
        QPushButton:disabled {{ color: {TEXT_SECONDARY}; }}
        QPushButton#primary {{
            background-color: {ORANGE}; color: white; border: none; font-weight: bold;
        }}
        QPushButton#primary:hover {{ background-color: #D45A20; }}
        QPushButton#primary:disabled {{ background-color: #555; color: #888; }}
        QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
        QSlider::handle:horizontal {{
            background: {ORANGE}; width: 14px; height: 14px;
            margin: -5px 0; border-radius: 7px;
        }}
        QSlider::sub-page:horizontal {{ background: {ORANGE}; border-radius: 2px; }}
        QLineEdit, QSpinBox, QComboBox, QFontComboBox {{
            background-color: {BG_WIDGET}; border: 1px solid {BORDER};
            border-radius: 4px; padding: 4px 8px; color: {TEXT_PRIMARY};
        }}
        QLineEdit:focus, QSpinBox:focus {{ border-color: {ORANGE}; }}
        QCheckBox {{ color: {TEXT_PRIMARY}; spacing: 8px; }}
        QCheckBox::indicator {{
            width: 16px; height: 16px; border: 1px solid {BORDER};
            border-radius: 3px; background: {BG_WIDGET};
        }}
        QCheckBox::indicator:checked {{ background: {ORANGE}; border-color: {ORANGE}; }}
        QRadioButton {{ color: {TEXT_PRIMARY}; spacing: 6px; }}
        QRadioButton::indicator {{
            width: 14px; height: 14px; border: 1px solid {BORDER};
            border-radius: 7px; background: {BG_WIDGET};
        }}
        QRadioButton::indicator:checked {{ background: {ORANGE}; border-color: {ORANGE}; }}
        QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; border: none; }}
        QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 20px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollArea {{ border: none; }}
        QFormLayout QLabel {{ color: {TEXT_SECONDARY}; }}
    """)


# ── ColorButton ────────────────────────────────────────────────────────────

class ColorButton(QPushButton):
    """A button that shows a color swatch and opens a color picker on click."""
    color_changed = Signal(str)

    def __init__(self, color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(36, 28)
        self._update_swatch()
        self.clicked.connect(self._pick_color)
        self.setToolTip("Farbe wählen")

    def _update_swatch(self):
        self.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid {BORDER}; border-radius: 4px;"
        )

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self, "Farbe wählen")
        if color.isValid():
            self._color = color.name()
            self._update_swatch()
            self.color_changed.emit(self._color)

    def get_color(self) -> str:
        return self._color

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._update_swatch()


# ── ImageListPanel ─────────────────────────────────────────────────────────

class ImageListPanel(QWidget):
    """Left panel: loaded images as a scrollable thumbnail list."""
    images_changed = Signal(list)
    selection_changed = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_paths: list[Path] = []
        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QLabel("BILDER")
        header.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Hinzufügen")
        self.btn_clear = QPushButton("Alle weg")
        self.btn_clear.setEnabled(False)
        self.btn_add.clicked.connect(self._on_add)
        self.btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

        self.count_label = QLabel("Keine Bilder")
        self.count_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self.count_label)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(72, 54))
        self.list_widget.setSpacing(2)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: {BG_DARK}; border: none; outline: none; }}
            QListWidget::item {{ padding: 4px; border-radius: 4px; color: {TEXT_PRIMARY}; }}
            QListWidget::item:selected {{ background: {ORANGE}33; border: 1px solid {ORANGE}; }}
            QListWidget::item:hover {{ background: {BG_WIDGET}; }}
        """)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, stretch=1)

        self.drop_hint = QLabel("Bilder hier\nfallen lassen\noder oben hinzufügen")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet(f"""
            color: {TEXT_SECONDARY}; border: 2px dashed {BORDER};
            border-radius: 8px; padding: 20px; font-size: 12px; line-height: 1.5;
        """)
        layout.addWidget(self.drop_hint)

    def _on_add(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Bilder auswählen", "", INPUT_FILE_FILTER
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
                thumb.thumbnail((72, 54))
                buf = io.BytesIO()
                thumb.convert("RGB").save(buf, format="PNG")
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
        if n == 0:
            self.count_label.setText("Keine Bilder")
        elif n == 1:
            self.count_label.setText("1 Bild geladen")
        else:
            self.count_label.setText(f"{n} Bilder geladen")
        self.drop_hint.setVisible(n == 0)
        self.list_widget.setVisible(n > 0)
        self.btn_clear.setEnabled(n > 0)

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
            if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTS:
                paths.append(p)
            elif p.is_dir():
                for ext in SUPPORTED_INPUT_EXTS:
                    paths.extend(sorted(p.glob(f"*{ext}")))
        if paths:
            self.add_paths(paths)


# ── PreviewPanel ───────────────────────────────────────────────────────────

class PreviewPanel(QWidget):
    """Center panel: displays the current image with effects applied live."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_pil: PilImage.Image | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Preview area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet(f"background: {BG_DARK};")
        self.image_label.setText("Kein Bild ausgewählt")
        self.image_label.setStyleSheet(f"color: {TEXT_SECONDARY}; background: {BG_DARK}; font-size: 14px;")
        layout.addWidget(self.image_label, stretch=1)

        # Info bar
        info_bar = QWidget()
        info_bar.setFixedHeight(28)
        info_bar.setStyleSheet(f"background: {BG_PANEL}; border-top: 1px solid {BORDER};")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(12, 4, 12, 4)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        layout.addWidget(info_bar)

    def show_processed_image(self, pil_image: PilImage.Image, path: Path | None = None):
        self._current_pil = pil_image
        self._render()
        if path:
            w, h = pil_image.size
            self.info_label.setText(f"{path.name}  •  {w} × {h} px")

    def _render(self):
        if not self._current_pil:
            return
        available = self.image_label.size()
        max_w = max(available.width() - 24, 100)
        max_h = max(available.height() - 24, 100)
        display = self._current_pil.copy()
        display.thumbnail((max_w, max_h), PilImage.LANCZOS)
        buf = io.BytesIO()
        display.convert("RGB").save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        self.image_label.setPixmap(pixmap)
        self.image_label.setStyleSheet(f"background: {BG_DARK};")

    def clear(self):
        self._current_pil = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("Kein Bild ausgewählt")
        self.image_label.setStyleSheet(f"color: {TEXT_SECONDARY}; background: {BG_DARK}; font-size: 14px;")
        self.info_label.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pil:
            self._render()


# ── SettingsPanel ──────────────────────────────────────────────────────────

class SettingsPanel(QWidget):
    """Right panel: tabbed settings (watermark / frame / export)."""
    settings_changed = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._suppress = False
        self._build_ui()
        self._load_from_settings()

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {ORANGE}; font-weight: bold; font-size: 10px; "
            f"letter-spacing: 1px; margin-top: 10px; margin-bottom: 2px;"
        )
        return lbl

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_watermark_tab(), "Wasserzeichen")
        self.tabs.addTab(self._build_frame_tab(), "Rahmen")
        self.tabs.addTab(self._build_export_tab(), "Export")

    # ── Watermark tab ──────────────────────────────────────────────────────

    def _build_watermark_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        w.setStyleSheet(f"background: {BG_DARK};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)
        scroll.setWidget(w)

        self.wm_enabled = QCheckBox("Wasserzeichen aktiv")
        self.wm_enabled.setChecked(True)
        lay.addWidget(self.wm_enabled)

        lay.addWidget(self._section("MODUS"))
        mode_row = QHBoxLayout()
        self.wm_mode_text = QRadioButton("Text")
        self.wm_mode_logo = QRadioButton("Logo / Bild")
        self.wm_mode_text.setChecked(True)
        mode_row.addWidget(self.wm_mode_text)
        mode_row.addWidget(self.wm_mode_logo)
        mode_row.addStretch()
        lay.addLayout(mode_row)

        # TEXT controls
        self.wm_text_group = QWidget()
        self.wm_text_group.setStyleSheet(f"background: {BG_DARK};")
        tg = QFormLayout(self.wm_text_group)
        tg.setSpacing(6)
        tg.setContentsMargins(0, 4, 0, 0)
        self.wm_text = QLineEdit("sultani.de")
        tg.addRow("Text:", self.wm_text)
        self.wm_font = QFontComboBox()
        self.wm_font.setCurrentFont(QFont("Arial"))
        tg.addRow("Schrift:", self.wm_font)
        self.wm_size = QSpinBox()
        self.wm_size.setRange(8, 200)
        self.wm_size.setValue(36)
        tg.addRow("Größe:", self.wm_size)
        c_row = QHBoxLayout()
        self.wm_color = ColorButton("#FFFFFF")
        c_row.addWidget(self.wm_color)
        c_row.addStretch()
        tg.addRow("Farbe:", c_row)
        lay.addWidget(self.wm_text_group)

        # LOGO controls
        self.wm_logo_group = QWidget()
        self.wm_logo_group.setStyleSheet(f"background: {BG_DARK};")
        lg = QFormLayout(self.wm_logo_group)
        lg.setSpacing(6)
        lg.setContentsMargins(0, 4, 0, 0)
        logo_pick_row = QHBoxLayout()
        self.wm_logo_path = QLineEdit()
        self.wm_logo_path.setPlaceholderText("Kein Logo gewählt")
        self.wm_logo_path.setReadOnly(True)
        self.wm_logo_btn = QPushButton("…")
        self.wm_logo_btn.setFixedWidth(32)
        self.wm_logo_btn.clicked.connect(self._pick_logo)
        logo_pick_row.addWidget(self.wm_logo_path, stretch=1)
        logo_pick_row.addWidget(self.wm_logo_btn)
        lg.addRow("Logo:", logo_pick_row)
        logo_size_row = QHBoxLayout()
        self.wm_logo_size = QSlider(Qt.Horizontal)
        self.wm_logo_size.setRange(5, 50)
        self.wm_logo_size.setValue(15)
        self.wm_logo_size_lbl = QLabel("15%")
        self.wm_logo_size_lbl.setFixedWidth(36)
        logo_size_row.addWidget(self.wm_logo_size, stretch=1)
        logo_size_row.addWidget(self.wm_logo_size_lbl)
        lg.addRow("Größe:", logo_size_row)
        self.wm_logo_group.setVisible(False)
        lay.addWidget(self.wm_logo_group)

        # Opacity
        lay.addWidget(self._section("DECKKRAFT"))
        op_row = QHBoxLayout()
        self.wm_opacity = QSlider(Qt.Horizontal)
        self.wm_opacity.setRange(0, 100)
        self.wm_opacity.setValue(60)
        self.wm_opacity_lbl = QLabel("60%")
        self.wm_opacity_lbl.setFixedWidth(36)
        op_row.addWidget(self.wm_opacity, stretch=1)
        op_row.addWidget(self.wm_opacity_lbl)
        lay.addLayout(op_row)

        # Position
        lay.addWidget(self._section("POSITION"))
        lay.addWidget(self._build_position_grid())

        special_row = QHBoxLayout()
        self.wm_diagonal = QRadioButton("Diagonal")
        self.wm_tiles = QRadioButton("Kacheln")
        special_row.addWidget(self.wm_diagonal)
        special_row.addWidget(self.wm_tiles)
        special_row.addStretch()
        lay.addLayout(special_row)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Abstand (px):"))
        self.wm_padding = QSpinBox()
        self.wm_padding.setRange(0, 200)
        self.wm_padding.setValue(20)
        self.wm_padding.setFixedWidth(70)
        pad_row.addWidget(self.wm_padding)
        pad_row.addStretch()
        lay.addLayout(pad_row)
        lay.addStretch()

        # Signals
        self.wm_enabled.toggled.connect(self._emit)
        self.wm_mode_text.toggled.connect(self._on_wm_mode_changed)
        self.wm_text.textChanged.connect(self._emit)
        self.wm_font.currentFontChanged.connect(self._emit)
        self.wm_size.valueChanged.connect(self._emit)
        self.wm_color.color_changed.connect(self._emit)
        self.wm_logo_path.textChanged.connect(self._emit)
        self.wm_logo_size.valueChanged.connect(lambda v: (self.wm_logo_size_lbl.setText(f"{v}%"), self._emit()))
        self.wm_opacity.valueChanged.connect(lambda v: (self.wm_opacity_lbl.setText(f"{v}%"), self._emit()))
        self.wm_diagonal.toggled.connect(self._emit)
        self.wm_tiles.toggled.connect(self._emit)
        self.wm_padding.valueChanged.connect(self._emit)

        return scroll

    def _build_position_grid(self) -> QWidget:
        """3×3 grid of radio buttons for watermark anchor position."""
        POSITIONS = [
            ("top-left", "↖"),    ("top-center", "↑"),    ("top-right", "↗"),
            ("middle-left", "←"), ("center", "·"),         ("middle-right", "→"),
            ("bottom-left", "↙"), ("bottom-center", "↓"), ("bottom-right", "↘"),
        ]
        container = QWidget()
        container.setStyleSheet(f"background: {BG_PANEL}; border-radius: 6px; padding: 4px;")
        grid = QHBoxLayout(container)
        grid.setSpacing(0)
        grid.setContentsMargins(4, 4, 4, 4)

        self._pos_btns: dict[str, QRadioButton] = {}
        self._pos_group = QButtonGroup(self)
        self._pos_group.setExclusive(True)

        cols = [QVBoxLayout() for _ in range(3)]
        for i, (key, sym) in enumerate(POSITIONS):
            col = i % 3
            btn = QRadioButton(sym)
            btn.setToolTip(key.replace("-", " ").title())
            btn.setStyleSheet("QRadioButton { font-size: 18px; padding: 2px 4px; }")
            self._pos_btns[key] = btn
            self._pos_group.addButton(btn)
            cols[col].addWidget(btn)
            btn.toggled.connect(self._emit)

        self._pos_btns["bottom-right"].setChecked(True)
        for col_lay in cols:
            col_lay.setSpacing(0)
            grid.addLayout(col_lay)

        return container

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Logo wählen", "", "Bilder (*.png *.jpg *.webp)"
        )
        if path:
            self.wm_logo_path.setText(path)

    def _on_wm_mode_changed(self):
        is_text = self.wm_mode_text.isChecked()
        self.wm_text_group.setVisible(is_text)
        self.wm_logo_group.setVisible(not is_text)
        self._emit()

    # ── Frame tab ──────────────────────────────────────────────────────────

    def _build_frame_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        w.setStyleSheet(f"background: {BG_DARK};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)
        scroll.setWidget(w)

        self.fr_enabled = QCheckBox("Rahmen aktiv")
        lay.addWidget(self.fr_enabled)

        lay.addWidget(self._section("STIL"))
        self.fr_simple = QRadioButton("Einfacher Rahmen")
        self.fr_passe = QRadioButton("Passepartout")
        self.fr_simple.setChecked(True)
        lay.addWidget(self.fr_simple)
        lay.addWidget(self.fr_passe)

        # Simple
        self.fr_simple_group = QWidget()
        self.fr_simple_group.setStyleSheet(f"background: {BG_DARK};")
        sg = QFormLayout(self.fr_simple_group)
        sg.setSpacing(6)
        sg.setContentsMargins(0, 4, 0, 0)
        sc_row = QHBoxLayout()
        self.fr_color = ColorButton("#000000")
        sc_row.addWidget(self.fr_color)
        sc_row.addStretch()
        sg.addRow("Farbe:", sc_row)
        self.fr_width = QSpinBox()
        self.fr_width.setRange(1, 200)
        self.fr_width.setValue(20)
        sg.addRow("Breite (px):", self.fr_width)
        lay.addWidget(self.fr_simple_group)

        # Passepartout
        self.fr_passe_group = QWidget()
        self.fr_passe_group.setStyleSheet(f"background: {BG_DARK};")
        pg = QFormLayout(self.fr_passe_group)
        pg.setSpacing(6)
        pg.setContentsMargins(0, 4, 0, 0)
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
        self.fr_passe_pct_lbl.setFixedWidth(36)
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
        lay.addWidget(self.fr_passe_group)
        lay.addStretch()

        # Signals
        self.fr_enabled.toggled.connect(self._emit)
        self.fr_simple.toggled.connect(self._on_frame_style_changed)
        self.fr_color.color_changed.connect(self._emit)
        self.fr_width.valueChanged.connect(self._emit)
        self.fr_passe_color.color_changed.connect(self._emit)
        self.fr_passe_pct.valueChanged.connect(lambda v: (self.fr_passe_pct_lbl.setText(f"{v}%"), self._emit()))
        self.fr_passe_label.textChanged.connect(self._emit)
        self.fr_passe_label_font.currentFontChanged.connect(self._emit)
        self.fr_passe_label_size.valueChanged.connect(self._emit)
        self.fr_passe_label_color.color_changed.connect(self._emit)

        return scroll

    def _on_frame_style_changed(self):
        is_simple = self.fr_simple.isChecked()
        self.fr_simple_group.setVisible(is_simple)
        self.fr_passe_group.setVisible(not is_simple)
        self._emit()

    # ── Export tab ─────────────────────────────────────────────────────────

    def _build_export_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        w.setStyleSheet(f"background: {BG_DARK};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)
        scroll.setWidget(w)

        lay.addWidget(self._section("FORMAT"))
        self.ex_format = QComboBox()
        self.ex_format.addItem("JPG  (verlustbehaftet)",  "jpg")
        self.ex_format.addItem("PNG  (verlustfrei)",      "png")
        self.ex_format.addItem("WebP (verlustbehaftet)",  "webp")
        self.ex_format.addItem("TIFF (verlustfrei)",      "tiff")
        self.ex_format.addItem("BMP  (verlustfrei)",      "bmp")
        lay.addWidget(self.ex_format)

        self.ex_quality_group = QWidget()
        self.ex_quality_group.setStyleSheet(f"background: {BG_DARK};")
        qg = QHBoxLayout(self.ex_quality_group)
        qg.setContentsMargins(0, 4, 0, 0)
        qg.addWidget(QLabel("Qualität:"))
        self.ex_quality = QSlider(Qt.Horizontal)
        self.ex_quality.setRange(1, 100)
        self.ex_quality.setValue(90)
        self.ex_quality_lbl = QLabel("90")
        self.ex_quality_lbl.setFixedWidth(28)
        qg.addWidget(self.ex_quality, stretch=1)
        qg.addWidget(self.ex_quality_lbl)
        lay.addWidget(self.ex_quality_group)

        lay.addWidget(self._section("AUSGABEORDNER"))
        folder_row = QHBoxLayout()
        self.ex_folder = QLineEdit()
        self.ex_folder.setPlaceholderText("Kein Ordner gewählt")
        self.ex_folder_btn = QPushButton("…")
        self.ex_folder_btn.setFixedWidth(32)
        self.ex_folder_btn.clicked.connect(self._pick_folder)
        folder_row.addWidget(self.ex_folder, stretch=1)
        folder_row.addWidget(self.ex_folder_btn)
        lay.addLayout(folder_row)

        lay.addWidget(self._section("DATEINAME"))
        suffix_form = QFormLayout()
        suffix_form.setSpacing(6)
        self.ex_suffix = QLineEdit("_wapi")
        suffix_form.addRow("Suffix:", self.ex_suffix)
        self.ex_name_preview = QLabel("foto.jpg  →  foto_wapi.jpg")
        self.ex_name_preview.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        suffix_form.addRow("", self.ex_name_preview)
        lay.addLayout(suffix_form)
        lay.addStretch()

        # Signals
        self.ex_format.currentIndexChanged.connect(self._on_format_changed)
        self.ex_quality.valueChanged.connect(lambda v: (self.ex_quality_lbl.setText(str(v)), self._emit()))
        self.ex_folder.textChanged.connect(self._emit)
        self.ex_suffix.textChanged.connect(self._on_suffix_changed)

        return scroll

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Ausgabeordner wählen")
        if folder:
            self.ex_folder.setText(folder)

    def _on_format_changed(self):
        fmt = self.ex_format.currentData() or "jpg"
        # Quality slider only relevant for lossy formats
        self.ex_quality_group.setVisible(fmt in ("jpg", "webp"))
        self._on_suffix_changed()  # refresh file name preview with correct extension
        self._emit()

    def _on_suffix_changed(self):
        suffix = self.ex_suffix.text()
        fmt = self.ex_format.currentData() if hasattr(self, "ex_format") else "jpg"
        self.ex_name_preview.setText(f"foto.jpg  →  foto{suffix}.{fmt}")
        self._emit()

    # ── Settings read/write ────────────────────────────────────────────────

    def _emit(self, *_):
        if self._suppress:
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
            for key, btn in self._pos_btns.items():
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
        ex.format = self.ex_format.currentData() or "jpg"
        ex.quality = self.ex_quality.value()
        ex.output_folder = self.ex_folder.text()
        ex.suffix = self.ex_suffix.text()

    def _load_from_settings(self):
        self._suppress = True
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
        elif wm.position in self._pos_btns:
            self._pos_btns[wm.position].setChecked(True)

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
        idx = self.ex_format.findData(ex.format)
        self.ex_format.setCurrentIndex(idx if idx >= 0 else 0)
        self.ex_quality.setValue(ex.quality)
        self.ex_quality_lbl.setText(str(ex.quality))
        self.ex_folder.setText(ex.output_folder)
        self.ex_suffix.setText(ex.suffix)
        self.ex_name_preview.setText(f"foto.jpg  →  foto{ex.suffix}.{ex.format}")

        self._on_wm_mode_changed()
        self._on_frame_style_changed()
        self._on_format_changed()
        self._suppress = False


# ── BottomBar ──────────────────────────────────────────────────────────────

class BottomBar(QWidget):
    process_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"background: {BG_PANEL}; border-top: 1px solid {BORDER};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self.status_label = QLabel("Keine Bilder geladen")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(200)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {BG_WIDGET}; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {ORANGE}; border-radius: 3px; }}
        """)
        layout.addWidget(self.progress)

        self.process_btn = QPushButton("▶  Jetzt verarbeiten")
        self.process_btn.setObjectName("primary")
        self.process_btn.setFixedHeight(38)
        self.process_btn.setMinimumWidth(180)
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_clicked)
        layout.addWidget(self.process_btn)

    def set_ready(self, n_images: int, has_folder: bool):
        can = n_images > 0 and has_folder
        self.process_btn.setEnabled(can)
        if n_images == 0:
            self.status_label.setText("Keine Bilder geladen")
        elif not has_folder:
            self.status_label.setText(f"{n_images} Bild(er) — Ausgabeordner fehlt")
        else:
            suffix = "Bilder" if n_images != 1 else "Bild"
            self.status_label.setText(f"{n_images} {suffix} bereit zur Verarbeitung")

    def start_progress(self, total: int):
        self.progress.setVisible(True)
        self.progress.setMaximum(total)
        self.progress.setValue(0)
        self.process_btn.setEnabled(False)
        self.status_label.setText("Wird verarbeitet…")

    def update_progress(self, current: int, total: int):
        self.progress.setValue(current)
        self.status_label.setText(f"{current} von {total} Bilder verarbeitet…")

    def finish_progress(self, errors: list[str]):
        self.progress.setVisible(False)
        self.process_btn.setEnabled(True)
        if errors:
            self.status_label.setText(f"Fertig — {len(errors)} Fehler aufgetreten")
        else:
            self.status_label.setText("✓ Alle Bilder erfolgreich gespeichert!")


# ── MainWindow ─────────────────────────────────────────────────────────────

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

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar accent line
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(f"background: {ORANGE};")
        root.addWidget(accent)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")

        self.image_list_panel = ImageListPanel()
        self.image_list_panel.setMinimumWidth(190)
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

        root.addWidget(splitter, stretch=1)

        self.bottom_bar = BottomBar()
        root.addWidget(self.bottom_bar)

    def _wire_signals(self):
        self.image_list_panel.selection_changed.connect(self._on_image_selected)
        self.image_list_panel.images_changed.connect(self._on_images_changed)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.bottom_bar.process_clicked.connect(self._on_process)

    def _on_image_selected(self, path: Path):
        self._current_path = path
        self._preview_timer.start()

    def _on_images_changed(self, paths: list):
        has_folder = bool(self.settings.export.output_folder)
        self.bottom_bar.set_ready(len(paths), has_folder)

    def _on_settings_changed(self):
        save_settings(self.settings, self.settings_path)
        has_folder = bool(self.settings.export.output_folder)
        self.bottom_bar.set_ready(
            len(self.image_list_panel.image_paths), has_folder
        )
        if self._current_path:
            self._preview_timer.start()

    def _refresh_preview(self):
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
            self.statusBar().showMessage(f"Vorschau-Fehler: {e}", 5000)

    def _on_process(self):
        from processor import process_batch
        paths = self.image_list_panel.image_paths
        if not paths:
            return
        total = len(paths)
        self.bottom_bar.start_progress(total)

        def on_progress(current, _total):
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
            QMessageBox.warning(
                self, "Fehler beim Verarbeiten",
                "Folgende Bilder konnten nicht verarbeitet werden:\n\n" +
                "\n".join(errors[:10]) +
                ("\n…" if len(errors) > 10 else "")
            )

    def closeEvent(self, event):
        save_settings(self.settings, self.settings_path)
        super().closeEvent(event)


# ── ActivationDialog ───────────────────────────────────────────────────────

class ActivationDialog(QWidget):
    """
    Shown on first launch when no valid license is found.
    The user enters their license key and we activate against the backend.
    """

    Accepted = 1
    Rejected = 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = self.Rejected
        self._build_ui()
        self.setWindowTitle("WAPI — Lizenz aktivieren")
        self.setFixedSize(480, 380)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background: {BG_DARK}; color: {TEXT_PRIMARY};")

    def exec(self) -> int:
        """Show dialog modally and return Accepted or Rejected."""
        self.show()
        loop = QApplication.instance()
        while self.isVisible():
            loop.processEvents()
        return self._result

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 36, 40, 32)
        outer.setSpacing(0)

        # Orange top accent
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(f"background: {ORANGE};")
        outer.addWidget(accent)
        outer.addSpacing(24)

        # Logo / title
        title = QLabel("WAPI")
        title.setStyleSheet(f"color: {ORANGE}; font-size: 28px; font-weight: 900; letter-spacing: -1px;")
        outer.addWidget(title)

        subtitle = QLabel("Lizenzaktivierung erforderlich")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; margin-bottom: 24px;")
        outer.addWidget(subtitle)
        outer.addSpacing(20)

        # Key input
        key_label = QLabel("Lizenzschlüssel")
        key_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        outer.addWidget(key_label)
        outer.addSpacing(6)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX-XXXX")
        self.key_input.setFixedHeight(42)
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_WIDGET}; border: 1px solid {BORDER};
                border-radius: 6px; padding: 8px 14px;
                font-family: 'Consolas', monospace; font-size: 14px;
                color: {TEXT_PRIMARY}; letter-spacing: 2px;
            }}
            QLineEdit:focus {{ border-color: {ORANGE}; }}
        """)
        outer.addWidget(self.key_input)
        outer.addSpacing(8)

        # Status label
        self.status_label = QLabel("Lizenzschlüssel aus der Kaufbestätigung eingeben.")
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self.status_label.setWordWrap(True)
        outer.addWidget(self.status_label)

        outer.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self.buy_btn = QPushButton("Lizenz kaufen →")
        self.buy_btn.setStyleSheet(f"color: {ORANGE}; background: transparent; border: none; font-size: 12px;")
        self.buy_btn.clicked.connect(self._open_buy_link)
        btn_row.addWidget(self.buy_btn)
        btn_row.addStretch()

        self.activate_btn = QPushButton("Aktivieren")
        self.activate_btn.setObjectName("primary")
        self.activate_btn.setFixedHeight(38)
        self.activate_btn.setMinimumWidth(130)
        self.activate_btn.clicked.connect(self._on_activate)
        btn_row.addWidget(self.activate_btn)

        outer.addLayout(btn_row)

    def _open_buy_link(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://sultani.de/wapi"))  # deine Kauf-URL

    def _on_activate(self):
        key = self.key_input.text().strip()
        if not key:
            self._set_status("Bitte Lizenzschlüssel eingeben.", error=True)
            return

        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Aktiviere…")
        self._set_status("Verbindung zum Server…", error=False)
        QApplication.processEvents()

        from license import activate_license
        success, message, _data = activate_license(key)

        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("Aktivieren")

        if success:
            self._set_status(f"✓ {message}", error=False, success=True)
            QApplication.processEvents()
            import time; time.sleep(1.2)
            self._result = self.Accepted
            self.close()
        else:
            self._set_status(f"✗ {message}", error=True)

    def _set_status(self, text: str, error: bool = False, success: bool = False):
        if success:
            color = "#4ade80"
        elif error:
            color = "#f87171"
        else:
            color = TEXT_SECONDARY
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
