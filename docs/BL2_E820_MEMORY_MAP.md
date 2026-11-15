# Apokolips OS — BL-2 BIOS Memory-Map Discovery

**Status:** Hosted assembly/static tests passed; QEMU/SeaBIOS runtime smoke test passed (7 entries); Oracle VirtualBox runtime verification pending  
**Target:** x86 BIOS real mode, x86_64 system development  
**Parent milestone:** BL-1 Stage 1 → Stage 2 hand-off

## 1. Goal

BL-2 extends the diagnostic Stage 2 with bounded BIOS E820 memory-map discovery. It does not enter protected mode or long mode and does not load a kernel. The goal is to obtain a firmware-provided physical memory map safely enough to define the next bootloader milestone.

## 2. E820 interface

Stage 2 calls BIOS INT 15h with:
- EAX = E820h
- EDX = ASCII 'SMAP' (0x534D4150)
- ECX = 24 bytes requested
- ES:DI = destination record
- EBX = continuation token (zero before the first call)

Every returned record must have EAX = 'SMAP' and ECX >= 20. The implementation requests 24-byte records and preinitializes the extended attributes field to 1. Carry set, a bad signature, or a short record is treated as failure. A map is accepted only after at least one valid entry and a zero continuation token.

## 3. Buffer and bounds

- Physical buffer base: 0x5000.
- Maximum records: 32.
- Requested record size: 24 bytes.
- Maximum buffer consumption: 768 bytes (0x300).
- The buffer is below the boot sector at 0x7C00 and separate from Stage 2 at 0x8000.
- If the BIOS still supplies a non-zero continuation token after 32 records, BL-2 rejects the truncated map rather than silently using incomplete data.

This is a deliberately conservative initial cap. A later milestone may raise it only after the buffer placement and boot memory ownership map are revised and tested.

## 4. Diagnostics

On success, Stage 2 prints the number of E820 records received as two hexadecimal digits. On failure or truncation, it prints a clear error and halts. It never claims that the memory map has been validated by the kernel; Stage 2 only validates the BIOS response shape and bounds.

## 5. Safety and limitations

- This code runs in 16-bit real mode and depends on BIOS INT 15h E820 support.
- E820 records are not yet normalized, sorted, merged, or used for allocation.
- The kernel is not loaded; there is no protected-mode or long-mode transition.
- The BIOS-provided map remains untrusted input and must be validated again by the future kernel.
- The 32-entry cap may reject machines whose firmware reports more entries.
- GitHub Actions run #30 assembled the image, passed all 12 Python tests, and booted the diagnostic image under QEMU/SeaBIOS.
- QEMU/SeaBIOS reported 7 E820 entries. This verifies the implemented path in that emulated BIOS environment only.
- Oracle VirtualBox runtime testing remains pending and must be recorded separately.

## 6. Acceptance criteria

1. Stage 1 source and disk layout remain unchanged from BL-1.
2. Stage 2 assembles as a flat binary and fits in the reserved 16 KiB region.
3. E820 calls check carry, SMAP signature, minimum record size, and continuation termination.
4. The implementation never writes beyond 32 x 24 bytes.
5. A truncated map is rejected.
6. Hosted static tests pass.
7. Hosted assembly/static tests and the QEMU/SeaBIOS smoke test pass; Oracle VirtualBox runtime testing remains a separate outstanding acceptance item.
