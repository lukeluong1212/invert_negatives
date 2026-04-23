from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from PIL import UnidentifiedImageError

from invertneg.core.models import ImageSettings, parse_settings
from invertneg.services.session_service import (
    SessionImage,
    SessionNotFoundError,
    SessionImageNotFoundError,
    SessionService,
    SessionUploadError,
    UnsupportedImageError,
    UploadedFile,
)

from image_processing import (
    image_to_bytes,
)


BASE_DIR = Path(__file__).resolve().parent
SESSION_ROOT = BASE_DIR / ".sessions"
SESSION_ROOT.mkdir(exist_ok=True)
PREVIEW_MAX_SIZE = (1280, 850)
PREVIEW_JPEG_QUALITY = 84


app = FastAPI(title="Negative Converter")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
session_service = SessionService(
    session_root=SESSION_ROOT,
    preview_max_size=PREVIEW_MAX_SIZE,
    preview_jpeg_quality=PREVIEW_JPEG_QUALITY,
)


def settings_from_payload(payload: dict[str, object], fallback: ImageSettings) -> ImageSettings:
    return parse_settings_or_400(
        mode=str(payload.get("mode", fallback.mode)),
        percentile=float(payload.get("percentile", fallback.percentile)),
        exposure=float(payload.get("exposure", fallback.exposure)),
        white_balance=float(payload.get("white_balance", fallback.white_balance)),
        contrast=float(payload.get("contrast", fallback.contrast)),
        saturation=float(payload.get("saturation", fallback.saturation)),
        clarity=float(payload.get("clarity", fallback.clarity)),
        red_tint=float(payload.get("red_tint", fallback.red_tint)),
        green_tint=float(payload.get("green_tint", fallback.green_tint)),
        blue_tint=float(payload.get("blue_tint", fallback.blue_tint)),
    )


def get_session(session_id: str):
    try:
        return session_service.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_session_image(session, image_id: str) -> SessionImage:
    try:
        return session_service.get_session_image(session, image_id)
    except SessionImageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def parse_settings_or_400(
    mode: str,
    percentile: float,
    exposure: float,
    white_balance: float,
    contrast: float,
    saturation: float,
    clarity: float,
    red_tint: float,
    green_tint: float,
    blue_tint: float,
) -> ImageSettings:
    try:
        return parse_settings(
            mode=mode,
            percentile=percentile,
            exposure=exposure,
            white_balance=white_balance,
            contrast=contrast,
            saturation=saturation,
            clarity=clarity,
            red_tint=red_tint,
            green_tint=green_tint,
            blue_tint=blue_tint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/sessions")
async def create_session(files: list[UploadFile] = File(...)) -> JSONResponse:
    uploaded: list[UploadedFile] = []
    for upload in files:
        uploaded.append(UploadedFile(filename=upload.filename or "", content=await upload.read()))

    try:
        session = session_service.create_session(uploaded)
    except SessionUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse(session_service.serialize_session(session))


@app.get("/api/sessions/{session_id}")
async def session_detail(session_id: str) -> JSONResponse:
    session = get_session(session_id)
    return JSONResponse(session_service.serialize_session(session))


@app.post("/api/sessions/{session_id}/images/{image_id}/settings")
async def update_settings(
    session_id: str,
    image_id: str,
    request: Request,
) -> JSONResponse:
    session = get_session(session_id)
    image = get_session_image(session, image_id)
    payload = await request.json()
    session_service.update_image_settings(image, settings_from_payload(payload, image.settings))
    return JSONResponse(session_service.serialize_image(image))


@app.post("/api/sessions/{session_id}/settings/apply-to-all")
async def apply_settings_to_all(session_id: str, request: Request) -> JSONResponse:
    session = get_session(session_id)
    payload = await request.json()
    try:
        session_service.apply_settings_to_all(session, settings_from_payload(payload, session.images[0].settings))
    except SessionUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(session_service.serialize_session(session))


@app.get("/api/sessions/{session_id}/images/{image_id}/original")
async def original_preview(session_id: str, image_id: str) -> Response:
    session = get_session(session_id)
    image = get_session_image(session, image_id)
    try:
        data = session_service.render_original_preview_bytes(image.original_path)
        return Response(content=data, media_type="image/jpeg")
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/images/{image_id}/preview")
async def processed_preview(
    session_id: str,
    image_id: str,
    mode: str | None = None,
    percentile: float | None = None,
    exposure: float | None = None,
    white_balance: float | None = None,
    contrast: float | None = None,
    saturation: float | None = None,
    clarity: float | None = None,
    red_tint: float | None = None,
    green_tint: float | None = None,
    blue_tint: float | None = None,
) -> Response:
    session = get_session(session_id)
    image = get_session_image(session, image_id)
    settings = parse_settings_or_400(
        mode=mode or image.settings.mode,
        percentile=image.settings.percentile if percentile is None else percentile,
        exposure=image.settings.exposure if exposure is None else exposure,
        white_balance=image.settings.white_balance if white_balance is None else white_balance,
        contrast=image.settings.contrast if contrast is None else contrast,
        saturation=image.settings.saturation if saturation is None else saturation,
        clarity=image.settings.clarity if clarity is None else clarity,
        red_tint=image.settings.red_tint if red_tint is None else red_tint,
        green_tint=image.settings.green_tint if green_tint is None else green_tint,
        blue_tint=image.settings.blue_tint if blue_tint is None else blue_tint,
    )
    try:
        return Response(content=session_service.render_processed_preview_bytes(image.original_path, settings), media_type="image/jpeg")
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/images/{image_id}/histogram")
async def processed_histogram(
    session_id: str,
    image_id: str,
    mode: str | None = None,
    percentile: float | None = None,
    exposure: float | None = None,
    white_balance: float | None = None,
    contrast: float | None = None,
    saturation: float | None = None,
    clarity: float | None = None,
    red_tint: float | None = None,
    green_tint: float | None = None,
    blue_tint: float | None = None,
) -> JSONResponse:
    session = get_session(session_id)
    image = get_session_image(session, image_id)
    settings = parse_settings_or_400(
        mode=mode or image.settings.mode,
        percentile=image.settings.percentile if percentile is None else percentile,
        exposure=image.settings.exposure if exposure is None else exposure,
        white_balance=image.settings.white_balance if white_balance is None else white_balance,
        contrast=image.settings.contrast if contrast is None else contrast,
        saturation=image.settings.saturation if saturation is None else saturation,
        clarity=image.settings.clarity if clarity is None else clarity,
        red_tint=image.settings.red_tint if red_tint is None else red_tint,
        green_tint=image.settings.green_tint if green_tint is None else green_tint,
        blue_tint=image.settings.blue_tint if blue_tint is None else blue_tint,
    )
    try:
        histogram = session_service.histogram_for_processed_preview(image.original_path, settings)
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"settings": asdict(settings), "histogram": histogram})


@app.get("/api/sessions/{session_id}/images/{image_id}/download")
async def download_image(session_id: str, image_id: str) -> Response:
    session = get_session(session_id)
    image = get_session_image(session, image_id)
    stem = Path(image.filename).stem
    filename = f"{stem}_positive.jpg"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    try:
        content = session_service.render_processed_download_bytes(image.original_path, image.settings)
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=content, media_type="image/jpeg", headers=headers)


@app.get("/api/sessions/{session_id}/download.zip")
async def download_zip(session_id: str) -> StreamingResponse:
    session = get_session(session_id)
    try:
        data = session_service.render_session_zip(session)
    except UnsupportedImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    buffer = BytesIO(data)
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="negative-session-{session_id}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)