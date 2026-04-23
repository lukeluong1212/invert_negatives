from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image, UnidentifiedImageError

from invertneg.core.image_processing import image_to_bytes, make_preview, process_image
from invertneg.core.models import ImageSettings


DEFAULT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
DEFAULT_PREVIEW_MAX_SIZE = (1280, 850)
DEFAULT_PREVIEW_JPEG_QUALITY = 84


class SessionError(Exception):
    pass


class SessionNotFoundError(SessionError):
    pass


class SessionImageNotFoundError(SessionError):
    pass


class SessionUploadError(SessionError):
    pass


class UnsupportedImageError(SessionError):
    pass


@dataclass
class SessionImage:
    id: str
    filename: str
    original_path: Path
    settings: ImageSettings = field(default_factory=ImageSettings)
    previous_settings: ImageSettings | None = None


@dataclass
class SessionState:
    id: str
    session_dir: Path
    images: list[SessionImage]


@dataclass
class UploadedFile:
    filename: str
    content: bytes


class SessionService:
    def __init__(
        self,
        session_root: Path,
        allowed_extensions: set[str] | None = None,
        preview_max_size: tuple[int, int] = DEFAULT_PREVIEW_MAX_SIZE,
        preview_jpeg_quality: int = DEFAULT_PREVIEW_JPEG_QUALITY,
    ) -> None:
        self.session_root = session_root
        self.session_root.mkdir(parents=True, exist_ok=True)
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS
        self.preview_max_size = preview_max_size
        self.preview_jpeg_quality = preview_jpeg_quality
        self.sessions: dict[str, SessionState] = {}

    def serialize_image(self, image: SessionImage) -> dict[str, object]:
        return {
            "id": image.id,
            "filename": image.filename,
            "settings": asdict(image.settings),
            "previous_settings": asdict(image.previous_settings) if image.previous_settings else None,
        }

    def serialize_session(self, session: SessionState) -> dict[str, object]:
        return {
            "id": session.id,
            "images": [self.serialize_image(item) for item in session.images],
        }

    def get_session(self, session_id: str) -> SessionState:
        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        return session

    def get_session_image(self, session: SessionState, image_id: str) -> SessionImage:
        for item in session.images:
            if item.id == image_id:
                return item
        raise SessionImageNotFoundError("Image not found")

    def create_session(self, files: list[UploadedFile]) -> SessionState:
        if not files:
            raise SessionUploadError("No files uploaded")

        session_id = uuid.uuid4().hex
        session_dir = self.session_root / session_id
        originals_dir = session_dir / "originals"
        originals_dir.mkdir(parents=True, exist_ok=True)

        images: list[SessionImage] = []
        for upload in files:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in self.allowed_extensions:
                continue

            image_id = uuid.uuid4().hex
            target_path = originals_dir / f"{image_id}{suffix}"
            target_path.write_bytes(upload.content)

            try:
                with Image.open(target_path) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError):
                target_path.unlink(missing_ok=True)
                continue

            images.append(
                SessionImage(
                    id=image_id,
                    filename=upload.filename or target_path.name,
                    original_path=target_path,
                )
            )

        if not images:
            shutil.rmtree(session_dir, ignore_errors=True)
            raise SessionUploadError("No supported image files were uploaded")

        session = SessionState(id=session_id, session_dir=session_dir, images=images)
        self.sessions[session_id] = session
        return session

    def update_image_settings(self, image: SessionImage, settings: ImageSettings) -> None:
        image.previous_settings = image.settings
        image.settings = settings

    def apply_settings_to_all(self, session: SessionState, settings: ImageSettings) -> None:
        if not session.images:
            raise SessionUploadError("Session has no images")
        for image in session.images:
            image.previous_settings = image.settings
            image.settings = ImageSettings(**asdict(settings))

    def render_processed_image(self, image_path: Path, settings: ImageSettings) -> Image.Image:
        try:
            with Image.open(image_path) as source:
                return process_image(
                    source,
                    mode=settings.mode,
                    percentile=settings.percentile,
                    exposure=settings.exposure,
                    white_balance=settings.white_balance,
                    contrast=settings.contrast,
                    saturation=settings.saturation,
                    clarity=settings.clarity,
                    red_tint=settings.red_tint,
                    green_tint=settings.green_tint,
                    blue_tint=settings.blue_tint,
                )
        except UnidentifiedImageError as exc:
            raise UnsupportedImageError("Unsupported image file") from exc

    def render_original_preview_bytes(self, image_path: Path) -> bytes:
        try:
            with Image.open(image_path) as source:
                preview = make_preview(source, max_size=self.preview_max_size)
            return image_to_bytes(preview, format_name="JPEG", quality=self.preview_jpeg_quality)
        except UnidentifiedImageError as exc:
            raise UnsupportedImageError("Unsupported image file") from exc

    def render_processed_preview_bytes(self, image_path: Path, settings: ImageSettings) -> bytes:
        processed = self.render_processed_image(image_path, settings)
        preview = make_preview(processed, max_size=self.preview_max_size)
        return image_to_bytes(preview, format_name="JPEG", quality=self.preview_jpeg_quality)

    def histogram_for_processed_preview(self, image_path: Path, settings: ImageSettings) -> dict[str, list[int]]:
        processed = self.render_processed_image(image_path, settings)
        preview = make_preview(processed, max_size=self.preview_max_size)
        return rgb_histogram(preview)

    def render_processed_download_bytes(self, image_path: Path, settings: ImageSettings) -> bytes:
        processed = self.render_processed_image(image_path, settings)
        return image_to_bytes(processed, format_name="JPEG", quality=95)

    def render_session_zip(self, session: SessionState) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            manifest: list[dict[str, object]] = []
            for image in session.images:
                output_name = f"{Path(image.filename).stem}_positive.jpg"
                archive.writestr(output_name, self.render_processed_download_bytes(image.original_path, image.settings))
                manifest.append({"filename": image.filename, "output": output_name, "settings": asdict(image.settings)})
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))

        return buffer.getvalue()


def rgb_histogram(image: Image.Image) -> dict[str, list[int]]:
    rgb = np.array(image.convert("RGB"))
    red = np.bincount(rgb[:, :, 0].ravel(), minlength=256).astype(int).tolist()
    green = np.bincount(rgb[:, :, 1].ravel(), minlength=256).astype(int).tolist()
    blue = np.bincount(rgb[:, :, 2].ravel(), minlength=256).astype(int).tolist()
    return {"red": red, "green": green, "blue": blue}
