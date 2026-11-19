import struct
import unittest

from tools.e820 import (
    E820MapError,
    E820Entry,
    MAX_NORMALIZED_E820_ENTRIES,
    MAX_RAW_E820_ENTRIES,
    UINT64_MAX,
    normalize_e820_map,
    parse_e820_record,
)


def record(base, length, entry_type, attributes=None):
    data = struct.pack("<QQI", base, length, entry_type)
    if attributes is not None:
        data += struct.pack("<I", attributes)
    return data


class BL5E820NormalizationTests(unittest.TestCase):
    def test_twenty_byte_record_is_enabled_by_default(self):
        entry = parse_e820_record(record(0x1000, 0x2000, 1))
        self.assertEqual(entry, E820Entry(0x1000, 0x2000, 1, 1))

    def test_disabled_twenty_four_byte_record_is_ignored(self):
        result = normalize_e820_map([
            record(0x1000, 0x1000, 1, 0),
            record(0x4000, 0x1000, 1, 1),
        ])
        self.assertEqual(result, [E820Entry(0x4000, 0x1000, 1, 1)])

    def test_zero_length_record_is_ignored(self):
        result = normalize_e820_map([
            record(0x1000, 0, 1),
            record(0x3000, 0x1000, 2),
        ])
        self.assertEqual(result, [E820Entry(0x3000, 0x1000, 2, 1)])

    def test_rejects_record_sizes_other_than_twenty_or_twenty_four(self):
        for size in (0, 19, 21, 23, 25):
            with self.subTest(size=size):
                with self.assertRaisesRegex(E820MapError, "exactly 20 or 24"):
                    parse_e820_record(bytes(size))

    def test_rejects_64_bit_end_address_overflow(self):
        with self.assertRaisesRegex(E820MapError, "overflows"):
            parse_e820_record(record(UINT64_MAX - 7, 8, 1))

    def test_sorts_and_merges_adjacent_ranges_of_same_type(self):
        result = normalize_e820_map([
            record(0x3000, 0x1000, 1),
            record(0x1000, 0x2000, 1),
        ])
        self.assertEqual(result, [E820Entry(0x1000, 0x3000, 1, 1)])

    def test_reserved_overlap_splits_usable_range(self):
        result = normalize_e820_map([
            record(0x1000, 0x5000, 1),
            record(0x3000, 0x1000, 2),
        ])
        self.assertEqual(result, [
            E820Entry(0x1000, 0x2000, 1, 1),
            E820Entry(0x3000, 0x1000, 2, 1),
            E820Entry(0x4000, 0x2000, 1, 1),
        ])

    def test_bad_reserved_nvs_and_reclaimable_overlap_precedence(self):
        result = normalize_e820_map([
            record(0x1000, 0x5000, 3),
            record(0x2000, 0x3000, 4),
            record(0x3000, 0x2000, 2),
            record(0x4000, 0x1000, 5),
        ])
        self.assertEqual([entry.type for entry in result], [3, 4, 2, 5, 2, 4, 3])

    def test_unknown_memory_type_becomes_reserved(self):
        result = normalize_e820_map([record(0x1000, 0x1000, 0x99)])
        self.assertEqual(result, [E820Entry(0x1000, 0x1000, 2, 1)])

    def test_nonvolatile_flag_is_kept_only_when_all_covering_records_agree(self):
        result = normalize_e820_map([
            record(0x1000, 0x3000, 1, 3),
            record(0x2000, 0x1000, 1, 1),
        ])
        self.assertEqual(result, [
            E820Entry(0x1000, 0x1000, 1, 3),
            E820Entry(0x2000, 0x1000, 1, 1),
            E820Entry(0x3000, 0x1000, 1, 3),
        ])

    def test_gaps_are_not_filled(self):
        result = normalize_e820_map([
            record(0x1000, 0x1000, 1),
            record(0x4000, 0x1000, 1),
        ])
        self.assertEqual(result, [
            E820Entry(0x1000, 0x1000, 1, 1),
            E820Entry(0x4000, 0x1000, 1, 1),
        ])

    def test_rejects_more_than_thirty_two_raw_records(self):
        records = [
            record(index * 0x1000, 0x1000, 1)
            for index in range(MAX_RAW_E820_ENTRIES + 1)
        ]
        with self.assertRaisesRegex(E820MapError, "input limit"):
            normalize_e820_map(records)

    def test_rejects_map_with_no_enabled_nonempty_entries(self):
        with self.assertRaisesRegex(E820MapError, "no enabled, non-empty"):
            normalize_e820_map([
                record(0x1000, 0, 1),
                record(0x2000, 0x1000, 1, 0),
            ])

    def test_normalized_output_limit_matches_worst_case_boundary_count(self):
        self.assertEqual(MAX_NORMALIZED_E820_ENTRIES, 63)


if __name__ == "__main__":
    unittest.main()
