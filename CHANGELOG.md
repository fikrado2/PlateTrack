# Changelog

All notable changes to PlateTrack will be documented in this file.

## [1.0.0] - 2026-10-27
### Added
- Initial release of PlateTrack v1.0.0
- Windows desktop application for license plate recognition from CCTV
- YOLOv8 vehicle detection + optional license-plate detection model
- PaddleOCR for plate text recognition
- SQLite database for visits and settings
- PySide6-based modern UI with live view, visits table, reports, and settings
- Export to CSV, Excel, PDF
- Watchlist with audio alert
- Configurable plate formats (country presets + custom regex)
- Dark mode toggle
- Automatic reconnection for camera streams
- Detection zone drawing (TODO: interactive)
- Build scripts for PyInstaller and Inno Setup installer