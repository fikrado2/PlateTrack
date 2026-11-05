# 🚗 PlateTrack

![Rust](https://img.shields.io/badge/language-Rust-orange.svg)
![Windows](https://img.shields.io/badge/platform-Windows-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Release](https://img.shields.io/badge/release-v1.0.0--rust-blueviolet)

**PlateTrack** is a high-performance, native Windows application for real-time and image-based license plate recognition (ALPR). Rebuilt from the ground up in Rust for maximum speed, security, and a minimal footprint.

> [!IMPORTANT]
> This is a modern Rust rewrite of the original [fikrado2/PlateTrack](https://github.com/fikrado2/PlateTrack) Python application.

---

## ✨ Features

- 🏎️ **Native Performance:** Fully compiled Rust code ensures rapid processing.
- 🖼️ **Intuitive UI:** Modern, responsive interface built with `egui` (light/dark mode support).
- 🔍 **ALPR Intelligence:** Powered by the [Plate Recognizer](https://platerecognizer.com/) Cloud Snapshot API.
- 📂 **Drag-and-Drop:** Easily drop images directly into the app for instant recognition.
- 🗄️ **Local Storage:** All detections are securely logged in a local SQLite database.
- 📊 **History & Analytics:** Search, filter, and export your detection data to CSV.
- 🛡️ **Fikrado Security:** Built with the quality and reliability expected from Fikrado products.

---

## 🚀 Getting Started

### 1. Get an API Token
1. Sign up at [platerecognizer.com](https://platerecognizer.com/).
2. Copy your **API Token** from the dashboard.
3. Launch PlateTrack, go to **Settings**, and paste your token.

### 2. Installation
Download the latest `PlateTrack.exe` from the [Releases](https://github.com/fikrado2/PlateTrack/releases) page and run it—no installation or Python runtime required!

---

## 🛠️ Build from Source

### Prerequisites
- **Rust Stable** (`x86_64-pc-windows-msvc`)
- **Visual Studio Build Tools** (C++ Desktop Development workload)

### Steps
```powershell
git clone https://github.com/fikrado2/PlateTrack.git
cd PlateTrack
git checkout rust-rewrite
cargo build --release
```
The binary will be generated at `.\target\release\platetrack.exe`.

---

## 🏢 About Fikrado Security

Fikrado Security is a leading provider of innovative security software solutions. We specialize in building robust tools that empower organizations and individuals to manage their security needs with ease and precision.

- **📧 Email:** [fikrado1@gmail.com](mailto:fikrado1@gmail.com)
- **📞 Phone:** +252634048063 / +251984858498
- **🌐 Website:** [fikrado2.github.io](https://fikrado2.github.io)

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

Built with ❤️ by [Fikrado Security](https://github.com/fikrado2)
