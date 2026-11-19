# Apokolips OS — BL-5 E820 Map Validation and Normalization

**Status:** Host-side reference model and tests added; BIOS Stage 2 integration pending  
**Parent milestone:** BL-2 BIOS E820 discovery  
**Input buffer:** 32 records maximum at physical address 0x5000  
**Raw record size:** 20 or 24 bytes  
**Normalized output bound:** 63 records maximum

## 1. Goal

BL-5 defines the rules for converting the raw BIOS E820 records collected by Stage 2 into a sorted, non-overlapping physical memory map. The normalized map is a prerequisite for a future physical page-frame allocator.

The BIOS map is untrusted firmware input. A record must never be treated as allocatable merely because the firmware returned it.

This document defines the algorithm and its host-side reference implementation. It does **not** claim that the current 16-bit Stage 2 assembly performs normalization yet.

## 2. Raw E820 record format

The BIOS E820 interface can return either:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 8 | Base physical address |
| 8 | 8 | Region length |
| 16 | 4 | Memory type |
| 20 | 4 | Extended attributes (24-byte form only) |

All fields are little-endian.

- A 20-byte record has no extended attributes field and is treated as enabled.
- For a 24-byte record, attribute bit 0 means enabled. A record with bit 0 clear is ignored.
- Attribute bit 1 indicates non-volatile memory. Other attribute bits are not propagated.
- A zero-length record is ignored.
- Any other record size is rejected.
- A range whose exclusive end cannot be represented in the 64-bit end-address field is rejected.
- The input count may not exceed the existing 32-record Stage 2 limit.

## 3. Memory types

| Type | Meaning | Allocation policy |
|---:|---|---|
| 1 | Usable RAM | Candidate for future allocation |
| 2 | Reserved | Never allocate |
| 3 | ACPI reclaimable | Keep unavailable until a later ACPI-aware stage |
| 4 | ACPI NVS | Never allocate |
| 5 | Bad memory | Never allocate |
| Other | Unknown firmware type | Convert to generic reserved type 2 |

Only type 1 is considered usable. The future kernel must still exclude its own image, boot metadata, page tables, firmware data, and other reserved ranges before allocating pages.

## 4. Overlap policy

The normalized map uses half-open intervals: [base, end). It is sorted by base address, contains no zero-length entries, and has no overlapping output ranges. Gaps remain gaps.

The algorithm collects every input start/end boundary and partitions the address space into segments. For each segment, it selects the most restrictive type among all records covering that segment:

1. Type 5 — bad memory
2. Type 2 — reserved
3. Type 4 — ACPI NVS
4. Type 3 — ACPI reclaimable
5. Type 1 — usable

Therefore, an overlapping reserved or special-purpose range can never be accidentally exposed as usable RAM. Unknown types are converted to type 2 before overlap resolution.

Adjacent output segments are merged only when both type and normalized attributes match. The enabled attribute is set on every emitted entry. The non-volatile attribute is retained only when every input record covering that segment marks it non-volatile.

With at most 32 input intervals, there are at most 64 distinct boundaries and 63 non-empty boundary segments. The normalized output limit is therefore 63 records.

## 5. Reference implementation

The file tools/e820.py provides a host-side reference implementation:

- parse_e820_record() validates and parses one 20-byte or 24-byte record.
- normalize_e820_map() validates the input count, ignores disabled/empty records, resolves overlaps conservatively, sorts ranges, and merges adjacent compatible ranges.
- E820MapError reports malformed or unsafe input.

The reference implementation is intended to make the rules testable before they are translated into real-mode assembly. It is not linked into the boot image.

## 6. Tests

The file tests/test_bl5_e820.py covers:

- 20-byte and 24-byte record handling.
- Disabled and zero-length records.
- Invalid record sizes and 64-bit range overflow.
- Sorting and merging adjacent ranges.
- Reserved-over-usable overlap handling.
- Precedence among bad, reserved, NVS, and reclaimable ranges.
- Unknown type handling.
- Non-volatile attribute handling.
- Preservation of gaps.
- The 32-entry input limit and empty-map rejection.
- The 63-entry normalized-output bound.

## 7. Completion gate

BL-5 is **not complete** until all of the following are implemented and verified:

1. Translate this exact normalization policy into BIOS Stage 2 assembly.
2. Keep raw and normalized buffers within explicitly reserved, non-overlapping memory ranges.
3. Reject malformed records and truncated E820 maps without continuing.
4. Add QEMU/SeaBIOS positive and negative runtime tests for normalization.
5. Verify the boot path in Oracle VirtualBox separately.
6. Document the normalized buffer address, record count, and record format for the future kernel.

No physical memory allocator or kernel memory initialization may rely on the map until this gate passes.
