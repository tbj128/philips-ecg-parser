"""
Custom LZW decompression class based on the Java version from:
https://github.com/sixlettervariables/sierra-ecg-tools/blob/master/jsierraecg/src/org/sierraecg/codecs/LzwInputStream.java
"""

class Lzw:
    def __init__(self, compressed):
        self.compressed = compressed
        self.previous = []
        self.next_code = 256
        self.strings = {}
        self.current = None
        self.pos = -1
        self.bits = 10
        self.max_code = 1022
        self.bit_count = 0
        self.bit_buffer = 0
        self.pointer = 0

        for code in range(256):
            self.strings[code] = [bytes([code])]

    def read_code_word(self):
        while self.bit_count <= 24:
            if self.pointer >= len(self.compressed):
                return -1
            input = self.compressed[self.pointer]
            if input < 0:
                return input
            self.bit_buffer = self.bit_buffer | (input << (24 - self.bit_count))
            self.bit_count += 8
            self.pointer += 1
        code = (self.bit_buffer >> (32 - self.bits)) & 0x0000FFFF
        self.bit_buffer = ((self.bit_buffer & 0xFFFFFFFF) << self.bits) & 0xFFFFFFFF
        self.bit_count -= self.bits
        return code

    def internal_read(self):
        data = []
        while True:
            code = self.read_code_word()
            if code == -1:
                break
            if code >= (self.max_code + 1):
                break

            if code not in self.strings:
                data = list(self.previous)
                data.append(self.previous[0])
                self.strings[code] = data
            else:
                data = self.strings[code]

            if len(self.previous) > 0 and self.next_code <= self.max_code:
                next_data = list(self.previous)
                next_data.append(data[0])
                self.strings[self.next_code] = next_data
                self.next_code += 1

            self.previous = data
            return data
        return data

    def read(self):
        if self.current is None or self.pos == len(self.current):
            self.current = self.internal_read()
            self.pos = 0
        if len(self.current) > 0:
            retval = self.current[self.pos]
            self.pos += 1
            return int.from_bytes(retval, byteorder='little', signed=True)
        else:
            return None

