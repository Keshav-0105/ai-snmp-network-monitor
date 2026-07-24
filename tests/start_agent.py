#!/usr/bin/env python3
"""Start the local SNMP agent for this project.

Run:
    python3 tests/start_agent.py

Keep this terminal open, then run your Go app in another terminal.
"""

from pathlib import Path
import select
import socket


HOST = "127.0.0.1"
PORTS = [
    2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2169, 2170,
    2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180,
    2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190,
]
USERNAME = b"snmpuser"
ENGINE_ID = b"local-snmp-agent"
ENGINE_BOOTS = 1
ENGINE_TIME = 1
USM_UNKNOWN_ENGINE_IDS = "1.3.6.1.6.3.15.1.1.4.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNMPREC = PROJECT_ROOT / "data" / "public.snmprec"


def main():
    values_by_port = {port: load_values(index) for index, port in enumerate(PORTS)}
    sockets = {}
    for port in PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, port))
        sockets[sock] = port

    print("SNMP agents started")
    print(f"Address: {HOST}")
    print("Ports:")
    for port in PORTS:
        print(f"  {port}")
    print(f"Data file: {SNMPREC}")
    print("Now open another terminal and run:")
    print("  ./start_main.sh")
    print("Press Ctrl+C here to stop the SNMP agents.")

    try:
        while True:
            ready, _, _ = select.select(list(sockets), [], [])
            for sock in ready:
                port = sockets[sock]
                packet, address = sock.recvfrom(65535)
                response = build_response(packet, values_by_port[port])
                sock.sendto(response, address)
                print(f"Answered SNMP request on {HOST}:{port} from {address[0]}:{address[1]}")
    except KeyboardInterrupt:
        print("\nSNMP agents stopped")
    finally:
        for sock in sockets:
            sock.close()


def load_values(offset):
    values = {}
    for line in SNMPREC.read_text().splitlines():
        if not line.strip():
            continue
        oid, value_type, value = line.split("|", 2)
        if value.isdigit():
            value = str(int(value) + offset)
        values[oid] = (int(value_type), value)
    return values


def build_response(packet, values):
    message, _ = read_tlv(packet, 0)
    version, offset = read_tlv(message.value, 0)
    header, offset = read_tlv(message.value, offset)
    security_parameters, offset = read_tlv(message.value, offset)
    scoped_pdu, _ = read_tlv(message.value, offset)

    if int_from_bytes(version.value) != 3:
        raise ValueError("Only SNMP v3 is supported")

    msg_id, header_offset = read_tlv(header.value, 0)
    msg_max_size, header_offset = read_tlv(header.value, header_offset)
    _, header_offset = read_tlv(header.value, header_offset)
    _, _ = read_tlv(header.value, header_offset)

    security = parse_security_parameters(security_parameters.value)
    context_engine_id, scoped_offset = read_tlv(scoped_pdu.value, 0)
    context_name, scoped_offset = read_tlv(scoped_pdu.value, scoped_offset)
    request, _ = read_tlv(scoped_pdu.value, scoped_offset)

    if security["engine_id"] == b"":
        return build_v3_message(
            int_from_bytes(msg_id.value),
            int_from_bytes(msg_max_size.value),
            context_name.value,
            request,
            0xA8,
            [encode_varbind(USM_UNKNOWN_ENGINE_IDS, (2, "1"))],
        )
    if security["username"] != USERNAME:
        raise ValueError("SNMP v3 username must be snmpuser")
    if context_engine_id.value != ENGINE_ID:
        raise ValueError("SNMP v3 context engine ID does not match")

    response_varbinds = []
    offset = 0
    varbind_list = get_varbind_list(request)
    while offset < len(varbind_list.value):
        varbind, offset = read_tlv(varbind_list.value, offset)
        oid_tlv, _ = read_tlv(varbind.value, 0)
        oid = decode_oid(oid_tlv.value)
        response_varbinds.append(encode_varbind(oid, values.get(oid)))

    return build_v3_message(
        int_from_bytes(msg_id.value),
        int_from_bytes(msg_max_size.value),
        context_name.value,
        request,
        0xA2,
        response_varbinds,
    )


def parse_security_parameters(data):
    sequence, _ = read_tlv(data, 0)
    engine_id, offset = read_tlv(sequence.value, 0)
    engine_boots, offset = read_tlv(sequence.value, offset)
    engine_time, offset = read_tlv(sequence.value, offset)
    username, offset = read_tlv(sequence.value, offset)
    _, offset = read_tlv(sequence.value, offset)
    _, _ = read_tlv(sequence.value, offset)
    return {
        "engine_id": engine_id.value,
        "engine_boots": int_from_bytes(engine_boots.value),
        "engine_time": int_from_bytes(engine_time.value),
        "username": username.value,
    }


def get_varbind_list(request):
    request_id, pdu_offset = read_tlv(request.value, 0)
    _, pdu_offset = read_tlv(request.value, pdu_offset)
    _, pdu_offset = read_tlv(request.value, pdu_offset)
    varbind_list, _ = read_tlv(request.value, pdu_offset)
    return varbind_list


def build_v3_message(msg_id, msg_max_size, context_name, request, pdu_type, response_varbinds):
    request_id, _ = read_tlv(request.value, 0)
    pdu = tlv(
        pdu_type,
        encode_integer(int_from_bytes(request_id.value))
        + encode_integer(0)
        + encode_integer(0)
        + tlv(0x30, b"".join(response_varbinds)),
    )
    scoped_pdu = tlv(0x30, tlv(0x04, ENGINE_ID) + tlv(0x04, context_name) + pdu)
    header = tlv(
        0x30,
        encode_integer(msg_id)
        + encode_integer(msg_max_size)
        + tlv(0x04, b"\x00")
        + encode_integer(3),
    )
    security_parameters = tlv(
        0x30,
        tlv(0x04, ENGINE_ID)
        + encode_integer(ENGINE_BOOTS)
        + encode_integer(ENGINE_TIME)
        + tlv(0x04, USERNAME)
        + tlv(0x04, b"")
        + tlv(0x04, b""),
    )
    return tlv(
        0x30,
        encode_integer(3)
        + header
        + tlv(0x04, security_parameters)
        + scoped_pdu,
    )


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
