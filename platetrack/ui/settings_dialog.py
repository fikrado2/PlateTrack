"""Settings dialog for PlateTrack."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QMessageBox,
    # tab widget
    QTabWidget,
    QWidget,
)

from platetrack import APP_NAME
from platetrack.logging_setup import setup_logging
from platetrack.core.paths import app_data_dir, models_dir
from platetrack.core.database import get_setting, set_setting
from platetrack.core.plate_parser import preset_names, preset_description
from platetrack.core.timeutil import fmt_duration

logger = setup_logging()


class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} – Settings")
        self.setMinimumWidth(500)
        self.resize(600, 500)

        # ----- tabs -----
        tabs = QTabWidget(self)
        tabs.addTab(self._create_camera_tab(), "Camera")
        tabs.addTab(self._create_detection_tab(), "Detection")
        tabs.addTab(self._create_plate_format_tab(), "Plate Format")
        tabs.addTab(self._create_ui_tab(), "UI")
        tabs.addTab(self._create_advanced_tab(), "Advanced")

        # ----- buttons -----
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_box.addStretch()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        # ----- main layout -----
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addLayout(btn_box)

        self._load_settings()

    # ------------------------------------------------------------------ #
    # Tab builders
    # ------------------------------------------------------------------ #
    def _create_camera_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        # source type
        self.source_type = QComboBox()
        self.source_type.addItems(["USB webcam", "Network (RTSP/HTTP/MJPEG)", "Video file"])
        self.source_type.currentIndexChanged.connect(self._on_source_type_changed)
        form.addRow("Source type:", self.source_type)

        # source value
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("e.g. 0 for first webcam, or rtsp://user:pass@ip:554/stream")
        form.addRow("Source:", self.source_edit)

        # browse button for file
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self._browse_source)
        src_hbox = QHBoxLayout()
        src_hbox.addWidget(self.source_edit)
        src_hbox.addWidget(self.btn_browse)
        form.addRow("", src_hbox)

        # username / password (only for network)
        self.network_group = QGroupBox("Network credentials")
        net_form = QFormLayout(self.network_group)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        net_form.addRow("Username:", self.username_edit)
        net_form.addRow("Password:", self.password_edit)
        form.addRow(self.network_group)

        return w

    def _create_detection_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        # model folders
        self.models_dir_label = QLabel(str(Path.home()))
        btn_models = QPushButton("Choose models folder…")
        btn_models.clicked.connect(self._choose_models_folder)
        models_hbox = QHBoxLayout()
        models_hbox.addWidget(self.models_dir_label)
        models_hbox.addWidget(btn_models)
        form.addRow("Models folder:", models_hbox)

        # confidence threshold
        self.confidence_edit = QLineEdit()
        self.confidence_edit.setValidator(QDoubleValidator(0.0, 1.0, 2))
        form.addRow("OCR confidence threshold:", self.confidence_edit)

        # exit timeout
        self.exit_timeout_edit = QLineEdit()
        self.exit_timeout_edit.setValidator(QIntValidator(5, 300))
        form.addRow("Exit timeout (seconds):", self.exit_timeout_edit)

        # save snapshots
        self.save_snapshots_cb = QCheckBox("Save snapshot images")
        form.addRow(self.save_snapshots_cb)

        # dark mode
        self.dark_mode_cb = QCheckBox("Enable dark mode")
        form.addRow(self.dark_mode_cb)

        return w

    def _create_plate_format_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.plate_preset = QComboBox()
        self.plate_preset.addItems(preset_names())
        form.addRow("Plate format preset:", self.plate_preset)

        self.custom_regex = QLineEdit()
        self.custom_regex.setPlaceholderText("Leave empty to use preset")
        form.addRow("Custom regex (when preset = Custom):", self.custom_regex)

        # example
        self.example_label = QLabel("Example: ")
        form.addRow("Example:", self.example_label)

        self.plate_preset.currentIndexChanged.connect(self._update_example)
        return w

    def _create_ui_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.show_track_id_cb = QCheckBox("Show track IDs on video")
        form.addRow(self.show_track_id_cb)

        self.zone_color_btn = QPushButton("Choose zone colour…")
        self.zone_color = "#00A5FF"  # default orange
        self.zone_color_btn.clicked.connect(self._choose_zone_color)
        form.addRow("Detection zone colour:", self.zone_color_btn)

        return w

    def _create_advanced_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.watchlist_edit = QLineEdit()
        self.watchlist_edit.setPlaceholderText("Comma-separated list of plates (e.g. ABC123,XYZ789)")
        form.addRow("Watchlist:", self.watchlist_edit)

        self.watchlist_sound_edit = QLineEdit()
        btn_sound = QPushButton("Browse…")
        btn_sound.clicked.connect(self._browse_sound)
        sound_hbox = QHBoxLayout()
        sound_hbox.addWidget(self.watchlist_sound_edit)
        sound_hbox.addWidget(btn_sound)
        form.addRow("Watchlist alert sound:", sound_hbox)

        return w

    # ------------------------------------------------------------------ #
    # Slots for UI interactions
    # ------------------------------------------------------------------ #
    def _on_source_type_changed(self, index: int) -> None:
        # index: 0 USB, 1 Network, 2 File
        self.network_group.setVisible(index == 1)
        self.btn_browse.setVisible(index == 2)
        if index == 0:
            self.source_edit.setPlaceholderText("0, 1, 2… (webcam index)")
        elif index == 1:
            self.source_edit.setPlaceholderText("rtsp://user:pass@192.168.1.64:554/stream")
        elif index == 2:
            self.source_edit.setPlaceholderText("Path to a local video file")

    def _browse_source(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select video file",
            str(Path.home()),
            "Video files (*.mp4 *.avi *.mkv *.mov);;All files (*)",
        )
        if file_name:
            self.source_edit.setText(file_name)

    def _choose_models_folder(self) -> None:
        dir_name = QFileDialog.getExistingDirectory(self, "Select models folder", str(Path.home()))
        if dir_name:
            self.models_dir_label.setText(dir_name)

    def _choose_zone_color(self) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self.zone_color = color.name()
            self.zone_color_btn.setStyleSheet(f"background-color: {self.zone_color};")

    def _browse_sound(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select alert sound",
            str(Path.home()),
            "Audio files (*.wav *.mp3);;All files (*)",
        )
        if file_name:
            self.watchlist_sound_edit.setText(file_name)

    def _update_example(self) -> None:
        preset = self.plate_preset.currentText()
        desc = preset_description(preset)
        self.example_label.setText(f"{desc} (e.g. {self._example_for_preset(preset)})")

    def _example_for_preset(self, preset: str) -> str:
        examples = {
            "generic": "ABC123",
            "kenya": "KDA445J",
            "tanzania": "T372BAA",
            "uganda": "UAG445B",
            "uk": "AB12CDE",
            "eu": "B-AB1234",
            "custom": "see custom regex",
        }
        return examples.get(preset, "")

    # ------------------------------------------------------------------ #
    # Settings loading / saving
    # ------------------------------------------------------------------ #
    def _load_settings(self) -> None:
        # Camera
        src_type = get_setting("camera_source_type", "0")  # 0=usb,1=network,2=file
        try:
            self.source_type.setCurrentIndex(int(src_type))
        except ValueError:
            self.source_type.setCurrentIndex(0)
        self._on_source_type_changed(self.source_type.currentIndex())
        self.source_edit.setText(get_setting("camera_source", ""))
        self.username_edit.setText(get_setting("camera_username", ""))
        self.password_edit.setText(get_setting("camera_password", ""))

        # Detection
        models_dir_str = get_setting("models_dir", str(models_dir()))
        self.models_dir_label.setText(models_dir_str)
        self.confidence_edit.setText(get_setting("confidence_threshold", "0.5"))
        self.exit_timeout_edit.setText(get_setting("exit_timeout_seconds", "30"))
        self.save_snapshots_cb.setChecked(get_setting("save_snapshots", "1") == "1")
        self.dark_mode_cb.setChecked(get_setting("dark_mode", "0") == "1")

        # Plate format
        preset = get_setting("plate_format_preset", "generic")
        idx = self.plate_preset.findText(preset)
        if idx >= 0:
            self.plate_preset.setCurrentIndex(idx)
        self._update_example()
        self.custom_regex.setText(get_setting("plate_format_custom_regex", ""))

        # UI
        self.show_track_id_cb.setChecked(get_setting("show_track_id", "0") == "1")
        self.zone_color = get_setting("zone_color", "#00A5FF")
        self.zone_color_btn.setStyleSheet(f"background-color: {self.zone_color};")

        # Advanced
        self.watchlist_edit.setText(get_setting("watchlist", ""))
        self.watchlist_sound_edit.setText(get_setting("watchlist_sound", ""))

    def accept(self) -> None:
        """Validate and save settings."""
        # Camera
        src_type = self.source_type.currentIndex()
        set_setting("camera_source_type", str(src_type))
        source = self.source_edit.text().strip()
        set_setting("camera_source", source)
        if src_type == 1:  # network
            set_setting("camera_username", self.username_edit.text())
            set_setting("camera_password", self.password_edit.text())
        else:
            # clear credentials for non-network types
            set_setting("camera_username", "")
            set_setting("camera_password", "")

        # Detection
        set_setting("models_dir", self.models_dir_label.text())
        set_setting("confidence_threshold", self.confidence_edit.text() or "0.5")
        set_setting("exit_timeout_seconds", self.exit_timeout_edit.text() or "30")
        set_setting("save_snapshots", "1" if self.save_snapshots_cb.isChecked() else "0")
        set_setting("dark_mode", "1" if self.dark_mode_cb.isChecked() else "0")

        # Plate format
        preset = self.plate_preset.currentText()
        set_setting("plate_format_preset", preset)
        set_setting("plate_format_custom_regex", self.custom_regex.text())

        # UI
        set_setting("show_track_id", "1" if self.show_track_id_cb.isChecked() else "0")
        set_setting("zone_color", self.zone_color)

        # Advanced
        set_setting("watchlist", self.watchlist_edit.text())
        set_setting("watchlist_sound", self.watchlist_sound_edit.text())

        logger.info("Settings saved")
        super().accept()


# Small helper to avoid importing QColorDialog at module level (optional)
from PySide6.QtGui import QColorDialog  # noqa: E402
