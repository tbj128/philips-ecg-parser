"""
Utility functions to parse the Philips ECG XML file.

Methods are based on the Java methods found at:
- https://github.com/sixlettervariables/sierra-ecg-tools/blob/master/jsierraecg/src/org/sierraecg/codecs/XliDecompressor.java
- https://github.com/sixlettervariables/sierra-ecg-tools/blob/master/jsierraecg/src/org/sierraecg/DecodedLead.java

"""

import ctypes
import struct
from lzw import Lzw


def read_chunk(input, chunk_offset):
    content = input[chunk_offset:]
    if len(content) < 8:
        return None, None
    header = content[:8]  # treat as little endian
    compressed_data_size = header[:4]
    compressed_data_size = int.from_bytes(compressed_data_size, 'little', signed=True)
    unknown_usage = header[4:6]
    delta_code = header[6:8]
    delta_code = struct.unpack('h' * (len(delta_code) // 2), delta_code)

    content = content[8:]
    compressed_data = content[:compressed_data_size]
    assert len(compressed_data) == compressed_data_size

    compressed_data = [int(str(x)) for x in compressed_data]
    decompressed_data = []
    lzw = Lzw(compressed_data)
    while True:
        next_val = lzw.read()
        if next_val is None:
            break
        decompressed_data.append(next_val)

    if len(decompressed_data) % 2 == 1:
        decompressed_data.append(0)

    unpacked_data = unpack(decompressed_data)
    decoded = decode_deltas(unpacked_data, delta_code[0])

    return chunk_offset + 8 + compressed_data_size, decoded


def reconstitute_leads(leads):
    lead_I = leads[0]
    lead_II = leads[1]
    lead_III = leads[2]
    lead_AVR = leads[3]
    lead_AVL = leads[4]
    lead_AVF = leads[5]

    # Lead III
    for i in range(len(lead_III)):
        lead_III[i] = lead_II[i] - lead_I[i] - lead_III[i]

    # Lead aVR
    for i in range(len(lead_AVR)):
        lead_AVR[i] = -1 * lead_AVR[i] - ((lead_I[i] + lead_II[i]) / 2)

    # Lead aVL
    for i in range(len(lead_AVL)):
        lead_AVL[i] = ((lead_I[i] - lead_III[i]) / 2) - lead_AVL[i]

    # Lead aVF
    for i in range(len(lead_AVF)):
        lead_AVF[i] = ((lead_II[i] + lead_III[i]) / 2) - lead_AVF[i]


def create_from_lead_set(lead_data):
    leads = []
    for lead in lead_data:
        leads.append(lead)
        if len(leads) >= 12:
            break
    reconstitute_leads(leads)
    return leads


def unpack(bytes_arr):
    actual = []
    actual_len = int(len(bytes_arr) / 2)
    for i in range(actual_len):
        hi = (bytes_arr[i] << 8) & 0xFFFF
        lo = bytes_arr[actual_len + i] & 0xFF
        actual.append(ctypes.c_int16(hi | lo).value)
    return actual


def decode_deltas(input, initial_value):
    deltas = input.copy()
    x = deltas[0]
    y = deltas[1]
    last_value = initial_value
    i = 2
    while i < len(deltas):
        z = (y + y) - x - last_value
        last_value = deltas[i] - 64
        deltas[i] = z
        x = y
        y = z
        i += 1
    return deltas
