# Negative Review Lab

Convert scanned film negatives to positive images using either:

- a web interface for batch review and tuning
- a desktop app that runs without a web server
- a CLI for scripted processing

## Features

- Batch upload and per-image settings
- Auto, color, and black-and-white modes
- Percentile stretch, exposure, and white balance controls
- RGB tint controls (red, green, blue)
- Undo for image settings
- Download current image or full session ZIP
- Original scan visibility toggle in the sidebar
- Desktop actions: Apply To All, Undo, and Reset

## Requirements

- Python 3.10+
- Packages listed in requirements.txt

## Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the Web App

```powershell
uvicorn app:app --reload
```

Then open:

- http://127.0.0.1:8000/

## Run the Standalone Desktop App

```powershell
python desktop_app.py
```

This launches a local desktop UI and does not require starting FastAPI.

## CLI Usage

Single file:

```powershell
python invert_negative.py data\P8013700.JPG --output results\P8013700_positive.jpg
```

Batch (glob):

```powershell
python invert_negative.py data\*.JPG --output-dir results\positives
```

With adjustments:

```powershell
python invert_negative.py data\*.JPG --output-dir results\positives --mode auto --percentile 0.5 --exposure 0.2 --white-balance 5 --red-tint 2 --green-tint 0 --blue-tint -2
```

## CLI Options

```text
input...              Input negative file(s)
-o, --output          Output file path (single input only)
--output-dir          Output directory for batch processing
--mode                auto | color | bw
--percentile          0 to 5
--exposure            Exposure in stops
--white-balance       Cool to warm adjustment
--red-tint            Red channel tint percentage
--green-tint          Green channel tint percentage
--blue-tint           Blue channel tint percentage
```

## Project Structure

```text
app.py                FastAPI app and API routes
desktop_app.py        Desktop app entry point
invert_negative.py    CLI entry point
image_processing.py   Compatibility shim to shared core
invertneg/core/       Shared processing + models
invertneg/services/   Shared session/workspace and rendering services
invertneg/desktop/    Standalone PySide6 UI
templates/index.html  Web UI
static/               Static assets
.sessions/            Runtime session storage
results/              Output images
data/                 Example inputs
```

## Notes

- Supported image formats include: .jpg, .jpeg, .png, .tif, .tiff, .bmp, .webp
- Session files are stored under .sessions and are recreated at runtime
