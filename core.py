import csv
import datetime as dt
import os
import re


class ValidationResult:
    def __init__(self, ok, message, normalized=None, payload=None, u32_hex=None):
        self.ok = ok
        self.message = message
        self.normalized = normalized
        self.payload = payload
        self.u32_hex = u32_hex


def _strip_to_hex(raw):
    return re.sub(r"[^0-9A-Fa-f]", "", raw or "").upper()


def parse_sn(raw):
    cleaned = _strip_to_hex(raw)
    crc_hex = None
    if len(cleaned) == 12:
        crc_hex = cleaned[8:12]
        cleaned = cleaned[:8]
    if len(cleaned) != 8:
        return None
    pairs = [cleaned[i : i + 2] for i in range(0, 8, 2)]
    normalized = f"SN:{pairs[0]}-{pairs[1]}-{pairs[2]}-{pairs[3]}"
    serial_bytes = bytes(int(part, 16) for part in pairs)
    data_hex = "".join(f"{b:02X}" for b in serial_bytes)
    return {
        "normalized": normalized,
        "bytes": serial_bytes,
        "data_hex": data_hex,
        "u32_hex": data_hex,
        "crc_hex": crc_hex,
    }


def sn_from_bytes(value_bytes):
    if value_bytes is None or len(value_bytes) != 4:
        return None
    data_hex = "".join(f"{b:02X}" for b in value_bytes)
    pairs = [data_hex[i : i + 2] for i in range(0, 8, 2)]
    return f"SN:{pairs[0]}-{pairs[1]}-{pairs[2]}-{pairs[3]}"


def crc16_ccitt_false(data, poly=0x1021, init=0xFFFF):
    crc = init & 0xFFFF
    for byte in data:
        crc ^= (byte << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def build_payload(serial_bytes, with_crc):
    if serial_bytes is None or len(serial_bytes) != 4:
        return None
    data_hex = "".join(f"{b:02X}" for b in serial_bytes)
    if not with_crc:
        return data_hex
    crc = crc16_ccitt_false(serial_bytes)
    return f"{data_hex}-{crc:04X}"


def _u32_from_payload(payload_hex):
    if not payload_hex:
        return None
    base = payload_hex.split("-")[0]
    if len(base) != 8:
        return None
    try:
        return int(base, 16)
    except ValueError:
        return None


def check_duplicate(csv_path, payload_hex):
    if not payload_hex or not os.path.exists(csv_path):
        return False
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("payload_hex") == payload_hex:
                return True
    return False


def load_serial_sets(csv_path):
    payloads = set()
    u32_set = set()
    if not os.path.exists(csv_path):
        return payloads, u32_set
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            payload_hex = row.get("payload_hex") or row.get("payload") or ""
            payload_hex = payload_hex.strip().upper()
            if payload_hex:
                payloads.add(payload_hex)
            u32_hex = row.get("u32_hex", "").strip().upper()
            if u32_hex:
                try:
                    u32_set.add(int(u32_hex, 16))
                except ValueError:
                    pass
            else:
                u32 = _u32_from_payload(payload_hex)
                if u32 is not None:
                    u32_set.add(u32)
    return payloads, u32_set


def next_sn_max_plus_one(u32_set):
    max_u32 = max(u32_set) if u32_set else -1
    candidate = max_u32 + 1
    if candidate > 0xFFFFFFFF:
        raise ValueError("Ueberlauf: keine freie SN mehr.")
    return sn_from_bytes(candidate.to_bytes(4, "big"))


def next_sn_smallest_free(u32_set, start=0):
    expected = start
    for value in sorted(u32_set):
        if value < start:
            continue
        if value == expected:
            expected += 1
            continue
        if value > expected:
            break
    if expected > 0xFFFFFFFF:
        raise ValueError("Ueberlauf: keine freie SN mehr.")
    return sn_from_bytes(expected.to_bytes(4, "big"))


def append_serial(csv_path, normalized_serial, payload_hex, u32_hex, note):
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "sn_text", "payload_hex", "u32_hex", "note"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "sn_text": normalized_serial,
                "payload_hex": payload_hex,
                "u32_hex": u32_hex,
                "note": note or "",
            }
        )


def validate_serial(raw, csv_path, with_crc):
    parsed = parse_sn(raw)
    if not parsed:
        return ValidationResult(False, "Ungueltiges Format (8 Hex-Zeichen erwartet).")
    if parsed.get("crc_hex"):
        crc_calc = crc16_ccitt_false(parsed["bytes"])
        if f"{crc_calc:04X}" != parsed["crc_hex"].upper():
            return ValidationResult(
                False,
                "CRC-16 stimmt nicht.",
                parsed["normalized"],
            )
    payload = build_payload(parsed["bytes"], with_crc)
    if not payload:
        return ValidationResult(False, "Payload konnte nicht erzeugt werden.", parsed["normalized"])
    if check_duplicate(csv_path, payload):
        return ValidationResult(
            False,
            "Duplikat: Payload existiert bereits.",
            parsed["normalized"],
            payload,
            parsed["u32_hex"],
        )
    return ValidationResult(True, "OK", parsed["normalized"], payload, parsed["u32_hex"])
