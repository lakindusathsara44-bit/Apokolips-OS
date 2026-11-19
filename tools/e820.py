#!/usr/bin/env python3
"""Host-side reference model for safe BIOS E820 map normalization."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import struct

UINT64_MAX = (1 << 64) - 1
MAX_RAW_E820_ENTRIES = 32
MAX_NORMALIZED_E820_ENTRIES = (2 * MAX_RAW_E820_ENTRIES) - 1

E820_TYPE_USABLE = 1
E820_TYPE_RESERVED = 2
E820_TYPE_ACPI_RECLAIMABLE = 3
E820_TYPE_ACPI_NVS = 4
E820_TYPE_BAD = 5
_KNOWN_TYPES = {
    E820_TYPE_USABLE,
    E820_TYPE_RESERVED,
    E820_TYPE_ACPI_RECLAIMABLE,
    E820_TYPE_ACPI_NVS,
    E820_TYPE_BAD,
}


class E820MapError(ValueError):
    """Raised when firmware memory-map data cannot be normalized safely."""


@dataclass(frozen=True)
class E820Entry:
    """One normalized, half-open physical-address range."""

    base: int
    length: int
    type: int
    attributes: int = 1

    @property
    def end(self) -> int:
        """Exclusive end address; construction guarantees no 64-bit wrap."""
        return self.base + self.length


def parse_e820_record(raw: bytes) -> E820Entry:
    """Parse one 20-byte or ACPI 3.x 24-byte BIOS E820 record.

    A 20-byte record has no extended attributes field and is treated as
    enabled. For a 24-byte record, bit 0 is the enabled flag and bit 1 is
    the non-volatile-memory flag. Unknown memory types are conservatively
    mapped to the generic reserved type.
    """
    if len(raw) not in (20, 24):
        raise E820MapError("E820 record must be exactly 20 or 24 bytes.")

    base, length, entry_type = struct.unpack_from("<QQI", raw, 0)
    attributes = struct.unpack_from("<I", raw, 20)[0] if len(raw) == 24 else 1

    if base + length > UINT64_MAX:
        raise E820MapError(
            "E820 address range overflows the 64-bit end-address field."
        )

    if (attributes & 0x1) == 0 or length == 0:
        return E820Entry(base, length, 0, attributes)

    normalized_type = (
        entry_type if entry_type in _KNOWN_TYPES else E820_TYPE_RESERVED
    )
    return E820Entry(base, length, normalized_type, attributes & 0x3)


def _most_restrictive_type(types: set[int]) -> int:
    """Choose a conservative type when firmware ranges overlap."""
    priority = {
        E820_TYPE_USABLE: 0,
        E820_TYPE_ACPI_RECLAIMABLE: 1,
        E820_TYPE_ACPI_NVS: 2,
        E820_TYPE_RESERVED: 3,
        E820_TYPE_BAD: 4,
    }
    return max(types, key=lambda entry_type: priority[entry_type])


def normalize_e820_map(records: Iterable[bytes]) -> list[E820Entry]:
    """Validate, sort, split, and merge a bounded BIOS E820 memory map.

    Disabled and zero-length records are ignored. Overlapping ranges are
    split at every boundary; each output segment receives the most
    restrictive type covering that segment. The result is sorted and
    non-overlapping, with gaps preserved.
    """
    raw_records = list(records)
    if len(raw_records) > MAX_RAW_E820_ENTRIES:
        raise E820MapError(
            f"E820 map exceeds the {MAX_RAW_E820_ENTRIES}-entry input limit."
        )

    entries: list[E820Entry] = []
    for raw in raw_records:
        entry = parse_e820_record(raw)
        if entry.length and entry.type:
            entries.append(entry)

    if not entries:
        raise E820MapError("E820 map contains no enabled, non-empty records.")

    boundaries = sorted(
        {address for entry in entries for address in (entry.base, entry.end)}
    )
    normalized: list[E820Entry] = []

    for start, end in zip(boundaries, boundaries[1:]):
        covering = [
            entry
            for entry in entries
            if entry.base <= start and entry.end >= end
        ]
        if not covering:
            continue

        entry_type = _most_restrictive_type(
            {entry.type for entry in covering}
        )
        nonvolatile = all(entry.attributes & 0x2 for entry in covering)
        attributes = 0x1 | (0x2 if nonvolatile else 0x0)
        segment_length = end - start

        if (
            normalized
            and normalized[-1].end == start
            and normalized[-1].type == entry_type
            and normalized[-1].attributes == attributes
        ):
            previous = normalized[-1]
            normalized[-1] = E820Entry(
                previous.base,
                previous.length + segment_length,
                entry_type,
                attributes,
            )
        else:
            normalized.append(
                E820Entry(start, segment_length, entry_type, attributes)
            )

    if not normalized:
        raise E820MapError("E820 map produced no normalized ranges.")
    if len(normalized) > MAX_NORMALIZED_E820_ENTRIES:
        raise E820MapError(
            "Normalized E820 map exceeds its documented output limit."
        )

    return normalized
