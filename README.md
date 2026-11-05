# PlateTrack

A native Windows desktop application for license plate recognition, rebuilt from scratch in Rust.

**Original:** [fikrado2/PlateTrack](https://github.com/fikrado2/PlateTrack) (Python/PySide6)  
**This version:** Rust + egui (fully native, single `.exe`, no Python dependency)

---

## Features

- **License Plate Recognition** via [Plate Recognizer](https://github.com/parkpow/deep-license-plate-recognition) API (cloud Snapshot API)
- **Image file support** – open via file dialog or drag-and-drop
- **SQLite database** for storing all detection records locally
- **History screen** – search, filter, view, and delete past detections
- **CSV export** of all detection history
- **Settings screen** – configure API token and endpoint
- **Modern native UI** with egui (light/dark theme, responsive)
- **All processing runs on background threads** – UI stays responsive
- **Graceful error handling** – no crashes on network failure, invalid token, rate limit, or unreadable images
- **Snapshots saved locally** for each detection

---

## Screenshots

The app has three main screens:

| Screen | Description |
|---|---|
| **Dashboard** | Stats cards (today/week/month counts) + recent detection result + open/drop image |
| **History** | Table of all past detections with search, refresh, CSV export, and delete |
| **Settings** | API token and endpoint configuration |

---

## Getting an API Token

1. Go to [platerecognizer.com](https://platerecognizer.com/) and sign up for a free account
2. After logging in, go to your **Dashboard** → **API Token**
3. Copy the token (starts with `pl_`)
4. Paste it into PlateTrack's **Settings → API Token** field
5. Click **Save Settings**

> **Free tier:** Plate Recognizer offers a free tier with 500 credits/month. Each plate read costs 1 credit.

---

## How to Build

### Prerequisites

- **Windows 10/11** (x86_64)
- **Rust** (stable toolchain, `x86_64-pc-windows-msvc` target)
- **Visual Studio Build Tools** with "Desktop development with C++" workload (needed for linking)

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/fikrado2/PlateTrack.git
cd PlateTrack

# 2. Build in release mode
cargo build --release

# 3. Run
.\target\release\platetrack.exe
```

The executable will be at `target/release/platetrack.exe`.

### Using Visual Studio Developer Command Prompt

If `link.exe` is not found in PATH, open the **x64 Native Tools Command Prompt for VS**:

```powershell
cd PlateTrack
cargo build --release
```

---

## Project Structure

```
PlateTrack/
├── Cargo.toml              # Dependencies and build config
├── README.md                # This file
├── src/
│   ├── main.rs              # Binary entry point
│   ├── lib.rs               # Library root
│   ├── app.rs               # Main app + eframe setup + UI screens
│   ├── config.rs            # Settings persistence (AppData/config.json)
│   ├── db.rs                # SQLite database (rusqlite)
│   ├── api.rs               # Plate Recognizer API client (reqwest)
│   ├── logging.rs           # Tracing/logging setup
│   └── ui/
│       └── mod.rs           # UI re-exports
└── target/                  # Build output
```

---

## Technology Choices

- **GUI:** `egui` + `eframe` – most mature fully-native Rust GUI framework. No Electron, no web views, no platform-specific toolkits needed.
- **Database:** `rusqlite` with SQLite WAL mode – fast, single-file, zero-config
- **API Client:** `reqwest` blocking client (no async runtime needed)
- **Config:** `directories` crate for correct AppData path on Windows; JSON config file
- **Logging:** `tracing` + `tracing-subscriber` with file rotation

---

## Data Storage

All data is stored in the user's AppData folder:

```
%APPDATA%\PlateTrack\
├── config.json          # User settings (API token, etc.)
├── platetrack.db        # SQLite database
├── snapshots\           # Saved detection images
└── logs\
    └── platetrack.log   # Application logs
```

---

## API Integration

PlateTrack uses the **Plate Recognizer Snapshot API**:

```
POST https://api.platerecognizer.com/v1/plate-reader/
Authorization: Token YOUR_API_TOKEN
Content-Type: multipart/form-data

upload: <image file bytes>
```

The API returns a JSON response:

```json
{
  "results": [{
    "plate": "ABC123",
    "confidence": 0.95,
    "vehicle": { "type": "Car" },
    "box": { "xmin": 120, "ymin": 80, "xmax": 400, "ymax": 150 }
  }]
}
```

---

## Error Handling

| Error | User message |
|---|---|
| No API token | "API Token is not configured." |
| Network failure | "API Error: connection failed" |
| Invalid token (401) | "API Error: Invalid API token" |
| Rate limit (429) | "API Error: rate limit exceeded" |
| Unreadable image | "Could not read image file" |
| No plate detected | "No plate detected in image" |

---

## Branch & Commits

This Rust rewrite is on branch `rust-rewrite`. To push:

```powershell
git checkout -b rust-rewrite
git add .
git commit -m "Initial Rust rewrite: egui UI, rusqlite DB, Plate Recognizer API"
git push origin rust-rewrite
```

---

## Building the Installer (Optional)

After building the release `.exe`, you can create a Windows installer using [Inno Setup](https://jrsoftware.org/isinfo.php):

1. Install Inno Setup
2. Create a script pointing to `target/release/platetrack.exe`
3. Compile to produce a single `.exe` installer

---

## License

MIT License – same as the original project. See `LICENSE` file.
