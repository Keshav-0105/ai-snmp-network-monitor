#!/usr/bin/env python3
"""Start the local SNMP agent for this project.

Run:
    python3 tests/start_agent.py

Keep this terminal open, then run your Go app in another terminal.
"""

from pathlib import Path
import socket


HOST = "127.0.0.1"
PORT = 1161
COMMUNITY = b"public"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNMPREC = PROJECT_ROOT / "data" / "public.snmprec"


def main():
    values = load_values()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))

    print("SNMP agent started")
    print(f"Address: {HOST}:{PORT}")
    print(f"Data file: {SNMPREC}")
    print("Now open another terminal and run:")
    print("  go run .")
    print("Press Ctrl+C here to stop the SNMP agent.")

    try:
        while True:
            packet, address = sock.recvfrom(65535)
            response = build_response(packet, values)
            sock.sendto(response, address)
            print(f"Answered SNMP request from {address[0]}:{address[1]}")
    except KeyboardInterrupt:
        print("\nSNMP agent stopped")


def load_values():
    values = {}
    for line in SNMPREC.read_text().splitlines():
        if not line.strip():
            continue
        oid, value_type, value = line.split("|", 2)
        values[oid] = (int(value_type), value)
    return values


def build_response(packet, values):
    message, _ = read_tlv(packet, 0)
    version, offset = read_tlv(message.value, 0)
    community, offset = read_tlv(message.value, offset)
    request, _ = read_tlv(message.value, offset)

    if int_from_bytes(version.value) != 1:
        raise ValueError("Only SNMP v2c is supported")
    if community.value != COMMUNITY:
        raise ValueError("Community must be public")

    request_id, pdu_offset = read_tlv(request.value, 0)
    _, pdu_offset = read_tlv(request.value, pdu_offset)
    _, pdu_offset = read_tlv(request.value, pdu_offset)
    varbind_list, _ = read_tlv(request.value, pdu_offset)

    response_varbinds = []
    offset = 0
    while offset < len(varbind_list.value):
        varbind, offset = read_tlv(varbind_list.value, offset)
        oid_tlv, _ = read_tlv(varbind.value, 0)
        oid = decode_oid(oid_tlv.value)
        response_varbinds.append(encode_varbind(oid, values.get(oid)))

    pdu = tlv(
        0xA2,
        encode_integer(int_from_bytes(request_id.value))
        + encode_integer(0)
        + encode_integer(0)
        + tlv(0x30, b"".join(response_varbinds)),
    )
    return tlv(0x30, encode_integer(1) + tlv(0x04, COMMUNITY) + pdu)


def encode_varbind(oid, typed_value):
    if typed_value is None:
        value_tlv = tlv(0x05, b"")
    else:
        value_type, value = typed_value
        if value_type == 4:
            value_tlv = tlv(0x04, value.encode())
        elif value_type in {65, 66, 67, 70}:
            value_tlv = tlv(value_type, encode_unsigned(int(value)))
        else:
            value_tlv = encode_integer(int(value))
    return tlv(0x30, encode_oid(oid) + value_tlv)


def read_tlv(data, offset):
    tag = data[offset]
    offset += 1
    length_byte = data[offset]
    offset += 1
    if length_byte & 0x80:
        length_size = length_byte & 0x7F
        length = int.from_bytes(data[offset:offset + length_size], "big")
        offset += length_size
    else:
        length = length_byte
    value = data[offset:offset + length]
    return TLV(tag, value), offset + length


class TLV:
    def __init__(self, tag, value):
        self.tag = tag
        self.value = value


def tlv(tag, value):
    return bytes([tag]) + encode_length(len(value)) + value


def encode_length(length):
    if length < 128:
        return bytes([length])
    length_bytes = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(length_bytes)]) + length_bytes


def encode_integer(value):
    return tlv(0x02, encode_signed(value))


def encode_signed(value):
    if value == 0:
        return b"\x00"
    size = max(1, (value.bit_length() + 8) // 8)
    encoded = value.to_bytes(size, "big", signed=True)
    while len(encoded) > 1 and encoded[0] == 0 and encoded[1] < 0x80:
        encoded = encoded[1:]
    return encoded


def encode_unsigned(value):
    if value == 0:
        return b"\x00"
    encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
    if encoded[0] >= 0x80:
        encoded = b"\x00" + encoded
    return encoded


def int_from_bytes(data):
    return int.from_bytes(data, "big", signed=bool(data and data[0] & 0x80))


def decode_oid(data):
    numbers = [data[0] // 40, data[0] % 40]
    value = 0
    for byte in data[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            numbers.append(value)
            value = 0
    return ".".join(str(number) for number in numbers)


def encode_oid(oid):
    numbers = [int(part) for part in oid.split(".")]
    encoded = bytes([numbers[0] * 40 + numbers[1]])
    for number in numbers[2:]:
        encoded += encode_base128(number)
    return tlv(0x06, encoded)


def encode_base128(number):
    if number == 0:
        return b"\x00"
    parts = []
    while number:
        parts.insert(0, number & 0x7F)
        number >>= 7
    for index in range(len(parts) - 1):
        parts[index] |= 0x80
    return bytes(parts)


if __name__ == "__main__":
    main()
