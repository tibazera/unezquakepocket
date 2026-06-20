#!/usr/bin/env python3
"""Compare uncompressed TGA screenshots without external dependencies."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys
from typing import Any


class ScreenshotError(RuntimeError):
    pass


def read_tga(path: pathlib.Path) -> tuple[int, int, bytes]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ScreenshotError(f"cannot read {path}: {exc}") from exc
    if len(data) < 18:
        raise ScreenshotError(f"{path}: truncated TGA header")
    (
        id_length,
        color_map_type,
        image_type,
        _color_map_first,
        _color_map_length,
        _color_map_depth,
        _x_origin,
        _y_origin,
        width,
        height,
        depth,
        descriptor,
    ) = struct.unpack("<BBBHHBHHHHBB", data[:18])
    if color_map_type != 0 or image_type != 2 or depth not in (24, 32):
        raise ScreenshotError(f"{path}: only uncompressed 24/32-bit true-color TGA is supported")
    channels = depth // 8
    pixel_data = data[18 + id_length :]
    expected_size = width * height * channels
    if len(pixel_data) < expected_size:
        raise ScreenshotError(f"{path}: truncated pixel data")

    rows = []
    stride = width * channels
    for row_index in range(height):
        row = pixel_data[row_index * stride : (row_index + 1) * stride]
        if not descriptor & 0x20:
            rows.insert(0, row)
        else:
            rows.append(row)

    rgb = bytearray(width * height * 3)
    output = 0
    for row in rows:
        for offset in range(0, len(row), channels):
            b, g, r = row[offset : offset + 3]
            rgb[output : output + 3] = bytes((r, g, b))
            output += 3
    return width, height, bytes(rgb)


def compare_images(reference: pathlib.Path, candidate: pathlib.Path) -> dict[str, Any]:
    ref_width, ref_height, ref = read_tga(reference)
    cand_width, cand_height, cand = read_tga(candidate)
    if (ref_width, ref_height) != (cand_width, cand_height):
        raise ScreenshotError(
            f"dimensions differ: {ref_width}x{ref_height} vs {cand_width}x{cand_height}"
        )
    channel_differences = [abs(a - b) for a, b in zip(ref, cand)]
    mean_difference = sum(channel_differences) / (len(channel_differences) * 255.0)
    changed_pixels = sum(
        1
        for offset in range(0, len(ref), 3)
        if ref[offset : offset + 3] != cand[offset : offset + 3]
    )
    return {
        "schema": 1,
        "width": ref_width,
        "height": ref_height,
        "mean_absolute_difference": mean_difference,
        "maximum_channel_difference": max(channel_differences, default=0) / 255.0,
        "changed_pixel_ratio": changed_pixels / (ref_width * ref_height),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=pathlib.Path)
    parser.add_argument("candidate", type=pathlib.Path)
    parser.add_argument("--maximum-difference", type=float, default=0.01)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.maximum_difference <= 1:
            raise ScreenshotError("maximum difference must be between 0 and 1")
        report = compare_images(args.reference, args.candidate)
        text = json.dumps(report, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        if report["mean_absolute_difference"] > args.maximum_difference:
            raise ScreenshotError(
                f"mean image difference {report['mean_absolute_difference']:.4%} "
                f"exceeds {args.maximum_difference:.4%}"
            )
    except ScreenshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
