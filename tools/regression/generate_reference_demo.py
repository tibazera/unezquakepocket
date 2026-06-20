#!/usr/bin/env python3
"""Generate a deterministic QWD using an existing legal Quake data directory."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys


class GenerationError(RuntimeError):
    pass


def generate(
    executable: pathlib.Path,
    quake_dir: pathlib.Path,
    output: pathlib.Path,
    timeout: float,
) -> pathlib.Path:
    executable = executable.resolve()
    quake_dir = quake_dir.resolve()
    output = output.resolve()
    if not executable.is_file():
        raise GenerationError(f"executable not found: {executable}")
    if not (quake_dir / "id1" / "pak0.pak").is_file():
        raise GenerationError(f"quake data not found under {quake_dir}")
    qw_dir = quake_dir / "qw"
    qw_dir.mkdir(parents=True, exist_ok=True)
    old_candidates = set(quake_dir.rglob("phase0_shareware_e1m1.qwd"))
    log_path = quake_dir / "reference_generation.log"
    if log_path.exists():
        log_path.unlink()

    command = [
        str(executable),
        "-basedir",
        str(quake_dir),
        "-nohome",
        "-nosound",
        "-window",
        "-width",
        "640",
        "-height",
        "480",
        "-condebug",
        str(log_path),
        "+demo_regression_generate_reference",
    ]
    try:
        completed = subprocess.run(
            command, cwd=quake_dir, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GenerationError(f"client execution failed: {exc}") from exc
    if completed.returncode != 0:
        raise GenerationError(f"client exited with code {completed.returncode}")

    candidates = set(quake_dir.rglob("phase0_shareware_e1m1.qwd"))
    generated = sorted(candidates - old_candidates, key=lambda path: path.stat().st_mtime)
    if not generated:
        generated = sorted(candidates, key=lambda path: path.stat().st_mtime)
    if not generated:
        raise GenerationError(f"client produced no QWD; inspect {log_path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generated[-1], output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=pathlib.Path)
    parser.add_argument("--quake-dir", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args(argv)
    try:
        output = generate(
            args.executable, args.quake_dir, args.output, args.timeout
        )
        print(output)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
