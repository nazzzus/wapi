# main.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from settings import load_settings
from ui import MainWindow, apply_dark_theme, ActivationDialog

SETTINGS_PATH = Path(__file__).parent / "wapi_settings.json"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WAPI")
    app.setApplicationDisplayName("WAPI")

    apply_dark_theme(app)

    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # ── License check ──────────────────────────────────────────────────────
    from license import is_licensed
    if not is_licensed():
        dialog = ActivationDialog()
        if dialog.exec() != dialog.Accepted:
            sys.exit(0)  # User cancelled activation — exit app

    # ── Launch main window ─────────────────────────────────────────────────
    settings = load_settings(SETTINGS_PATH)
    window = MainWindow(settings, SETTINGS_PATH)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
