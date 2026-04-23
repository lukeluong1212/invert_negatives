import argparse
import glob
import sys
from pathlib import Path

from image_processing import (
    MAX_CLARITY,
    MAX_CONTRAST,
    MAX_EXPOSURE,
    MAX_SATURATION,
    MAX_TINT,
    MAX_WHITE_BALANCE,
    MIN_CLARITY,
    MIN_CONTRAST,
    MIN_EXPOSURE,
    MIN_SATURATION,
    MIN_TINT,
    MIN_WHITE_BALANCE,
    convert_negative_file,
)


def expand_input_paths(inputs: list[str]) -> list[Path]:
    """Expand wildcard input patterns so shells without glob expansion still work."""
    expanded_paths: list[Path] = []

    for item in inputs:
        matches = [Path(match) for match in glob.glob(item)]
        if matches:
            expanded_paths.extend(matches)
            continue

        candidate = Path(item)
        if candidate.exists():
            expanded_paths.append(candidate)
            continue

        print(f"Error: no files matched input: {item}", file=sys.stderr)
        sys.exit(1)

    return expanded_paths


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert a scanned film negative JPEG to a positive image.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input", nargs="+", help="Input negative file(s) (JPEG, PNG, TIFF, …)")
    p.add_argument("-o", "--output", help="Output file path (only valid for single input)")
    p.add_argument(
        "--output-dir",
        default="output",
        help="Folder where positive files are saved (default: output/)",
    )
    p.add_argument(
        "--mode",
        choices=["auto", "color", "bw"],
        default="auto",
        help="Processing mode: auto-detect, force colour, or force B&W",
    )
    p.add_argument(
        "--percentile",
        type=float,
        default=0.5,
        help="Clipping percentile for auto-stretch (0–5; lower = less aggressive)",
    )
    p.add_argument(
        "--exposure",
        type=float,
        default=0.0,
        help=f"Exposure adjustment in stops ({MIN_EXPOSURE} to {MAX_EXPOSURE})",
    )
    p.add_argument(
        "--white-balance",
        type=float,
        default=0.0,
        help=f"White balance shift ({MIN_WHITE_BALANCE} cool to {MAX_WHITE_BALANCE} warm)",
    )
    p.add_argument(
        "--contrast",
        type=float,
        default=0.0,
        help=f"Contrast adjustment percentage ({MIN_CONTRAST} to {MAX_CONTRAST})",
    )
    p.add_argument(
        "--saturation",
        type=float,
        default=0.0,
        help=f"Saturation adjustment percentage ({MIN_SATURATION} to {MAX_SATURATION})",
    )
    p.add_argument(
        "--clarity",
        type=float,
        default=0.0,
        help=f"Clarity adjustment percentage ({MIN_CLARITY} to {MAX_CLARITY})",
    )
    p.add_argument(
        "--red-tint",
        type=float,
        default=0.0,
        help=f"Red channel tint percentage ({MIN_TINT} to {MAX_TINT})",
    )
    p.add_argument(
        "--green-tint",
        type=float,
        default=0.0,
        help=f"Green channel tint percentage ({MIN_TINT} to {MAX_TINT})",
    )
    p.add_argument(
        "--blue-tint",
        type=float,
        default=0.0,
        help=f"Blue channel tint percentage ({MIN_TINT} to {MAX_TINT})",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    input_paths = expand_input_paths(args.input)

    if args.output and len(input_paths) > 1:
        print("Error: --output can only be used with a single input file.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for src in input_paths:
        if args.output:
            dst = args.output
        else:
            dst = out_dir / f"{src.stem}_positive{src.suffix}"
        result = convert_negative_file(
            src,
            output_path=dst,
            mode=args.mode,
            percentile=args.percentile,
            exposure=args.exposure,
            white_balance=args.white_balance,
            contrast=args.contrast,
            saturation=args.saturation,
            clarity=args.clarity,
            red_tint=args.red_tint,
            green_tint=args.green_tint,
            blue_tint=args.blue_tint,
        )
        print(f"Saved: {result}")


if __name__ == "__main__":
    main()
