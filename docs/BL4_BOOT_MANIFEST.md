# Apokolips OS — BL-4 Boot Manifest Specification

**Status:** Implemented in the BL-4 development branch  
**Format version:** 1  
**Encoding:** Little-endian integers  
**Sector size:** 512 bytes  
**Location:** LBA 33 (the sector immediately after the reserved Stage 2 region)

## 1. Purpose

The manifest is a fixed-size, versioned description of the boot image. Stage 2 reads and validates it before proceeding to E820 discovery. The manifest is not executable code and is not a kernel loader.

The current image contains no kernel payload. The payload fields are reserved for a later, separately tested kernel-loading milestone.

## 2. Disk layout

| LBA | Contents |
|---:|---|
| 0 | 512-byte Stage 1 boot sector |
| 1–32 | 16 KiB reserved Stage 2 region |
| 33 | 512-byte manifest sector |
| 34+ | Future payload area; currently empty |

## 3. Version-1 header

The first 32 bytes are the fixed header. All offsets are from the beginning of the manifest sector.

| Offset | Size | Field | Version-1 value / rule |
|---:|---:|---|---|
| 0 | 8 | Magic | ASCII APOKMAN1 |
| 8 | 2 | Version | 1 |
| 10 | 2 | Header size | 32 |
| 12 | 2 | Stage 2 sectors | 32 |
| 14 | 2 | Flags | 0; other values rejected |
| 16 | 4 | Payload start LBA | At least 34 |
| 20 | 4 | Payload sector count | 0 in BL-4 |
| 24 | 4 | Payload CRC32 | 0 when payload sector count is 0 |
| 28 | 4 | Manifest CRC32 | CRC-32/ISO-HDLC over all 512 bytes with this field treated as zero |
| 32 | 480 | Reserved | All bytes must be zero in version 1 |

The checksum field is excluded by replacing bytes 28–31 with four zero bytes during calculation. The CRC uses the reflected polynomial 0xEDB88320, initial value 0xFFFFFFFF, and final XOR 0xFFFFFFFF. This is the standard CRC-32/ISO-HDLC variant used by Python zlib.crc32.

## 4. Validation rules

The host-side image builder and BIOS Stage 2 apply the same structural rules:

1. The sector length must be exactly 512 bytes.
2. The magic, version, header size, Stage 2 sector count, and flags must match the version-1 values.
3. Payload start LBA must be at least 34; it cannot overlap Stage 1, Stage 2, or the manifest sector.
4. If payload sectors are non-zero, adding the sector count to the start LBA must not overflow the 32-bit LBA field.
5. An empty payload must have a zero payload CRC32.
6. All reserved bytes (32–511) must be zero.
7. The manifest CRC32 must match the entire sector with bytes 28–31 treated as zero.

The current Stage 2 does not know the capacity of the boot device and does not load payload sectors. Actual device-capacity checks, payload reads, and payload CRC verification belong to the later kernel-image-loading milestone. The LBA arithmetic check prevents metadata wraparound; it is not a claim that a future payload fits on every disk.

## 5. Failure behaviour

If the manifest sector cannot be read, Stage 2 displays BL-4 ERROR: MANIFEST READ FAILED and halts.

If any field, reserved byte, range calculation, or checksum is invalid, Stage 2 displays BL-4 ERROR: MANIFEST INVALID and halts. It must not continue to E820 discovery or any future payload-loading operation.

A successful validation prints BL-4: MANIFEST VALID.

## 6. Tests

The Python test suite covers:
- The exact version-1 field values and sector size.
- CRC32 generation and verification.
- Corrupted checksum rejection.
- Unsupported version rejection even when the checksum is recomputed.
- Payload overlap and LBA overflow rejection.
- Non-zero reserved byte rejection.
- Correct placement at LBA 33 in the final raw image.

The QEMU/SeaBIOS smoke test boots a valid image and a second image with a deliberately corrupted manifest byte. It requires the valid image to reach E820 discovery and the corrupted image to halt at the manifest check.

## 7. Scope boundaries

BL-4 does not implement:
- Kernel payload loading.
- Payload checksum verification.
- E820 range normalization or physical allocation.
- A20, GDT, paging, or long-mode transition.
- Kernel hand-off or kernel code.

Those remain separate milestones with separate tests.
