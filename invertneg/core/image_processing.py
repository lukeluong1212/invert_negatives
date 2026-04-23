from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


DEFAULT_PERCENTILE = 0.5
DEFAULT_EXPOSURE = 0.0
DEFAULT_TINT = 0.0
DEFAULT_WHITE_BALANCE = 0.0
DEFAULT_CONTRAST = 0.0
DEFAULT_SATURATION = 0.0
DEFAULT_CLARITY = 0.0
MIN_PERCENTILE = 0.0
MAX_PERCENTILE = 5.0
MIN_EXPOSURE = -4.0
MAX_EXPOSURE = 4.0
MIN_TINT = -100.0
MAX_TINT = 100.0
MIN_WHITE_BALANCE = -100.0
MAX_WHITE_BALANCE = 100.0
MIN_CONTRAST = -100.0
MAX_CONTRAST = 100.0
MIN_SATURATION = -100.0
MAX_SATURATION = 100.0
MIN_CLARITY = -100.0
MAX_CLARITY = 100.0


def clamp_percentile(percentile: float) -> float:
    return float(min(max(percentile, MIN_PERCENTILE), MAX_PERCENTILE))


def clamp_exposure(exposure: float) -> float:
    return float(min(max(exposure, MIN_EXPOSURE), MAX_EXPOSURE))


def clamp_tint(tint: float) -> float:
    return float(min(max(tint, MIN_TINT), MAX_TINT))


def clamp_white_balance(white_balance: float) -> float:
    return float(min(max(white_balance, MIN_WHITE_BALANCE), MAX_WHITE_BALANCE))


def clamp_contrast(contrast: float) -> float:
    return float(min(max(contrast, MIN_CONTRAST), MAX_CONTRAST))


def clamp_saturation(saturation: float) -> float:
    return float(min(max(saturation, MIN_SATURATION), MAX_SATURATION))


def clamp_clarity(clarity: float) -> float:
    return float(min(max(clarity, MIN_CLARITY), MAX_CLARITY))


def apply_contrast(image: Image.Image, contrast: float) -> Image.Image:
    factor = 1.0 + clamp_contrast(contrast) / 100.0
    return ImageEnhance.Contrast(image).enhance(factor)


def apply_saturation(image: Image.Image, saturation: float) -> Image.Image:
    factor = 1.0 + clamp_saturation(saturation) / 100.0
    return ImageEnhance.Color(image).enhance(factor)


def apply_clarity(image: Image.Image, clarity: float) -> Image.Image:
    value = clamp_clarity(clarity)
    if value == 0:
        return image

    amount = abs(value) / 100.0
    if value > 0:
        percent = int(80 + amount * 170)
        return image.filter(ImageFilter.UnsharpMask(radius=1.6, percent=percent, threshold=2))

    blur_radius = 0.5 + amount * 1.5
    alpha = amount * 0.35
    blurred = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return Image.blend(image, blurred, alpha)


def invert_bw(img_array: np.ndarray) -> np.ndarray:
    return 255 - img_array


def apply_exposure(img_array: np.ndarray, exposure: float) -> np.ndarray:
    multiplier = 2.0 ** clamp_exposure(exposure)
    adjusted = img_array.astype(np.float32) * multiplier
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def apply_rgb_tint(
    img_array: np.ndarray,
    red_tint: float = DEFAULT_TINT,
    green_tint: float = DEFAULT_TINT,
    blue_tint: float = DEFAULT_TINT,
) -> np.ndarray:
    multipliers = np.array(
        [
            1.0 + clamp_tint(red_tint) / 100.0,
            1.0 + clamp_tint(green_tint) / 100.0,
            1.0 + clamp_tint(blue_tint) / 100.0,
        ],
        dtype=np.float32,
    )
    adjusted = img_array.astype(np.float32) * multipliers
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def apply_white_balance(img_array: np.ndarray, white_balance: float = DEFAULT_WHITE_BALANCE) -> np.ndarray:
    # Positive values warm the image (more red, less blue); negative values cool it.
    wb = clamp_white_balance(white_balance)
    warm_shift = wb / 100.0 * 0.4
    multipliers = np.array(
        [1.0 + warm_shift, 1.0, 1.0 - warm_shift],
        dtype=np.float32,
    )
    adjusted = img_array.astype(np.float32) * multipliers
    return np.clip(adjusted, 0, 255).astype(np.uint8)


def correct_orange_mask(img_array: np.ndarray, percentile: float = DEFAULT_PERCENTILE) -> np.ndarray:
    percentile = clamp_percentile(percentile)
    inverted = 255.0 - img_array.astype(np.float32)

    output = np.empty_like(inverted)
    for ch in range(3):
        channel = inverted[:, :, ch]
        lo = np.percentile(channel, percentile)
        hi = np.percentile(channel, 100.0 - percentile)
        if hi > lo:
            stretched = (channel - lo) / (hi - lo) * 255.0
        else:
            stretched = channel
        output[:, :, ch] = np.clip(stretched, 0, 255)

    return output.astype(np.uint8)


def process_image(
    image: Image.Image,
    mode: str = "auto",
    percentile: float = DEFAULT_PERCENTILE,
    exposure: float = DEFAULT_EXPOSURE,
    white_balance: float = DEFAULT_WHITE_BALANCE,
    contrast: float = DEFAULT_CONTRAST,
    saturation: float = DEFAULT_SATURATION,
    clarity: float = DEFAULT_CLARITY,
    red_tint: float = DEFAULT_TINT,
    green_tint: float = DEFAULT_TINT,
    blue_tint: float = DEFAULT_TINT,
) -> Image.Image:
    working = ImageOps.exif_transpose(image)
    is_color = working.mode in ("RGB", "RGBA", "P")
    if mode == "bw":
        is_color = False
    elif mode == "color":
        is_color = True

    if is_color:
        rgb = working.convert("RGB")
        result_arr = correct_orange_mask(np.array(rgb), percentile=percentile)
        if white_balance != 0:
            result_arr = apply_white_balance(result_arr, white_balance=white_balance)
        if exposure != 0:
            result_arr = apply_exposure(result_arr, exposure)
        if red_tint != 0 or green_tint != 0 or blue_tint != 0:
            result_arr = apply_rgb_tint(result_arr, red_tint=red_tint, green_tint=green_tint, blue_tint=blue_tint)
        result = Image.fromarray(result_arr, mode="RGB")
        if contrast != 0:
            result = apply_contrast(result, contrast)
        if saturation != 0:
            result = apply_saturation(result, saturation)
        if clarity != 0:
            result = apply_clarity(result, clarity)
        return result

    gray = working.convert("L")
    result_arr = invert_bw(np.array(gray))
    if exposure != 0:
        result_arr = apply_exposure(result_arr, exposure)
    result = Image.fromarray(result_arr, mode="L")
    if contrast != 0:
        result = apply_contrast(result, contrast)
    if clarity != 0:
        result = apply_clarity(result, clarity)
    return result


def convert_negative_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    mode: str = "auto",
    percentile: float = DEFAULT_PERCENTILE,
    exposure: float = DEFAULT_EXPOSURE,
    white_balance: float = DEFAULT_WHITE_BALANCE,
    contrast: float = DEFAULT_CONTRAST,
    saturation: float = DEFAULT_SATURATION,
    clarity: float = DEFAULT_CLARITY,
    red_tint: float = DEFAULT_TINT,
    green_tint: float = DEFAULT_TINT,
    blue_tint: float = DEFAULT_TINT,
) -> Path:
    input_path = Path(input_path)
    if output_path is None:
        out_dir = Path("output")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{input_path.stem}_positive{input_path.suffix}"
    output_path = Path(output_path)

    with Image.open(input_path) as image:
        result = process_image(
            image,
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
        result.save(output_path, quality=95)

    return output_path


def image_to_bytes(image: Image.Image, format_name: str = "JPEG", quality: int = 90) -> bytes:
    buffer = BytesIO()
    save_kwargs: dict[str, int | str] = {"format": format_name}
    if format_name.upper() in {"JPEG", "JPG"}:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        save_kwargs["quality"] = quality
    image.save(buffer, **save_kwargs)
    return buffer.getvalue()


def make_preview(image: Image.Image, max_size: tuple[int, int] = (1600, 1000)) -> Image.Image:
    preview = image.copy()
    preview.thumbnail(max_size)
    return preview
