from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.build_bl1_image import (
    MANIFEST_CRC_OFFSET,
    MANIFEST_FORMAT,
    MANIFEST_HEADER_SIZE,
    MANIFEST_LBA,
    MANIFEST_MAGIC,
    MANIFEST_VERSION,
    PAYLOAD_START_LBA,
    SECTOR_SIZE,
    STAGE2_SECTORS,
    STAGE2_SIZE,
    build,
    build_manifest,
    validate_manifest,
)


def recalculate_crc(manifest: bytearray) -> None:
    manifest[MANIFEST_CRC_OFFSET:MANIFEST_CRC_OFFSET + 4] = b"\0\0\0\0"
    checksum = zlib.crc32(manifest) & 0xFFFFFFFF
    struct.pack_into("<I", manifest, MANIFEST_CRC_OFFSET, checksum)


class BL4ManifestTests(unittest.TestCase):
    def test_generated_manifest_has_expected_versioned_fields(self):
        manifest = build_manifest()
        self.assertEqual(len(manifest), SECTOR_SIZE)
        fields = struct.unpack_from(MANIFEST_FORMAT, manifest, 0)
        self.assertEqual(fields[0], MANIFEST_MAGIC)
        self.assertEqual(fields[1], MANIFEST_VERSION)
        self.assertEqual(fields[2], MANIFEST_HEADER_SIZE)
        self.assertEqual(fields[3], STAGE2_SECTORS)
        self.assertEqual(fields[4], 0)
        self.assertEqual(fields[5], PAYLOAD_START_LBA)
        self.assertEqual(fields[6], 0)
        self.assertEqual(fields[7], 0)
        validate_manifest(manifest)

    def test_rejects_manifest_checksum_corruption(self):
        manifest = bytearray(build_manifest())
        manifest[100] ^= 0x01
        with self.assertRaisesRegex(ValueError, "CRC32 mismatch"):
            validate_manifest(bytes(manifest))

    def test_rejects_unsupported_version_even_with_valid_crc(self):
        manifest = bytearray(build_manifest())
        struct.pack_into("<H", manifest, 8, MANIFEST_VERSION + 1)
        recalculate_crc(manifest)
        with self.assertRaisesRegex(ValueError, "Unsupported manifest version"):
            validate_manifest(bytes(manifest))

    def test_rejects_payload_overlap_even_with_valid_crc(self):
        manifest = bytearray(build_manifest())
        struct.pack_into("<I", manifest, 16, MANIFEST_LBA)
        struct.pack_into("<I", manifest, 20, 1)
        recalculate_crc(manifest)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            validate_manifest(bytes(manifest))

    def test_rejects_payload_lba_overflow_even_with_valid_crc(self):
        manifest = bytearray(build_manifest())
        struct.pack_into("<I", manifest, 16, 0xFFFFFFF0)
        struct.pack_into("<I", manifest, 20, 0x40)
        recalculate_crc(manifest)
        with self.assertRaisesRegex(ValueError, "overflows"):
            validate_manifest(bytes(manifest))

    def test_rejects_nonzero_reserved_bytes_even_with_valid_crc(self):
        manifest = bytearray(build_manifest())
        manifest[MANIFEST_HEADER_SIZE] = 0xA5
        recalculate_crc(manifest)
        with self.assertRaisesRegex(ValueError, "reserved"):
            validate_manifest(bytes(manifest))

    def test_image_contains_manifest_at_reserved_sector(self):
        boot = bytearray(SECTOR_SIZE)
        boot[510:512] = bytes((0x55, 0xAA))
        stage2 = b"APOKOLIPS-STAGE2"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            boot_file = root / "stage1.bin"
            stage2_file = root / "stage2.bin"
            output_file = root / "image.img"
            boot_file.write_bytes(boot)
            stage2_file.write_bytes(stage2)
            build(boot_file, stage2_file, output_file)
            image = output_file.read_bytes()

        self.assertEqual(len(image), (MANIFEST_LBA + 1) * SECTOR_SIZE)
        self.assertEqual(image[:SECTOR_SIZE], bytes(boot))
        self.assertEqual(image[SECTOR_SIZE:SECTOR_SIZE + len(stage2)], stage2)
        manifest_start = MANIFEST_LBA * SECTOR_SIZE
        manifest = image[manifest_start:manifest_start + SECTOR_SIZE]
        validate_manifest(manifest)

    def test_rejects_stage2_overflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            boot = bytearray(SECTOR_SIZE)
            boot[510:512] = bytes((0x55, 0xAA))
            boot_file = root / "boot"
            stage2_file = root / "stage2"
            output_file = root / "out"
            boot_file.write_bytes(boot)
            stage2_file.write_bytes(b"X" * (STAGE2_SIZE + 1))
            with self.assertRaises(SystemExit):
                build(boot_file, stage2_file, output_file)


if __name__ == "__main__":
    unittest.main()
