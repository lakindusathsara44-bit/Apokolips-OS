# Apokolips OS — BIOS Bootloader (BL-1)

BL-1 is the first executable milestone of the original Apokolips OS boot chain.

1. **Stage 1** is one 512-byte BIOS boot sector. It saves the BIOS boot drive,
   checks for Enhanced Disk Drive (EDD) support, reads 32 sectors from LBA 1
   into physical address 0x8000, then transfers control to Stage 2.
2. **Stage 2** prints a diagnostic message and halts. It proves only the
   Stage 1 → Stage 2 hand-off; it is not a kernel.

## Raw image layout

| LBA | Purpose | Size |
|---:|---|---:|
| 0 | Stage 1 boot sector | 512 bytes |
| 1–32 | Stage 2 reserved region | 16 KiB |
| 33 | Reserved manifest sector | 512 bytes |
| 34+ | Future kernel payload | Not included |

The manifest is reserved metadata; Stage 1 does not parse it in BL-1.

## Build

Requirements: NASM and Python 3 (standard library only).

    mkdir -p build
    nasm -f bin bootloader/bios/stage1/boot.asm -o build/stage1.bin
    nasm -f bin bootloader/bios/stage2/stage2.asm -o build/stage2.bin
    python3 tools/build_bl1_image.py
    python3 -m unittest discover -s tests -v

The image is build/apokolips-bl1.img. GitHub Actions builds it in a hosted
runner and uploads it as an artifact for 14 days.

## Expected VirtualBox display

    APOKOLIPS OS
    BL-1: STAGE 2 LOADED SUCCESSFULLY
    Bootloader milestone only - kernel not loaded.

This expected display is conditional on successful BIOS boot and EDD disk I/O.
If EDD is unavailable or the read fails, Stage 1 displays an error and halts.

## Safety and limits

- The image builder writes only the requested output file; it never accesses
  host physical disks.
- Test only in a disposable VM with a virtual disk image.
- BL-1 contains no partition table, installer, filesystem, kernel, or drivers.
- Hosted build/static tests do not prove runtime boot. VirtualBox boot
  verification remains pending.
