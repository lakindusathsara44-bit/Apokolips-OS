#!/usr/bin/env python3
"""Build a deterministic raw BIOS image for Apokolips OS BL-1."""
from __future__ import annotations
import argparse
from pathlib import Path

SECTOR_SIZE = 512
STAGE2_SECTORS = 32
STAGE2_SIZE = SECTOR_SIZE * STAGE2_SECTORS
MANIFEST_MAGIC = b"APOKMAN1"


def read_required(path: Path, label: str) -> bytes:
    if not path.is_file():
        raise SystemExit(f"Missing {label}: {path}")
    data = path.read_bytes()
    if not data:
        raise SystemExit(f"{label} is empty: {path}")
    return data


def build(boot_path: Path, stage2_path: Path, output_path: Path) -> None:
    boot = read_required(boot_path, "Stage 1 binary")
    stage2 = read_required(stage2_path, "Stage 2 binary")
    if len(boot) != SECTOR_SIZE:
        raise SystemExit(f"Stage 1 must be 512 bytes; received {len(boot)}.")
    if boot[510:512] != bytes((0x55, 0xAA)):
        raise SystemExit("Stage 1 is missing the 0x55AA BIOS boot signature.")
    if len(stage2) > STAGE2_SIZE:
        raise SystemExit(f"Stage 2 exceeds {STAGE2_SIZE} bytes.")

    stage2_region = stage2.ljust(STAGE2_SIZE, bytes((0,)))
    manifest = bytearray(SECTOR_SIZE)
    manifest[0:8] = MANIFEST_MAGIC
    manifest[8:10] = (1).to_bytes(2, "little")
    manifest[10:12] = STAGE2_SECTORS.to_bytes(2, "little")
    manifest[12:16] = (34).to_bytes(4, "little")

    image = boot + stage2_region + bytes(manifest)
    if len(image) != 34 * SECTOR_SIZE:
        raise AssertionError("Internal image-layout size check failed.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image)
    print(f"Created: {output_path}")
    print(f"Image size: {len(image)} bytes ({len(image) // SECTOR_SIZE} sectors)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot", type=Path, default=Path("build/stage1.bin"))
    parser.add_argument("--stage2", type=Path, default=Path("build/stage2.bin"))
    parser.add_argument("--output", type=Path, default=Path("build/apokolips-bl1.img"))
    args = parser.parse_args()
    build(args.boot, args.stage2, args.output)


if __name__ == "__main__":
    main()
