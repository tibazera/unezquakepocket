#!/usr/bin/env python3
"""Capture and compare deterministic uNezQuake demo telemetry."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import sys
from typing import Any


SCHEMA_VERSION = 1
FRAME_FIELDS = (
    "valid_sequence",
    "demo_time",
    "physics_frame",
    "origin",
    "velocity",
    "angles",
    "onground",
    "waterlevel",
    "weapon",
    "weapon_frame",
    "command",
    "events",
)


class RegressionError(RuntimeError):
    pass


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegressionError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegressionError(f"{path} must contain a JSON object")
    return value


def read_telemetry(path: pathlib.Path) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    header_seen = False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RegressionError(f"cannot read telemetry {path}: {exc}") from exc

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RegressionError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise RegressionError(f"{path}:{line_number}: record must be an object")
        record_type = record.get("type")
        if record_type == "header":
            if header_seen or frames:
                raise RegressionError(f"{path}:{line_number}: misplaced duplicate header")
            if record.get("schema") != SCHEMA_VERSION:
                raise RegressionError(f"{path}:{line_number}: unsupported schema")
            header_seen = True
        elif record_type == "frame":
            if not header_seen:
                raise RegressionError(f"{path}:{line_number}: frame before header")
            missing = [field for field in FRAME_FIELDS if field not in record]
            if missing:
                raise RegressionError(
                    f"{path}:{line_number}: missing fields: {', '.join(missing)}"
                )
            frames.append({field: record[field] for field in FRAME_FIELDS})
        elif record_type != "end":
            raise RegressionError(f"{path}:{line_number}: unknown record type {record_type!r}")

    if not header_seen:
        raise RegressionError(f"{path}: missing telemetry header")
    if not frames:
        raise RegressionError(f"{path}: contains no frames")
    return frames


def canonical_hash(frames: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        frames, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def write_baseline(
    baseline_path: pathlib.Path, demo_id: str, telemetry_path: pathlib.Path
) -> None:
    frames = read_telemetry(telemetry_path)
    if baseline_path.exists():
        baseline = read_json(baseline_path)
    else:
        baseline = {"schema": SCHEMA_VERSION, "demos": {}}
    if baseline.get("schema") != SCHEMA_VERSION:
        raise RegressionError("unsupported baseline schema")
    demos = baseline.setdefault("demos", {})
    if not isinstance(demos, dict):
        raise RegressionError("baseline demos must be an object")
    demos[demo_id] = {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "frame_count": len(frames),
        "telemetry_sha256": canonical_hash(frames),
        "frames": frames,
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def compare_value(
    expected: Any,
    actual: Any,
    path: str,
    tolerance: float,
    differences: list[str],
) -> None:
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected is not actual:
            differences.append(f"{path}: expected {expected!r}, got {actual!r}")
        return
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if not (math.isfinite(float(expected)) and math.isfinite(float(actual))):
            differences.append(f"{path}: non-finite value")
            return
        scale = max(abs(float(expected)), 1.0)
        relative_error = abs(float(actual) - float(expected)) / scale
        if relative_error > tolerance:
            differences.append(
                f"{path}: expected {expected!r}, got {actual!r}, "
                f"relative error {relative_error:.8%}"
            )
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            differences.append(f"{path}: expected {len(expected)} values, got {len(actual)}")
            return
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            compare_value(
                expected_item, actual_item, f"{path}[{index}]", tolerance, differences
            )
        return
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            differences.append(f"{path}: object keys differ")
            return
        for key in expected:
            compare_value(expected[key], actual[key], f"{path}.{key}", tolerance, differences)
        return
    if expected != actual:
        differences.append(f"{path}: expected {expected!r}, got {actual!r}")


def compare_baseline(
    baseline_path: pathlib.Path,
    demo_id: str,
    telemetry_path: pathlib.Path,
    tolerance: float,
) -> None:
    baseline = read_json(baseline_path)
    demos = baseline.get("demos")
    if baseline.get("schema") != SCHEMA_VERSION or not isinstance(demos, dict):
        raise RegressionError("invalid baseline")
    expected_entry = demos.get(demo_id)
    if not isinstance(expected_entry, dict) or not isinstance(expected_entry.get("frames"), list):
        raise RegressionError(f"baseline has no demo {demo_id!r}")
    expected_frames = expected_entry["frames"]
    actual_frames = read_telemetry(telemetry_path)
    if len(expected_frames) != len(actual_frames):
        raise RegressionError(
            f"frame count differs: expected {len(expected_frames)}, got {len(actual_frames)}"
        )

    differences: list[str] = []
    for index, (expected, actual) in enumerate(zip(expected_frames, actual_frames)):
        compare_value(expected, actual, f"frame[{index}]", tolerance, differences)
        if len(differences) >= 20:
            break
    if differences:
        raise RegressionError("telemetry diverged:\n  " + "\n  ".join(differences))


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise RegressionError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def verify_manifest(manifest_path: pathlib.Path, require_files: bool) -> None:
    manifest = read_json(manifest_path)
    if manifest.get("schema") != SCHEMA_VERSION or not isinstance(manifest.get("demos"), list):
        raise RegressionError("invalid reference demo manifest")
    ids: set[str] = set()
    for index, entry in enumerate(manifest["demos"]):
        if not isinstance(entry, dict):
            raise RegressionError(f"manifest demo {index} must be an object")
        demo_id = entry.get("id")
        categories = entry.get("categories")
        relative_file = entry.get("file")
        if not isinstance(demo_id, str) or not demo_id:
            raise RegressionError(f"manifest demo {index} has no id")
        if demo_id in ids:
            raise RegressionError(f"duplicate demo id {demo_id!r}")
        ids.add(demo_id)
        if not isinstance(categories, list) or not categories:
            raise RegressionError(f"demo {demo_id!r} has no categories")
        if relative_file is None and not require_files:
            continue
        if not isinstance(relative_file, str) or not relative_file:
            raise RegressionError(f"demo {demo_id!r} has no file")
        demo_path = manifest_path.parent / relative_file
        if not demo_path.is_file():
            raise RegressionError(f"demo {demo_id!r} is missing: {demo_path}")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise RegressionError(f"demo {demo_id!r} has no valid SHA-256")
        actual_hash = sha256_file(demo_path)
        if actual_hash.lower() != expected_hash.lower():
            raise RegressionError(f"demo {demo_id!r} SHA-256 mismatch")


def run_engine(args: argparse.Namespace) -> pathlib.Path:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    telemetry = output_dir / f"{args.demo_id}.jsonl"
    engine_telemetry = args.quake_dir.resolve() / telemetry.name
    if telemetry.exists():
        telemetry.unlink()
    if engine_telemetry.exists():
        engine_telemetry.unlink()
    command = [
        str(args.executable.resolve()),
        "-basedir",
        str(args.quake_dir.resolve()),
        "-nohome",
        "-nosound",
        "-window",
        "-width",
        "640",
        "-height",
        "480",
        "+cl_independentPhysics",
        "0",
        "+demo_benchmarkdumps",
        "0",
        "+demo_regression_start",
        telemetry.name,
        "+alias",
        "f_demoend",
        "demo_regression_finish",
        "+timedemo2",
        args.demo,
        str(args.fps),
    ]
    command.extend(args.extra_arg)
    try:
        completed = subprocess.run(
            command, cwd=output_dir, timeout=args.timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RegressionError(f"engine execution failed: {exc}") from exc
    if completed.returncode != 0:
        raise RegressionError(f"engine exited with code {completed.returncode}")
    if engine_telemetry.exists():
        shutil.move(engine_telemetry, telemetry)
    read_telemetry(telemetry)
    return telemetry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify-manifest")
    verify.add_argument("manifest", type=pathlib.Path)
    verify.add_argument("--require-files", action="store_true")

    capture = subparsers.add_parser("capture")
    capture.add_argument("--baseline", required=True, type=pathlib.Path)
    capture.add_argument("--demo-id", required=True)
    capture.add_argument("telemetry", type=pathlib.Path)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--baseline", required=True, type=pathlib.Path)
    compare.add_argument("--demo-id", required=True)
    compare.add_argument("--tolerance", type=float, default=0.001)
    compare.add_argument("telemetry", type=pathlib.Path)

    run = subparsers.add_parser("run")
    run.add_argument("--executable", required=True, type=pathlib.Path)
    run.add_argument("--quake-dir", required=True, type=pathlib.Path)
    run.add_argument("--output-dir", required=True, type=pathlib.Path)
    run.add_argument("--demo-id", required=True)
    run.add_argument("--demo", required=True)
    run.add_argument("--fps", type=int, default=308)
    run.add_argument("--timeout", type=float, default=300)
    run.add_argument("--extra-arg", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify-manifest":
            verify_manifest(args.manifest, args.require_files)
        elif args.command == "capture":
            write_baseline(args.baseline, args.demo_id, args.telemetry)
        elif args.command == "compare":
            if not 0 <= args.tolerance <= 1:
                raise RegressionError("tolerance must be between 0 and 1")
            compare_baseline(args.baseline, args.demo_id, args.telemetry, args.tolerance)
        elif args.command == "run":
            telemetry = run_engine(args)
            print(telemetry)
    except RegressionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
