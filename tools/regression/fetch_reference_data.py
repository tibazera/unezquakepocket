#!/usr/bin/env python3
"""Fetch hash-pinned Quake shareware data for local regression tests."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import pathlib
import shutil
import sys
import urllib.error
import urllib.request
import zipfile


SHAREWARE_URL = "https://fte.triptohell.info/qsw106.zip"
SHAREWARE_SHA256 = "edf532a91d8ce2482bc0ee9bbc47f2e4076bb891fe8fd8767c3acee5818b710e"
PAK0_SHA256 = "35a9c55e5e5a284a159ad2a62e0e8def23d829561fe2f54eb402dbc0a9a946af"


class FetchError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: pathlib.Path) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "uNezQuake-regression/1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out)
        partial.replace(destination)
    except (OSError, urllib.error.URLError) as exc:
        if partial.exists():
            partial.unlink()
        raise FetchError(f"download failed: {exc}") from exc


def find_member(archive: zipfile.ZipFile, wanted: str) -> str:
    wanted_lower = wanted.lower()
    for member in archive.namelist():
        if member.lower() == wanted_lower:
            return member
    raise FetchError(f"archive is missing {wanted}")


def prepare(data_dir: pathlib.Path) -> pathlib.Path:
    data_dir = data_dir.resolve()
    archive_path = data_dir / "qsw106.zip"
    if not archive_path.exists() or sha256_file(archive_path) != SHAREWARE_SHA256:
        download(SHAREWARE_URL, archive_path)
    archive_hash = sha256_file(archive_path)
    if archive_hash != SHAREWARE_SHA256:
        raise FetchError(
            f"shareware archive hash mismatch: expected {SHAREWARE_SHA256}, got {archive_hash}"
        )

    quake_dir = data_dir / "quake"
    pak_path = quake_dir / "id1" / "pak0.pak"
    pak_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with gzip.open(archive_path, "rb") as compressed:
            zip_payload = compressed.read()
    except OSError as exc:
        raise FetchError(f"invalid shareware gzip envelope: {exc}") from exc

    with zipfile.ZipFile(io.BytesIO(zip_payload)) as archive:
        pak_member = find_member(archive, "ID1/PAK0.PAK")
        with archive.open(pak_member) as source, pak_path.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        for license_name in ("SLICNSE.TXT", "LICINFO.TXT"):
            member = find_member(archive, license_name)
            with archive.open(member) as source, (data_dir / license_name).open("wb") as destination:
                shutil.copyfileobj(source, destination)

    pak_hash = sha256_file(pak_path)
    if pak_hash != PAK0_SHA256:
        raise FetchError(f"pak0 hash mismatch: expected {PAK0_SHA256}, got {pak_hash}")
    (quake_dir / "qw").mkdir(parents=True, exist_ok=True)
    return quake_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=pathlib.Path, default=pathlib.Path("tests/data"))
    parser.add_argument(
        "--accept-shareware-license",
        action="store_true",
        help="acknowledge the bundled id Software shareware license for local use",
    )
    args = parser.parse_args(argv)
    if not args.accept_shareware_license:
        print(
            "error: pass --accept-shareware-license after reviewing SLICNSE.TXT; "
            "the assets are not GPL and must not be committed",
            file=sys.stderr,
        )
        return 2
    try:
        quake_dir = prepare(args.data_dir)
        print(quake_dir)
    except (FetchError, OSError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
