"""Must match firmware/body_controller/include/ble_protocol.h"""

from __future__ import annotations

import struct

NAME_PREFIX = "BodyCtrl"
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c09c331914"
INPUT_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

PACKET_STRUCT = struct.Struct("<BBHI")  # seq, flags, reserved, millis_ts


def parse_input_packet(data: bytes | bytearray) -> tuple[int, int]:
    if len(data) < 2:
        return 0, 0
    if len(data) >= 8:
        seq, flags, _reserved, _ms = PACKET_STRUCT.unpack_from(data, 0)
        return seq, flags
    return data[0], data[1]
