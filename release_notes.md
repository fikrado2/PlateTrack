# PlateTrack v1.0.0

## Features
- Connect to CCTV cameras (RTSP, HTTP, MJPEG, USB webcam, capture card, video file)
- License plate detection using YOLOv8 and OCR using PaddleOCR
- Vehicle tracking with ByteTrack to avoid double counting
- Count cars: today, week, month, total
- Record entry/exit times and duration per plate
- Save snapshots of detected plates
- Modern PySide6 UI with live video, counters, visits table, search, filter
- Settings for camera, detection zone, confidence, exit timeout
- Dark mode support
- Reports page with daily chart
- Export to Excel, CSV, and PDF
- Watchlist alerts with sound
- Manual correction of plate readings
- GPU (CUDA) fallback to CPU
- Error handling and logging
- Configurable plate format per country

## Build Instructions
To build the Windows installer, run the provided build script on a Windows machine with Python 3.11 installed:

1. Clone the repository
2. Run `build.bat` (or `build.ps1` for PowerShell) from the root directory
3. The script will:
   - Create a virtual environment and install dependencies
   - Build the executable with PyInstaller
   - Create the installer with Inno Setup
4. The installer `PlateTrack-Setup-1.0.0.exe` will be placed in the `dist` folder

## Requirements
- Windows 10/11
- Python 3.11 (for build environment)
- Inno Setup 6 (for installer creation)
- Optional: NVIDIA GPU with CUDA for accelerated detection

## License
MIT License - Copyright (c) 2026 Fikrado Security

## Created by
Fikrado Security
