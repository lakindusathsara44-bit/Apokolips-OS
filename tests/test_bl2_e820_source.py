from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGE2_SOURCE = ROOT / "bootloader" / "bios" / "stage2" / "stage2.asm"


class BL2E820SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = STAGE2_SOURCE.read_text(encoding="utf-8")

    def test_uses_bios_e820_and_checks_smap_signature(self):
        self.assertIn("mov eax, 0xE820", self.source)
        self.assertIn("mov edx, SMAP_SIGNATURE", self.source)
        self.assertIn("cmp eax, SMAP_SIGNATURE", self.source)

    def test_memory_map_buffer_is_bounded(self):
        self.assertIn("%define E820_BUFFER       0x5000", self.source)
        self.assertIn("%define E820_MAX_ENTRIES  32", self.source)
        self.assertRegex(self.source, r"(?m)^%define\\s+E820_ENTRY_SIZE\\s+24$")
        self.assertIn("cmp word [entry_count], E820_MAX_ENTRIES", self.source)

    def test_rejects_failed_or_malformed_e820_responses(self):
        self.assertIn("int 0x15", self.source)
        self.assertIn("jc .failed", self.source)
        self.assertIn("cmp ecx, 20", self.source)
        self.assertIn("stc", self.source)

    def test_preserves_segment_registers_and_destination_pointer(self):
        self.assertIn("push ds", self.source)
        self.assertIn("push es", self.source)
        self.assertIn("push di", self.source)
        self.assertIn("pop di", self.source)
        self.assertIn("pop es", self.source)
        self.assertIn("pop ds", self.source)

    def test_reports_entry_count_and_does_not_claim_kernel_boot(self):
        self.assertIn("BL-2: E820 MEMORY MAP ENTRIES", self.source)
        self.assertIn("BL-2 ERROR: E820 MEMORY MAP UNAVAILABLE/INVALID", self.source)
        self.assertIn("not a kernel", self.source.lower())


if __name__ == "__main__":
    unittest.main()
