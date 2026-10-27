# PlateTrack

Windows desktop application that detects car license plates from CCTV, counts cars and records time spent.  
**Created by Fikrado Security** – Version 1.0.0

## Features

- Connect to any camera: USB webcam, network (RTSP/HTTP/MJPEG), or video file
- Real-time license plate detection using YOLOv8 and PaddleOCR
- Count vehicles: today, this week, this month, total
- Track how long each vehicle stays in a user-definable detection zone
- Store every visit with plate number, entry/exit times, duration, and snapshot image
- Modern, clean UI (PySide6) with live video overlay, visits table, reports, and settings
- Export visits to CSV, Excel, or PDF
- Watchlist: get alerted when a specific plate appears
- Configurable plate formats (country presets or custom regex)
- Dark mode support
- Automatic reconnection if the video stream drops
- GPU acceleration (CUDA) when available, falls back to CPU

## Screenshots

_(To be added)_

## Installation

See the [releases](https://github.com/fikrado2/PlateTrack/releases) page to download the latest Windows installer.

## Usage

1. Launch PlateTrack.
2. Go to **Settings → Camera** to select your video source.
3. (Optional) Adjust detection confidence, exit timeout, and plate format.
4. Press **Start** to begin processing.
5. View live detections in the **Live** tab.
6. Browse past visits in the **Visits** tab.
7. See daily statistics in the **Reports** tab.
8. Use **Export** to save data for further analysis.

## Building from source

### Prerequisites

- Python 3.11+
- Git
- (Optional) GPU drivers and CUDA toolkit for YOLO acceleration

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/fikrado2/PlateTrack.git
   cd PlateTrack
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

### Creating the Windows installer

See `build.ps1` (PowerShell) or `build.bat` (batch) in the repository root.

## License

MIT License – see the [LICENSE](LICENSE) file.

## Contact

For issues or inquiries, please open a GitHub issue.
