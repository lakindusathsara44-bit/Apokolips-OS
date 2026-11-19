#!/usr/bin/env python3
"""Build and validate a deterministic raw BIOS image for Apokolips OS BL-1/BL-4."""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

SECTOR_SIZE = 512
STAGE2_SECTORS = 32
STAGE2_SIZE = SECTOR_SIZE * STAGE2_SECTORS
MANIFEST_LBA = 33
PAYLOAD_START_LBA = 34

MANIFEST_MAGIC = b"APOKMAN1"
MANIFEST_VERSION = 1
MANIFEST_HEADER_SIZE = 32
MANIFEST_FLAGS = 0
MANIFEST_CRC_OFFSET = 28
MANIFEST_FORMAT = "<8sHHHHIIII"
MANIFEST_FORMAT_SIZE = struct.calcsize(MANIFEST_FORMAT)


def read_required(path: Path, label: str) -> bytes:
    if not path.is_file():
        raise SystemExit(f"Missing {label}: {path}")
    data = path.read_bytes()
    if not data:
        raise SystemExit(f"{label} is empty: {path}")
    return data


def validate_manifest(manifest: bytes) -> None:
    """Validate the version-1 512-byte Apokolips boot manifest."""
    if len(manifest) != SECTOR_SIZE:
        raise ValueError(f"Manifest must be {SECTOR_SIZE} bytes.")

    (
        magic,
        version,
        header_size,
        stage2_sectors,
        flags,
        payload_start_lba,
        payload_sectors,
        payload_crc32,
        stored_crc32,
    ) = struct.unpack_from(MANIFEST_FORMAT, manifest, 0)

    if magic != MANIFEST_MAGIC:
        raise ValueError("Invalid manifest magic.")
    if version != MANIFEST_VERSION:
        raise ValueError("Unsupported manifest version.")
    if header_size != MANIFEST_HEADER_SIZE:
        raise ValueError("Invalid manifest header size.")
    if stage2_sectors != STAGE2_SECTORS:
        raise ValueError("Manifest Stage 2 size does not match the image layout.")
    if flags != MANIFEST_FLAGS:
        raise ValueError("Unsupported manifest flags.")
    if payload_start_lba < PAYLOAD_START_LBA:
        raise ValueError("Payload overlaps the reserved bootloader/manifest area.")
    if payload_sectors and payload_start_lba > 0xFFFFFFFF - payload_sectors:
        raise ValueError("Payload LBA range overflows the version-1 field.")
    if payload_sectors == 0 and payload_crc32 != 0:
        raise ValueError("An empty payload must have a zero payload checksum.")
    if any(manifest[MANIFEST_HEADER_SIZE:]):
        raise ValueError("Version-1 reserved manifest bytes must be zero.")

    checksum_input = bytearray(manifest)
    checksum_input[MANIFEST_CRC_OFFSET:MANIFEST_CRC_OFFSET + 4] = b"\0\0\0\0"
    calculated_crc32 = zlib.crc32(checksum_input) & 0xFFFFFFFF
    if stored_crc32 != calculated_crc32:
        raise ValueError(
            f"Manifest CRC32 mismatch: stored 0x{stored_crc32:08X}, "
            f"calculated 0x{calculated_crc32:08X}."
        )


def build_manifest() -> bytes:
    """Create the version-1 manifest for an image with no payload yet."""
    manifest = bytearray(SECTOR_SIZE)
    struct.pack_into(
        MANIFEST_FORMAT,
        manifest,
        0,
        MANIFEST_MAGIC,
        MANIFEST_VERSION,
        MANIFEST_HEADER_SIZE,
        STAGE2_SECTORS,
        MANIFEST_FLAGS,
        PAYLOAD_START_LBA,
        0,  # No kernel payload is included in BL-4.
        0,  # Empty payload checksum.
        0,  # CRC field is zero while the sector checksum is calculated.
    )
    checksum = zlib.crc32(manifest) & 0xFFFFFFFF
    struct.pack_into("<I", manifest, MANIFEST_CRC_OFFSET, checksum)

    result = bytes(manifest)
    validate_manifest(result)
    return result


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
    manifest = build_manifest()
    image = boot + stage2_region + manifest
    expected_size = (MANIFEST_LBA + 1) * SECTOR_SIZE
    if len(image) != expected_size:
        raise AssertionError("Internal image-layout size check failed.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image)
    print(f"Created: {output_path}")
    print(f"Image size: {len(image)} bytes ({len(image) // SECTOR_SIZE} sectors)")
    print(f"Manifest CRC32: 0x{int.from_bytes(manifest[MANIFEST_CRC_OFFSET:MANIFEST_CRC_OFFSET + 4], 'little'):08X}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot", type=Path, default=Path("build/stage1.bin"))
    parser.add_argument("--stage2", type=Path, default=Path("build/stage2.bin"))
    parser.add_argument("--output", type=Path, default=Path("build/apokolips-bl1.img"))
    args = parser.parse_args()
    build(args.boot, args.stage2, args.output)


if __name__ == "__main__":
    main()
