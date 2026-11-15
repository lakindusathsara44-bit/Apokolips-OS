from pathlib import Path
import tempfile
import unittest

from tools.build_bl1_image import MANIFEST_MAGIC, SECTOR_SIZE, STAGE2_SIZE, build


class BL1ImageTests(unittest.TestCase):
    def test_builds_expected_sector_layout(self):
        boot = bytearray(SECTOR_SIZE)
        boot[510:512] = bytes((0x55, 0xAA))
        stage2 = b"APOKOLIPS-STAGE2"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            boot_file, stage2_file, output = root / "stage1.bin", root / "stage2.bin", root / "image.img"
            boot_file.write_bytes(boot)
            stage2_file.write_bytes(stage2)
            build(boot_file, stage2_file, output)
            image = output.read_bytes()
        self.assertEqual(len(image), 34 * SECTOR_SIZE)
        self.assertEqual(image[:SECTOR_SIZE], bytes(boot))
        self.assertEqual(image[SECTOR_SIZE:SECTOR_SIZE + len(stage2)], stage2)
        self.assertEqual(image[SECTOR_SIZE + STAGE2_SIZE:SECTOR_SIZE + STAGE2_SIZE + 8], MANIFEST_MAGIC)

    def test_rejects_bad_boot_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            boot_file, stage2_file, output = root / "boot", root / "stage2", root / "out"
            boot_file.write_bytes(bytes(SECTOR_SIZE))
            stage2_file.write_bytes(b"stage2")
            with self.assertRaises(SystemExit):
                build(boot_file, stage2_file, output)

    def test_rejects_stage2_overflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            boot = bytearray(SECTOR_SIZE)
            boot[510:512] = bytes((0x55, 0xAA))
            boot_file, stage2_file, output = root / "boot", root / "stage2", root / "out"
            boot_file.write_bytes(boot)
            stage2_file.write_bytes(b"X" * (STAGE2_SIZE + 1))
            with self.assertRaises(SystemExit):
                build(boot_file, stage2_file, output)


if __name__ == "__main__":
    unittest.main()
