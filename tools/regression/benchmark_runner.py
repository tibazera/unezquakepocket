#!/usr/bin/env python3
"""Parse uNezQuake timedemo output and enforce benchmark thresholds."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any

try:
    import resource
except ImportError:  # Windows
    resource = None


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


def run_benchmark(command: list[str], timeout: float) -> tuple[dict[str, Any], str]:
    if not command:
        raise BenchmarkError("no benchmark command supplied")
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BenchmarkError(f"benchmark execution failed: {exc}") from exc
    elapsed = time.perf_counter() - start
    if completed.returncode != 0:
        raise BenchmarkError(
            f"benchmark exited with code {completed.returncode}\n{completed.stdout}"
        )
    report = parse_timedemo(completed.stdout)
    report["process"] = {
        "elapsed_seconds": elapsed,
        "return_code": completed.returncode,
        "command": command,
    }
    if resource is not None:
        peak_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        # Linux reports KiB; macOS reports bytes.
        if sys.platform != "darwin":
            peak_rss *= 1024
        report["memory"] = {"peak_rss_bytes": int(peak_rss)}
    return report, completed.stdout


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

    run = subparsers.add_parser("run")
    run.add_argument("--output", required=True, type=pathlib.Path)
    run.add_argument("--log-output", type=pathlib.Path)
    run.add_argument("--timeout", type=float, default=300)
    run.add_argument("command_line", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "parse":
            report = parse_timedemo(args.input.read_text(encoding="utf-8"))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        elif args.command == "compare":
            if not 0 <= args.max_fps_drop <= 1 or not 0 <= args.max_ram_growth <= 1:
                raise BenchmarkError("thresholds must be between 0 and 1")
            compare_reports(
                read_report(args.baseline),
                read_report(args.candidate),
                args.max_fps_drop,
                args.max_ram_growth,
            )
        else:
            command_line = args.command_line
            if command_line and command_line[0] == "--":
                command_line = command_line[1:]
            report, log = run_benchmark(command_line, args.timeout)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            if args.log_output:
                args.log_output.parent.mkdir(parents=True, exist_ok=True)
                args.log_output.write_text(log, encoding="utf-8")
    except (BenchmarkError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
