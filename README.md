# 🌊 SONNET: Sonar Target Detection & Acoustic Intelligence Workstation

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/UI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![YOLO](https://img.shields.io/badge/Detection-YOLO11s%20Balanced-success.svg)](https://github.com/ultralytics/ultralytics)
[![Mapping](https://img.shields.io/badge/GIS-TkinterMapView-orange.svg)](https://github.com/TomSchimansky/TkinterMapView)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

**SONNET** is an end-to-end desktop acoustic intelligence and sonar anomaly detection workstation designed for marine survey hydrographers, defense operators, and ROV/AUV pilots. It integrates real-time deep learning object detection, ByteTrack acoustic target tracking, digital signal processing (DSP) contrast equalizers, geospatial GPS mapping, and automated mission debrief generation.

---

## 🔄 Project Migration & Evolution History

In earlier revisions of the repository, the project consisted of fragmented prototypes, multi-tier mock experiments, and scattered script variants (`app.py`, `desktop_app.py`, `advanced_app.py`, alongside separate web/electron frontend mockups in `backend/` and `ui/`). 

We performed a comprehensive architectural migration to consolidate the codebase into a unified, high-performance, native desktop application:

| Feature / Aspect | Legacy Architecture (Old Commits) | Modern SONNET Workstation (Current) |
| :--- | :--- | :--- |
| **Code Structure** | Fragmented across `backend/`, `ui/`, `app.py`, `desktop_app.py` | Unified single-binary desktop architecture located in `src/main.py` |
| **Directory Organization** | Scattered root files and untracked artifacts | Clean taxonomy: `src/` (core app), `models/` (weights), `docs/` (evaluations), `scripts/` (processors), `assets/` |
| **Video Playback** | Basic play loop; pausing destroyed capture, resetting to frame 0 | **Interactive Transport Bar**: True pause/resume, interactive timeline scrub slider, step backward/forward (±1s), speed control (`0.5x`, `1.0x`, `2.0x`) |
| **Target Inspection** | Passive treeview table with no direct interaction | **Interactive Target Inspector**: Click-to-inspect card with crop thumbnails, live GPS readouts, operator verification (`Confirmed`/`False Alarm`), and notes logging |
| **Acoustic Enhancement** | None (raw BGR/grayscale video feed only) | **Live DSP Pipeline**: CLAHE adaptive histogram equalization, gain/contrast adjustment, and 5 acoustic colormaps (Thermal, Ironbow, Ocean, Amber) |
| **Geospatial Mapping** | Telemetry coordinates only displayed as text | **Synchronized Satellite GIS Map**: Live ROV track path with automatic pinned markers for detected anomalies |
| **Threat Alerts** | No alert mechanism | **Tactical Audio-Visual Alert**: Warning banners + acoustic audio ping (`winsound.Beep`) upon detecting high-risk targets (`mine_cylinder`) |
| **Export Formats** | Basic PDF debrief only | **Full Intelligence Suite**: Automated PDF mission debriefs, raw tabular CSV logs, and GIS-compliant GeoJSON point feature collections |
| **Model Management** | Hardcoded model path | **Dynamic Hot-Swapping**: Auto-discovers `.pt` model weights and allows live model switching on the fly |

---

## 🎯 Supported Marine Anomaly Classes

The underlying YOLO model (`sonar_yolo11s_balanced_v1_best.pt`) is specifically trained on sidescan sonar acoustics to classify 5 critical marine target categories:

1. 🛢️ **Pipeline** (`pipeline`): Subsea oil, gas, and utility pipeline segments and crossings.
2. 🚢 **Shipwreck** (`shipwreck`): Sunken vessels, structural maritime debris, and historic wrecks.
3. 💣 **Mine Cylinder** (`mine_cylinder`): Ground and moored cylindrical naval mines and ordnance.
4. 🕸️ **Ghost Net** (`ghost_net`): Abandoned fishing nets entangling reefs and marine wildlife.
5. 🦀 **Crab Pot** (`crab_pot`): Commercial and artisanal benthic traps and seafloor clutter.

---

## 🚀 Key Workstation Features

### 1. Acoustic Target Detection & Tracking
* Powered by Ultralytics YOLO with integrated **ByteTrack** and custom spatial centroid tracking.
* Prevents duplicate target counts as long objects or consecutive acoustic pings scroll through the sidescan waterfall.

### 2. Live Signal Enhancement & Acoustic Palettes
* **CLAHE Equalizer**: Contrast Limited Adaptive Histogram Equalization to bring out subtle acoustic shadows from low-contrast seabeds.
* **Acoustic Gain & Contrast**: Custom scaling for turbid and deep-water acoustic attenuation.
* **Palette Presets**:
  * **Default**: Standard sidescan acoustic imagery.
  * **Thermal (Inferno)**: High-temperature gradient for thermal contrast.
  * **Ironbow (Jet)**: High-visibility multi-spectrum color map.
  * **Ocean Blue**: Hydrographic survey deep-blue palette.
  * **Amber (Sepia)**: Classic golden sidescan sonar paper-recorder tone.

### 3. Operator Verification & Target Inspector
* Click any detection in the **Target Log** to view:
  * Cropped high-resolution thumbnail snapshot.
  * Exact geographic coordinates (Latitude, Longitude) and water depth.
  * Detection confidence and acoustic ping/frame index.
* Mark targets as **`❓ Pending`**, **`✅ Confirmed`**, or **`❌ False Alarm`**.
* Add custom **Operator Notes** directly saved into mission debrief files.

### 4. Interactive Transport & Video Scrubbing
* **Timeline Scrubber**: Drag or click anywhere on the slider to instantly inspect specific survey segments.
* **True Pause & Resume**: Inspect frames in detail without restarting video playback.
* **Frame Stepping**: `⏮ -1s` and `+1s ⏭` buttons for forensic review.
* **Speed Regulator**: Seamlessly switch between `0.5x`, `1.0x`, and `2.0x` speeds.

### 5. Multi-Format Mission Export
* 📄 **Executive PDF Debrief**: Summarizes target distribution charts, survey timestamps, and embedded crop snapshots.
* 📊 **CSV Data Table**: Raw telemetry, confidence scores, operator status, notes, and file paths.
* 🌐 **GeoJSON Layer**: Standard GeoJSON FeatureCollection of Point geometries ready for direct drag-and-drop into **QGIS**, **ArcGIS**, or **Google Earth**.

---

## 📂 Project Directory Structure

```text
Model/
├── assets/                  # Application icons and branding logos
│   ├── icon.ico
│   └── logo.png
├── docs/                    # Training metrics, PR curves, and dataset specifications
│   └── training_artifacts/
├── models/                  # Custom trained YOLO detection weights
│   └── sonar_yolo11s_balanced_v1_best.pt
├── reports/                 # Output directory for PDFs, CSVs, and GeoJSON exports
├── scripts/                 # Utility scripts (XTF to MP4 video generators)
│   ├── make_batch_videos.py
│   ├── make_more_videos.py
│   └── make_zenodo_video.py
├── snapshots/               # Auto-cropped target anomaly snapshots
├── src/                     # Core application source code
│   └── main.py              # Main CustomTkinter workstation application
├── weights/                 # Additional base and experimental weights
├── CONTRIBUTORS.md          # Project contributors list
├── requirements.txt         # Python package dependencies
├── Start.bat                # Windows one-click application launcher
└── README.md                # Comprehensive workstation documentation
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
* Python 3.10 or higher installed on Windows, Linux, or macOS.

### 2. Clone the Repository
```bash
git clone https://github.com/Arsh-Pathan/Sonnet.git
cd Sonnet
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch SONNET
On **Windows**, double-click:
```cmd
Start.bat
```
Or run directly via command line:
```bash
python src/main.py
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Space` | Play / Pause video feed |
| `Left Arrow` (`←`) | Step backward 1 second |
| `Right Arrow` (`→`) | Step forward 1 second |
| `F11` | Toggle Fullscreen workstation mode |

---

## 👥 Contributors & Acknowledgements

* **Arsh Pathan** ([@Arsh-Pathan](https://github.com/Arsh-Pathan))
* **Vaishnavi Jare** ([@vaishnavijare60-hash](https://github.com/vaishnavijare60-hash))
* **Chetan Sonawane** ([@sonawanechetan2007-source](https://github.com/sonawanechetan2007-source))
* **SnippyCodes** ([@SnippyCodes](https://github.com/SnippyCodes))
* **Saburi Katkar** ([@saburikatkar](https://github.com/saburikatkar))
* **Sahil Kumavat** ([@sahilkumavat-web](https://github.com/sahilkumavat-web))

---
*Built with ❤️ for marine hydrography, underwater robotics, and acoustic intelligence.*
