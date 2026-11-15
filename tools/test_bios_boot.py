#!/usr/bin/env python3
"""Run a BIOS boot smoke test and verify that Stage 2 receives an E820 map."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


E820_COUNT_PATTERN = re.compile(
    r"BL-2: E820 MEMORY MAP ENTRIES: ([0-9A-F]{2})"
)


def parse_e820_entry_count(output: str) -> int | None:
    """Return the hexadecimal E820 entry count, or None if no success line exists."""
    match = E820_COUNT_PATTERN.search(output)
    if match is None:
        return None
    return int(match.group(1), 16)


def run_bios_smoke_test(image_path: Path, timeout_seconds: float = 4.0) -> int:
    qemu = shutil.which("qemu-system-x86_64")
    if qemu is None:
        raise SystemExit("QEMU was not found. Install qemu-system-x86 first.")
    if not image_path.is_file():
        raise SystemExit(f"Boot image does not exist: {image_path}")

    image_path = image_path.resolve()
    with tempfile.TemporaryDirectory(prefix="apokolips-qemu-") as temp_dir:
        temp = Path(temp_dir)
        debug_log = temp / "qemu-debugcon.log"
        stderr_log = temp / "qemu-stderr.log"

        command = [
            qemu,
            "-machine", "pc",
            "-m", "64M",
            "-drive", f"file={image_path},format=raw,if=ide",
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

        output = debug_log.read_text(encoding="ascii", errors="replace") if debug_log.exists() else ""
        emulator_errors = stderr_log.read_text(encoding="utf-8", errors="replace").strip()

    if "BL-2 ERROR:" in output:
        raise SystemExit(f"BIOS reported an E820 failure:\n{output}")
    count = parse_e820_entry_count(output)
    if count is None:
        details = f"\nQEMU stderr:\n{emulator_errors}" if emulator_errors else ""
        raise SystemExit(
            "QEMU did not report a successful Stage 2 E820 result. "
            f"Debug output was:\n{output or '<empty>'}{details}"
        )
    if count < 1:
        raise SystemExit("BIOS returned zero E820 entries; refusing to pass the smoke test.")

    print(f"BIOS boot smoke test passed: Stage 2 received {count} E820 entries.")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Raw BIOS disk image to boot")
    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="Seconds to allow the guest to reach the Stage 2 halt (default: 4)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    run_bios_smoke_test(args.image, timeout_seconds=args.timeout)


if __name__ == "__main__":
    main()
