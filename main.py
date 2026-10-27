"""Entry point for PlateTrack (Qt GUI application)."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from platetrack import __version__, APP_NAME, PUBLISHER
from platetrack.logging_setup import setup_logging
from platetrack.ui.main_window import MainWindow


def main() -> None:
    # Enable high-DPI scaling (Qt 6 does this by default, but be explicit)
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(PUBLISHER)
    app.setOrganizationDomain("fikrado.com")  # placeholder

    # Set window icon (use the bundled icon)
    icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.ico")
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))

    # Initialise logging (creates log file in AppData)
    setup_logging()

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
