import os
import tempfile
import unittest

from core import append_serial, build_payload, check_duplicate, crc16_ccitt_false, parse_sn, validate_serial


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
        self.assertEqual(build_payload(serial, True), f"01020304-{crc16_ccitt_false(serial):04X}")
        self.assertEqual(build_payload(serial, False), "01020304")

    def test_duplicate_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "serials.csv")
            payload = build_payload(parse_sn("SN:01-02-03-04")["bytes"], True)
            append_serial(csv_path, "SN:01-02-03-04", payload, "01020304", "")
            self.assertTrue(check_duplicate(csv_path, payload))
            self.assertFalse(check_duplicate(csv_path, "AABBCCDD-0000"))

    def test_validate_with_crc16(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "serials.csv")
            payload = build_payload(parse_sn("01020304")["bytes"], True)
            input_text = payload
            result = validate_serial(input_text, csv_path, True)
            self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
