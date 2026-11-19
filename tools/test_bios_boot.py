#!/usr/bin/env python3
"""Run positive and negative BIOS boot tests for BL-2/BL-4."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

SECTOR_SIZE = 512
MANIFEST_LBA = 33
E820_COUNT_PATTERN = re.compile(
    r"BL-2: E820 MEMORY MAP ENTRIES: ([0-9A-F]{2})"
)


def parse_e820_entry_count(output: str) -> int | None:
    """Return the hexadecimal E820 entry count, or None if no success line exists."""
    match = E820_COUNT_PATTERN.search(output)
    if match is None:
        return None
    return int(match.group(1), 16)


def capture_bios_output(
    qemu: str, image_path: Path, timeout_seconds: float
) -> tuple[str, str]:
    """Boot a disposable raw image and return debug-console and stderr output."""
    with tempfile.TemporaryDirectory(prefix="apokolips-qemu-") as temp_dir:
        temp = Path(temp_dir)
        debug_log = temp / "qemu-debugcon.log"
        stderr_log = temp / "qemu-stderr.log"

        command = [
            qemu,
            "-machine", "pc",
            "-m", "64M",
            "-drive", f"file={image_path.resolve()},format=raw,if=ide",
            "-boot", "order=c",
            "-display", "none",
            "-serial", "none",
            "-monitor", "none",
            "-no-reboot",
            "-no-shutdown",
            "-debugcon", f"file:{debug_log}",
            "-global", "isa-debugcon.iobase=0xe9",
        ]

        with stderr_log.open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
            )
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2.0)

        output = (
            debug_log.read_text(encoding="ascii", errors="replace")
            if debug_log.exists()
            else ""
        )
        emulator_errors = stderr_log.read_text(
            encoding="utf-8", errors="replace"
        ).strip()
        return output, emulator_errors


def run_bios_smoke_test(image_path: Path, timeout_seconds: float = 4.0) -> int:
    qemu = shutil.which("qemu-system-x86_64")
    if qemu is None:
        raise SystemExit("QEMU was not found. Install qemu-system-x86 first.")
    if not image_path.is_file():
        raise SystemExit(f"Boot image does not exist: {image_path}")
    if timeout_seconds <= 0:
        raise SystemExit("Timeout must be greater than zero.")

    image_path = image_path.resolve()
    valid_output, valid_stderr = capture_bios_output(
        qemu, image_path, timeout_seconds
    )

    if "BL-4: MANIFEST VALID" not in valid_output:
        details = f"\nQEMU stderr:\n{valid_stderr}" if valid_stderr else ""
        raise SystemExit(
            "BIOS did not accept the valid boot manifest. "
            f"Debug output was:\n{valid_output or '<empty>'}{details}"
        )
    if "BL-4 ERROR:" in valid_output:
        raise SystemExit(f"BIOS reported a manifest error:\n{valid_output}")

    count = parse_e820_entry_count(valid_output)
    if count is None or count < 1:
        raise SystemExit(
            "BIOS did not report a non-zero E820 entry count after manifest "
            f"validation. Debug output was:\n{valid_output or '<empty>'}"
        )

    # Corrupt a reserved byte in the manifest sector without updating its CRC.
    # The guest must reject the image before attempting E820 discovery.
    with tempfile.TemporaryDirectory(prefix="apokolips-invalid-manifest-") as temp_dir:
        invalid_image = Path(temp_dir) / "invalid-manifest.img"
        image_bytes = bytearray(image_path.read_bytes())
        manifest_offset = MANIFEST_LBA * SECTOR_SIZE
        image_bytes[manifest_offset + 100] ^= 0x01
        invalid_image.write_bytes(image_bytes)

        invalid_output, invalid_stderr = capture_bios_output(
            qemu, invalid_image, timeout_seconds
        )

    if "BL-4 ERROR: MANIFEST INVALID" not in invalid_output:
        details = f"\nQEMU stderr:\n{invalid_stderr}" if invalid_stderr else ""
        raise SystemExit(
            "BIOS did not reject the corrupted manifest. "
            f"Debug output was:\n{invalid_output or '<empty>'}{details}"
        )
    if "BL-4: MANIFEST VALID" in invalid_output:
        raise SystemExit("Corrupted manifest was incorrectly accepted.")
    if "BL-2: E820 MEMORY MAP ENTRIES:" in invalid_output:
        raise SystemExit(
            "Boot continued to E820 discovery after the manifest was rejected."
        )

    print(
        "BIOS boot smoke test passed: valid manifest accepted, "
        f"{count} E820 entries reported, corrupted manifest rejected."
    )
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Raw BIOS disk image to boot")
    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="Seconds allowed for each bounded emulator run (default: 4)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    run_bios_smoke_test(args.image, timeout_seconds=args.timeout)


if __name__ == "__main__":
    main()
