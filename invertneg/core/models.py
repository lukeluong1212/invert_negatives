from __future__ import annotations

from dataclasses import dataclass

from invertneg.core.image_processing import (
    DEFAULT_CLARITY,
    DEFAULT_CONTRAST,
    DEFAULT_EXPOSURE,
    DEFAULT_PERCENTILE,
    DEFAULT_SATURATION,
    DEFAULT_TINT,
    DEFAULT_WHITE_BALANCE,
    clamp_clarity,
    clamp_contrast,
    clamp_exposure,
    clamp_percentile,
    clamp_saturation,
    clamp_tint,
    clamp_white_balance,
)


VALID_MODES = {"auto", "color", "bw"}


@dataclass
class ImageSettings:
    mode: str = "auto"
    percentile: float = DEFAULT_PERCENTILE
    exposure: float = DEFAULT_EXPOSURE
    white_balance: float = DEFAULT_WHITE_BALANCE
    contrast: float = DEFAULT_CONTRAST
    saturation: float = DEFAULT_SATURATION
    clarity: float = DEFAULT_CLARITY
    red_tint: float = DEFAULT_TINT
    green_tint: float = DEFAULT_TINT
    blue_tint: float = DEFAULT_TINT


def parse_settings(
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
    if mode not in VALID_MODES:
        raise ValueError("Invalid mode")

    return ImageSettings(
        mode=mode,
        percentile=clamp_percentile(percentile),
        exposure=clamp_exposure(exposure),
        white_balance=clamp_white_balance(white_balance),
        contrast=clamp_contrast(contrast),
        saturation=clamp_saturation(saturation),
        clarity=clamp_clarity(clarity),
        red_tint=clamp_tint(red_tint),
        green_tint=clamp_tint(green_tint),
        blue_tint=clamp_tint(blue_tint),
    )
