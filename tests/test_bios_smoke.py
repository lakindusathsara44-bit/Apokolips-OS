import unittest

from tools.test_bios_boot import parse_e820_entry_count


class BIOSQEMUSmokeLogTests(unittest.TestCase):
    def test_parses_hexadecimal_e820_entry_count(self):
        self.assertEqual(
            parse_e820_entry_count(
                "APOKOLIPS OS\r\nBL-2: E820 MEMORY MAP ENTRIES: 0A\r\n"
            ),
            10,
        )

    def test_returns_none_when_stage2_success_line_is_missing(self):
        self.assertIsNone(parse_e820_entry_count("APOKOLIPS OS\r\n"))

    def test_does_not_accept_malformed_or_partial_count(self):
        self.assertIsNone(
            parse_e820_entry_count("BL-2: E820 MEMORY MAP ENTRIES: G1")
        )
        self.assertIsNone(
            parse_e820_entry_count("BL-2: E820 MEMORY MAP ENTRIES: 0")
        )


if __name__ == "__main__":
    unittest.main()
