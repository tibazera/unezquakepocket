#!/usr/bin/env python3
"""Parse uNezQuake timedemo output and enforce benchmark thresholds."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


RESULT_RE = re.compile(
    r"(?P<frames>\d+) frames\s+(?P<seconds>[0-9.]+) seconds\s+(?P<fps>[0-9.]+) fps"
)
FRAMETIME_RE = re.compile(
    r"avg frametime (?P<average_ms>[0-9.]+)ms, std dev (?P<stddev_ms>[0-9.]+)ms"
)
WORST_RE = re.compile(
    r"worst frametime (?P<worst_ms>[0-9.]+)ms,\s*(?P<worst_fps>[0-9.]+)fps"
)


class BenchmarkError(RuntimeError):
    pass


def parse_timedemo(text: str) -> dict[str, Any]:
    result_match = RESULT_RE.search(text)
    if not result_match:
        raise BenchmarkError("timedemo result line not found")
    result: dict[str, Any] = {
        "schema": 1,
        "frames": int(result_match.group("frames")),
        "seconds": float(result_match.group("seconds")),
        "fps": {
            "average": float(result_match.group("fps")),
        },
    }
    frametime_match = FRAMETIME_RE.search(text)
    if frametime_match:
        result["frametime_ms"] = {
            "average": float(frametime_match.group("average_ms")),
            "stddev": float(frametime_match.group("stddev_ms")),
        }
    worst_match = WORST_RE.search(text)
    if worst_match:
        result.setdefault("frametime_ms", {})["worst"] = float(
            worst_match.group("worst_ms")
        )
        result["fps"]["worst"] = float(worst_match.group("worst_fps"))
    return result


def read_report(path: pathlib.Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkError(f"cannot read {path}: {exc}") from exc
    if not isinstance(report, dict) or report.get("schema") != 1:
        raise BenchmarkError(f"invalid benchmark report: {path}")
    return report


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    max_fps_drop: float,
    max_ram_growth: float,
) -> None:
    try:
        baseline_fps = float(baseline["fps"]["average"])
        candidate_fps = float(candidate["fps"]["average"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BenchmarkError("reports must contain fps.average") from exc
    if baseline_fps <= 0:
        raise BenchmarkError("baseline FPS must be positive")
    fps_drop = (baseline_fps - candidate_fps) / baseline_fps
    if fps_drop > max_fps_drop:
        raise BenchmarkError(
            f"FPS regression {fps_drop:.2%} exceeds {max_fps_drop:.2%}"
        )

    baseline_ram = baseline.get("memory", {}).get("peak_rss_bytes")
    candidate_ram = candidate.get("memory", {}).get("peak_rss_bytes")
    if baseline_ram is not None and candidate_ram is not None:
        if float(baseline_ram) <= 0:
            raise BenchmarkError("baseline peak RSS must be positive")
        ram_growth = (float(candidate_ram) - float(baseline_ram)) / float(baseline_ram)
        if ram_growth > max_ram_growth:
            raise BenchmarkError(
                f"RAM regression {ram_growth:.2%} exceeds {max_ram_growth:.2%}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse = subparsers.add_parser("parse")
    parse.add_argument("input", type=pathlib.Path)
    parse.add_argument("--output", required=True, type=pathlib.Path)

    compare = subparsers.add_parser("compare")
    compare.add_argument("baseline", type=pathlib.Path)
    compare.add_argument("candidate", type=pathlib.Path)
    compare.add_argument("--max-fps-drop", type=float, default=0.10)
    compare.add_argument("--max-ram-growth", type=float, default=0.15)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "parse":
            report = parse_timedemo(args.input.read_text(encoding="utf-8"))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        else:
            if not 0 <= args.max_fps_drop <= 1 or not 0 <= args.max_ram_growth <= 1:
                raise BenchmarkError("thresholds must be between 0 and 1")
            compare_reports(
                read_report(args.baseline),
                read_report(args.candidate),
                args.max_fps_drop,
                args.max_ram_growth,
            )
    except (BenchmarkError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
