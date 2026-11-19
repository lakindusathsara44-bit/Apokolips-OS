# Apokolips OS — BIOS Bootloader

## BL-1 — Original BIOS boot stages

BL-1 provides an original 512-byte BIOS Stage 1 that loads the fixed 16 KiB Stage 2 region using EDD INT 13h extensions. The raw image builder validates the boot-sector size/signature and keeps Stage 2 inside its reserved region.

## BL-2 — E820 memory-map discovery

BL-2 extends Stage 2 to query the BIOS E820 memory map in 16-bit real mode. It requests 24-byte records, stores at most 32 entries at physical address 0x5000, validates the SMAP signature and minimum returned size, and rejects failed or truncated responses. On success it displays the number of entries.

The memory map is not yet normalized or used by a physical memory allocator. BL-2 does not load a kernel or enter protected/long mode.

## BL-3 — QEMU BIOS runtime smoke test

GitHub Actions builds a separate diagnostic image and boots it under QEMU/SeaBIOS. The test checks that Stage 2 runs and receives a non-zero E820 entry count. The passing baseline reported 7 entries.

QEMU debug-console output is opt-in and compiled only into the smoke-test Stage 2. The normal image continues to use BIOS text output without port-0xE9 diagnostic writes. QEMU testing does not replace Oracle VirtualBox runtime validation.

## BL-4 — Versioned boot manifest

Stage 2 reads the reserved manifest sector at LBA 33 into physical address 0x6000. It validates the APOKMAN1 magic, version 1, fixed header size, Stage 2 layout, flags, payload range arithmetic, reserved bytes, and CRC32 checksum before continuing to E820 discovery.

The image builder creates the manifest deterministically. The hosted tests validate the generated structure and reject malformed metadata. The QEMU smoke test now checks both:
- A valid manifest is accepted and the E820 path runs.
- A corrupted manifest is rejected before the E820 path runs.

The manifest currently describes an empty payload. BL-4 does not load a kernel, verify a payload checksum, enter protected/long mode, or transfer control to a kernel.

## Raw image layout

| LBA | Purpose | Size |
|---:|---|---:|
| 0 | Stage 1 | 512 bytes |
| 1–32 | Stage 2 reserved region | 16 KiB |
| 33 | Versioned boot manifest | 512 bytes |
| 34+ | Future kernel payload | Not included |

## Build

Requirements: NASM, Python 3 standard library, and QEMU (qemu-system-x86) for the BIOS runtime smoke test.

    mkdir -p build
    nasm -f bin bootloader/bios/stage1/boot.asm -o build/stage1.bin
    nasm -f bin bootloader/bios/stage2/stage2.asm -o build/stage2.bin
    python3 tools/build_bl1_image.py
    python3 -m unittest discover -s tests -v

For the hosted runtime test, assemble Stage 2 with the QEMU diagnostic define, build a separate smoke-test image, and run tools/test_bios_boot.py. GitHub Actions performs these steps automatically.

The raw image builder enforces the 512-byte Stage 1 signature and 16 KiB Stage 2 limit. Neither CI nor QEMU testing proves compatibility with every BIOS, VirtualBox configuration, or physical computer.
