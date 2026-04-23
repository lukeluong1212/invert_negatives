# Negative Review Lab

Convert scanned film negatives to positive images using either:

- a web interface for batch review and tuning
- a desktop app that runs without a web server
- a CLI for scripted processing

## Features

- Batch upload and per-image settings (client-side in browser)
- Auto, color, and black-and-white modes
- Percentile stretch, exposure, and white balance controls
- RGB tint controls (red, green, blue)
- Undo for image settings
- Download current image or full session ZIP (generated in browser)
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

- [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

The web flow now runs image processing on client resources (browser CPU and memory). FastAPI is used as a lightweight local/static host during transition.

## Host as a Static Site (GitHub Pages)

The web app can be hosted as a static site using the root [index.html](index.html) and [static/client-app.js](static/client-app.js).

1. Push your latest changes to the `main` branch.
2. In GitHub, open Settings -> Pages.
3. Under Build and deployment, set Source to Deploy from a branch.
4. Select branch `main` and folder `/ (root)`.
5. Save and wait for Pages to publish.

After publish, your site URL will be shown in Pages settings.

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
app.py                Thin FastAPI static host (index + static assets + health check)
index.html            Static web app entrypoint for local host and GitHub Pages
desktop_app.py        Desktop app entry point
invert_negative.py    CLI entry point
image_processing.py   Compatibility shim to shared core
invertneg/core/       Shared processing + models
invertneg/services/   Shared Python services used by desktop/CLI paths
invertneg/desktop/    Standalone PySide6 UI
static/               Static assets
results/              Output images
data/                 Example inputs
```

## Notes

- Supported image formats include: .jpg, .jpeg, .png, .tif, .tiff, .bmp, .webp
- Browser sessions are in-memory for the web UI and reset on page reload

## Static Hosting Notes

- `index.html` is the single source of truth for the web UI entrypoint.
- `static/client-app.js` contains client-only processing and interaction logic.
- No web API routes are required for GitHub Pages hosting.
