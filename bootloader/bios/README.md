# Apokolips OS — BIOS Bootloader

## BL-1

BL-1 provides an original 512-byte BIOS Stage 1 that loads the fixed 16 KiB Stage 2 region using EDD INT 13h extensions.

## BL-2 — E820 memory-map discovery

BL-2 extends Stage 2 to query the BIOS E820 memory map in 16-bit real mode. It requests 24-byte records, stores at most 32 entries at physical address 0x5000, validates the SMAP signature and minimum returned size, and rejects failed or truncated responses. On success it displays the number of entries.

The memory map is not yet normalized or used by a physical memory allocator. BL-2 does not load a kernel or enter protected/long mode.

## Raw image layout

| LBA | Purpose | Size |
|---:|---|---:|
| 0 | Stage 1 | 512 bytes |
| 1–32 | Stage 2 reserved region | 16 KiB |
| 33 | Reserved manifest sector | 512 bytes |
| 34+ | Future kernel payload | Not included |

## Build

Requirements: NASM and Python 3 standard library.

    mkdir -p build
    nasm -f bin bootloader/bios/stage1/boot.asm -o build/stage1.bin
    nasm -f bin bootloader/bios/stage2/stage2.asm -o build/stage2.bin
    python3 tools/build_bl1_image.py
    python3 -m unittest discover -s tests -v

The raw image builder enforces the 512-byte Stage 1 signature and 16 KiB Stage 2 limit. Hosted builds do not prove VirtualBox runtime boot.
