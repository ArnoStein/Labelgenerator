import os
import tempfile
import unittest

from core import append_serial, build_dm_string, check_duplicate, crc16_ccitt_false, parse_sn, validate_serial


class CoreTests(unittest.TestCase):
    def test_normalize_serial(self):
        self.assertEqual(parse_sn("01020304")["normalized"], "SN:01-02-03-04")
        self.assertEqual(parse_sn("SN:01-02-03-04")["normalized"], "SN:01-02-03-04")
        self.assertEqual(parse_sn("01 02 03 04")["normalized"], "SN:01-02-03-04")
        self.assertIsNone(parse_sn("0102030"))

    def test_crc16_ccitt_false_vector(self):
        self.assertEqual(crc16_ccitt_false(b"123456789"), 0x29B1)

    def test_payload(self):
        serial = parse_sn("SN:01-02-03-04")["bytes"]
        dm_string = build_dm_string(serial)
        self.assertTrue(dm_string.startswith("G01020304-"))
        self.assertEqual(dm_string, f"G01020304-{crc16_ccitt_false(serial):04X}")

    def test_duplicate_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "serials.csv")
            payload_hex = "01020304"
            append_serial(csv_path, "SN:01-02-03-04", payload_hex, "01020304", "")
            self.assertTrue(check_duplicate(csv_path, payload_hex))
            self.assertFalse(check_duplicate(csv_path, "AABBCCDD-0000"))

    def test_validate_with_crc16(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "serials.csv")
            dm_string = build_dm_string(parse_sn("01020304")["bytes"])
            input_text = dm_string
            result = validate_serial(input_text, csv_path)
            self.assertTrue(result.ok)

    def test_dm_parser_ok_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "serials.csv")
            dm_string = "G01020304-89C3"
            result_ok = validate_serial(dm_string, csv_path)
            self.assertTrue(result_ok.ok)
            result_bad = validate_serial("G01020304-0000", csv_path)
            self.assertFalse(result_bad.ok)
            self.assertIn("CRC falsch", result_bad.message)


if __name__ == "__main__":
    unittest.main()
