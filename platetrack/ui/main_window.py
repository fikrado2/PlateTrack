"""Qt user interface for PlateTrack."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Slot, Signal, QObject, QThread
from PySide6.QtGui import QImage, QPixmap, QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QSystemTrayIcon,
    QMenu,
    QStatusBar,
    # dialogs
    QInputDialog,
    QColorDialog,
    # for rich text
    QTextEdit,
)

# Import our core
from platetrack import __version__, APP_NAME, PUBLISHER
import platetrack.paths as paths
from platetrack.logging_setup import setup_logging
from platetrack.core.database import (
    init_db,
    get_setting,
    set_setting,
    add_visit,
    get_visits,
    visits_today,
    visits_week,
    visits_month,
    visits_total,
    visits_inside_now,
    Visit,
)
from platetrack.core.timeutil import fmt_duration, now_local, iso
from platetrack.core.plate_parser import (
    normalize,
    validate as validate_plate,
    preset_names,
    preset_description,
)
from platetrack.core.pipeline import DetectionPipeline
from platetrack.core.utils import draw_zone, draw_track_id

logger = setup_logging()


class VideoFrameSignal(QObject):
    """Simple signal carrier to move video frames from the detection thread to the GUI thread."""
    frame_ready = Signal(object)  # will carry a QImage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.setMinimumSize(900, 600)

        # ----- central widget with tabs -----
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # ----- live view tab -----
        self.live_tab = QWidget()
        self.tabs.addTab(self.live_tab, "Live")

        live_layout = QVBoxLayout(self.live_tab)

        # video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("No video feed")
        self.video_label.setStyleSheet("background-color: #222; color: #fff;")
        live_layout.addWidget(self.video_label, stretch=1)

        # controls bar
        controls = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_settings = QPushButton("Settings")
        self.btn_export = QPushButton("Export")
        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)
        controls.addWidget(self.btn_settings)
        controls.addWidget(self.btn_export)
        controls.addStretch()
        live_layout.addLayout(controls)

        # counters bar
        counters = QHBoxLayout()
        self.lbl_today = QLabel("Today: 0")
        self.lbl_inside = QLabel("Inside now: 0")
        self.lbl_total = QLabel("Total: 0")
        counters.addWidget(self.lbl_today)
        counters.addWidget(self.lbl_inside)
        counters.addWidget(self.lbl_total)
        counters.addStretch()
        live_layout.addLayout(counters)

        # ----- visits tab -----
        self.visits_tab = QWidget()
        self.tabs.addTab(self.visits_tab, "Visits")
        visits_layout = QVBoxLayout(self.visits_tab)

        # search/filter bar
        search_layout = QHBoxLayout()
        self.txt_search_plate = QLineEdit()
        self.txt_search_plate.setPlaceholderText("Search plate...")
        self.btn_search = QPushButton("Search")
        self.btn_clear = QPushButton("Clear")
        search_layout.addWidget(self.txt_search_plate)
        search_layout.addWidget(self.btn_search)
        search_layout.addWidget(self.btn_clear)
        visits_layout.addLayout(search_layout)

        # visits table
        self.visits_table = QTableWidget(0, 7)
        self.visits_table.setHorizontalHeaderLabels(
            ["ID", "Plate", "Entry", "Exit", "Duration", "Confidence", "Snapshot"]
        )
        self.visits_table.horizontalHeader().setStretchLastSection(True)
        self.visits_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        visits_layout.addWidget(self.visits_table)

        # ----- reports tab -----
        self.reports_tab = QWidget()
        self.tabs.addTab(self.reports_tab, "Reports")
        reports_layout = QVBoxLayout(self.reports_tab)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        reports_layout.addWidget(self.report_view)
        btn_layout = QHBoxLayout()
        self.btn_refresh_report = QPushButton("Refresh Report")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_refresh_report)
        reports_layout.addLayout(btn_layout)

        # ----- about tab -----
        self.about_tab = QWidget()
        self.tabs.addTab(self.about_tab, "About")
        about_layout = QVBoxLayout(self.about_tab)
        self.about_text = QTextEdit()
        self.about_text.setReadOnly(True)
        about_layout.addWidget(self.about_text)
        self._fill_about()

        # ----- status bar -----
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        # ----- detection pipeline (runs in its own thread) -----
        self.pipeline: Optional[DetectionPipeline] = None
        self.pipeline_thread: Optional[QThread] = None
        self.frame_signal = VideoFrameSignal()
        self.frame_signal.frame_ready.connect(self._display_frame, Qt.QueuedConnection)

        # ----- connections -----
        self.btn_start.clicked.connect(self._start_pipeline)
        self.btn_stop.clicked.connect(self._stop_pipeline)
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_export.clicked.connect(self._export_data)
        self.btn_search.clicked.connect(self._search_visits)
        self.btn_clear.clicked.connect(self._clear_search)
        self.btn_refresh_report.clicked.connect(self._refresh_report)

        # ----- periodic UI refresh (counters, visits table) -----
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._refresh_ui)
        self.ui_timer.start(2000)  # every 2 seconds

        # ----- initialise DB and load settings -----
        init_db()
        self._load_settings_into_ui()
        self._refresh_ui()

        # ----- system tray icon -----
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        hide_action = QAction("Hide", self)
        exit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        exit_action.triggered.connect(self._on_tray_exit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        logger.info("PlateTrack main window initialised")

    # ------------------------------------------------------------------ #
    # UI helpers
    # ------------------------------------------------------------------ #
    def _fill_about(self) -> None:
        txt = f"""
        <h2>{APP_NAME}</h2>
        <p><b>Version:</b> {__version__}<br>
        <b>Publisher:</b> {PUBLISHER}<br>
        <b>Copyright:</b> Copyright (c) {PUBLISHER}</p>
        <p>PlateTrack is a Windows desktop application that connects to CCTV cameras,
        detects license plates using YOLO and OCR, counts vehicles, and records
        how long each vehicle stays in a user-defined detection zone.</p>
        <p>Built with Python, OpenCV, Ultralytics YOLO, PaddleOCR, and PySide6.</p>
        """
        self.about_text.setHtml(txt.strip())

    def _load_settings_into_ui(self) -> None:
        """Read settings from DB and store them locally; the Settings dialog will read/write."""
        # For now we just keep them in memory; the Settings dialog will read directly from DB.
        pass

    def _status(self, msg: str, timeout: int = 5000) -> None:
        self.status.showMessage(msg, timeout)

    # ------------------------------------------------------------------ #
    # Pipeline control
    # ------------------------------------------------------------------ #
    def _start_pipeline(self) -> None:
        source = get_setting("camera_source", "")
        if not source:
            QMessageBox.warning(self, "No camera", "Please configure a camera source in Settings first.")
            return
        if self.pipeline is not None:
            self._stop_pipeline()

        # Create pipeline in its own QThread
        self.pipeline_thread = QThread()
        self.pipeline = DetectionPipeline(
            source,
            plate_model_path=get_setting("plate_model_path", ""),
            vehicle_model_path=get_setting("vehicle_model_path", ""),
            ocr_lang=get_setting("ocr_lang", "en"),
            min_confidence=float(get_setting("confidence_threshold", "0.5")),
            callback=self._pipeline_callback,
        )
        self.pipeline.moveToThread(self.pipeline_thread)
        self.pipeline_thread.started.connect(self.pipeline.start)
        self.pipeline_thread.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._status("Detection started…")

    def _stop_pipeline(self) -> None:
        if self.pipeline is not None:
            self.pipeline.stop()
            self.pipeline = None
        if self.pipeline_thread is not None:
            self.pipeline_thread.quit()
            self.pipeline_thread.wait()
            self.pipeline_thread = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._status("Detection stopped.")

    @Slot(object)
    def _pipeline_callback(self, result: object, annotated_frame: object) -> None:
        """Called from the detection pipeline thread via Qt.QueuedConnection."""
        # result is PlateResult, annotated_frame is a numpy array (BGR)
        self.frame_signal.frame_ready.emit(annotated_frame)
        # Also store the visit in the database (entry/exit handling is done elsewhere)
        # For MVP we treat every detection as a new visit; real entry/exit logic will be added later.
        # We'll just add a visit entry now and later update exit via a tracker.
        try:
            plate = result.plate_text
            conf = result.confidence
            snapshot_path = None
            if get_setting("save_snapshots", "1") == "1":
                snap_dir = paths.snapshots_dir()
                snap_dir.mkdir(parents=True, exist_ok=True)
                ts = iso(now_local()).replace(":", "-")
                snap_path = snap_dir / f"{plate}_{ts}.jpg"
                cv2.imwrite(str(snap_path), annotated_frame)
                snapshot_path = snap_path
            add_visit(
                plate=plate,
                entry_time=now_local(),
                confidence=conf,
                snapshot_path=snapshot_path,
                camera_source=get_setting("camera_source", ""),
            )
        except Exception as e:  # pragma: no cover
            logger.error("Failed to store visit: %s", e)

    @Slot(QImage)
    def _display_frame(self, img: QImage) -> None:
        """Slot that receives a QImage and shows it in the video label."""
        pix = QPixmap.fromImage(img)
        # scale to fit the label while keeping aspect ratio
        self.video_label.setPixmap(pix.scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        ))

    # ------------------------------------------------------------------ #
    # Settings dialog (simple)
    # ------------------------------------------------------------------ #
    def _open_settings(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._status("Settings saved.")
            # restart pipeline if running
            was_running = self.pipeline is not None and self.pipeline_thread is not None and self.pipeline_thread.isRunning()
            if was_running:
                self._stop_pipeline()
                self._start_pipeline()

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def _export_data(self) -> None:
        fmt, _ = QFileDialog.getSaveFileName(
            self,
            "Export visits",
            str(paths.app_data_dir() / "exports"),
            "CSV files (*.csv);;Excel files (*.xlsx);;PDF files (*.pdf)",
        )
        if not fmt:
            return
        # For now we just export CSV; Excel/PDF can be added later.
        if fmt.lower().endswith(".csv"):
            self._export_csv(fmt)
        elif fmt.lower().endswith(".xlsx"):
            self._export_excel(fmt)
        elif fmt.lower().endswith(".pdf"):
            self._export_pdf(fmt)
        else:
            QMessageBox.warning(self, "Unknown format", "Please choose CSV, XLSX, or PDF.")
            return
        self._status(f"Exported to {fmt}")

    def _export_csv(self, path: str) -> None:
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Plate", "Entry", "Exit", "Duration (s)", "Confidence", "Snapshot", "Camera"])
            for v in get_visits(limit=10000):
                writer.writerow([
                    v.id,
                    v.plate,
                    iso(v.entry_time),
                    iso(v.exit_time) if v.exit_time else "",
                    v.duration_seconds if v.duration_seconds is not None else "",
                    v.confidence,
                    str(v.snapshot_path) if v.snapshot_path else "",
                    v.camera_source,
                ])

    def _export_excel(self, path: str) -> None:  # pragma: no cover - optional
        try:
            import pandas as pd
        except Exception:
            QMessageBox.warning(self, "Missing dependency", "Please install pandas and openpyxl for Excel export.")
            return
        data = []
        for v in get_visits(limit=10000):
            data.append({
                "ID": v.id,
                "Plate": v.plate,
                "Entry": iso(v.entry_time),
                "Exit": iso(v.exit_time) if v.exit_time else "",
                "Duration (s)": v.duration_seconds if v.duration_seconds is not None else "",
                "Confidence": v.confidence,
                "Snapshot": str(v.snapshot_path) if v.snapshot_path else "",
                "Camera": v.camera_source,
            })
        df = pd.DataFrame(data)
        df.to_excel(path, index=False)

    def _export_pdf(self, path: str) -> None:  # pragma: no cover - optional
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except Exception:
            QMessageBox.warning(self, "Missing dependency", "Please install reportlab for PDF export.")
            return
        c = canvas.Canvas(path, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"{APP_NAME} – Visit Report")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Generated: {iso(now_local())}")
        y = height - 100
        c.drawString(50, y, "ID")
        c.drawString(70, y, "Plate")
        c.drawString(150, y, "Entry")
        c.drawString(250, y, "Exit")
        c.drawString(350, y, "Duration (s)")
        c.drawString(450, y, "Confidence")
        y -= 14
        for v in get_visits(limit=100):
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(50, y, str(v.id))
            c.drawString(70, y, v.plate)
            c.drawString(150, y, iso(v.entry_time))
            c.drawString(250, y, iso(v.exit_time) if v.exit_time else "")
            c.drawString(350, y, str(v.duration_seconds) if v.duration_seconds is not None else "")
            c.drawString(450, y, f"{v.confidence:.2f}")
            y -= 12
        c.save()

    # ------------------------------------------------------------------ #
    # Visits tab interactions
    # ------------------------------------------------------------------ #
    def _search_visits(self) -> None:
        plate = self.txt_search_plate.text().strip()
        self._refresh_visits_table(plate_like=plate if plate else None)

    def _clear_search(self) -> None:
        self.txt_search_plate.clear()
        self._refresh_visits_table()

    def _refresh_visits_table(
        self,
        *,
        plate_like: Optional[str] = None,
        start_date: Optional[object] = None,  # kept for signature compatibility
        end_date: Optional[object] = None,
    ) -> None:
        visits = get_visits(limit=500, plate_like=plate_like)
        self.visits_table.setRowCount(len(visits))
        for row, v in enumerate(visits):
            self.visits_table.setItem(row, 0, QTableWidgetItem(str(v.id)))
            self.visits_table.setItem(row, 1, QTableWidgetItem(v.plate))
            self.visits_table.setItem(row, 2, QTableWidgetItem(iso(v.entry_time)))
            self.visits_table.setItem(row, 3, QTableWidgetItem(iso(v.exit_time) if v.exit_time else ""))
            self.visits_table.setItem(row, 4, QTableWidgetItem(fmt_duration(v.duration_seconds)))
            self.visits_table.setItem(row, 5, QTableWidgetItem(f"{v.confidence:.2f}"))
            snap_item = QTableWidgetItem("View" if v.snapshot_path else "")
            if v.snapshot_path:
                snap_item.setToolTip(str(v.snapshot_path))
            self.visits_table.setItem(row, 6, snap_item)
        self.visits_table.resizeColumnsToContents()

    # ------------------------------------------------------------------ #
    # Periodic UI refresh (counters, visits table, report)
    # ------------------------------------------------------------------ #
    def _refresh_ui(self) -> None:
        # counters
        self.lbl_today.setText(f"Today: {visits_today()}")
        self.lbl_inside.setText(f"Inside now: {visits_inside_now(int(get_setting('exit_timeout_seconds', '30')))}")
        self.lbl_total.setText(f"Total: {visits_total()}")
        # visits table (if visible)
        if self.tabs.currentIndex() == 1:  # Visits tab
            self._refresh_visits_table()
        # report (if visible)
        if self.tabs.currentIndex() == 2:  # Reports tab
            self._refresh_report()

    def _refresh_report(self) -> None:
        # simple text report for now
        today = visits_today()
        week = visits_week()
        month = visits_month()
        total = visits_total()
        inside = visits_inside_now(int(get_setting('exit_timeout_seconds', '30')))
        txt = f"""
PlateTrack Daily Report
=======================
Date: {iso(now_local())}

Counts:
  Today:      {today}
  This week:  {week}
  This month: {month}
  Total:      {total}
  Inside now: {inside}

Top plates today:
"""
        # get top 5 plates today
        from collections import Counter
        today_visits = get_visits(
            limit=1000,
            start_date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        counter = Counter(v.plate for v in today_visits)
        for plate, cnt in counter.most_common(5):
            txt += f"  {plate}: {cnt}\n"
        self.report_view.setPlainText(txt.strip())

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def _on_tray_exit(self):
        self._stop_pipeline()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "PlateTrack",
            "Application minimized to tray. The detection continues running.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
