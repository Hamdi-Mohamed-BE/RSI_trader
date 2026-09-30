"""Dependency-free QR code encoder (byte mode) rendering to inline SVG.

Follows ISO/IEC 18004 as implemented in Project Nayuki's reference QR library
(MIT). Verified against the ``qrcode`` package in ``tests/test_store_qr.py``
module-for-module when that package is available.
"""

from __future__ import annotations

from html import escape

ECL_FORMAT_BITS = {"L": 1, "M": 0, "Q": 3, "H": 2}
ECC_CODEWORDS_PER_BLOCK = {
    "L": (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "M": (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    "Q": (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "H": (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
}
NUM_ERROR_CORRECTION_BLOCKS = {
    "L": (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    "M": (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    "Q": (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    "H": (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
}


def _raw_modules(ver: int) -> int:
    result = (16 * ver + 128) * ver + 64
    if ver >= 2:
        align = ver // 7 + 2
        result -= (25 * align - 10) * align - 55
        if ver >= 7:
            result -= 36
    return result


def _data_codewords(ver: int, ecl: str) -> int:
    return _raw_modules(ver) // 8 - ECC_CODEWORDS_PER_BLOCK[ecl][ver] * NUM_ERROR_CORRECTION_BLOCKS[ecl][ver]


def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _rs_divisor(degree: int) -> list[int]:
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return result


def _rs_remainder(data: list[int], divisor: list[int]) -> list[int]:
    result = [0] * len(divisor)
    for byte in data:
        factor = byte ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= _gf_mul(coef, factor)
    return result


class QrCode:
    def __init__(self, data: bytes, ecl: str = "M", mask: int | None = None, min_version: int = 1):
        self.ecl = ecl
        for ver in range(min_version, 41):
            count_bits = 8 if ver <= 9 else 16
            if 4 + count_bits + 8 * len(data) <= _data_codewords(ver, ecl) * 8:
                break
        else:
            raise ValueError("data too long for a QR code")
        self.version = ver
        self.size = ver * 4 + 17
        bits: list[int] = []

        def append(value: int, length: int) -> None:
            bits.extend((value >> i) & 1 for i in reversed(range(length)))

        append(0b0100, 4)
        append(len(data), count_bits)
        for byte in data:
            append(byte, 8)
        capacity = _data_codewords(ver, ecl) * 8
        append(0, min(4, capacity - len(bits)))
        append(0, -len(bits) % 8)
        pad = 0xEC
        while len(bits) < capacity:
            append(pad, 8)
            pad ^= 0xEC ^ 0x11
        codewords = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.function = [[False] * self.size for _ in range(self.size)]
        self._draw_function_patterns()
        self._draw_codewords(self._add_ecc_and_interleave(codewords))
        if mask is None:
            best, best_penalty = 0, None
            for candidate in range(8):
                self._apply_mask(candidate)
                self._draw_format_bits(candidate)
                penalty = self._penalty()
                if best_penalty is None or penalty < best_penalty:
                    best, best_penalty = candidate, penalty
                self._apply_mask(candidate)
            mask = best
        self.mask = mask
        self._apply_mask(mask)
        self._draw_format_bits(mask)

    # -- construction ---------------------------------------------------
    def _set(self, x: int, y: int, dark: bool) -> None:
        self.modules[y][x] = dark
        self.function[y][x] = True

    def _draw_function_patterns(self) -> None:
        for i in range(self.size):
            self._set(6, i, i % 2 == 0)
            self._set(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (self.size - 4, 3), (3, self.size - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < self.size and 0 <= y < self.size:
                        self._set(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        positions = self._alignment_positions()
        last = len(positions) - 1
        for i, px in enumerate(positions):
            for j, py in enumerate(positions):
                if (i == 0 and j == 0) or (i == 0 and j == last) or (i == last and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._set(px + dx, py + dy, max(abs(dx), abs(dy)) != 1)
        self._draw_format_bits(0)
        if self.version >= 7:
            rem = self.version
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            value = self.version << 12 | rem
            for i in range(18):
                bit = bool((value >> i) & 1)
                a, b = self.size - 11 + i % 3, i // 3
                self._set(a, b, bit)
                self._set(b, a, bit)

    def _alignment_positions(self) -> list[int]:
        if self.version == 1:
            return []
        count = self.version // 7 + 2
        step = (self.version * 8 + count * 3 + 5) // (count * 4 - 4) * 2
        result = [self.size - 7 - i * step for i in range(count - 1)] + [6]
        return list(reversed(result))

    def _draw_format_bits(self, mask: int) -> None:
        data = ECL_FORMAT_BITS[self.ecl] << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412

        def bit(i: int) -> bool:
            return bool((bits >> i) & 1)

        for i in range(6):
            self._set(8, i, bit(i))
        self._set(8, 7, bit(6))
        self._set(8, 8, bit(7))
        self._set(7, 8, bit(8))
        for i in range(9, 15):
            self._set(14 - i, 8, bit(i))
        for i in range(8):
            self._set(self.size - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self._set(8, self.size - 15 + i, bit(i))
        self._set(8, self.size - 8, True)

    def _add_ecc_and_interleave(self, data: list[int]) -> list[int]:
        blocks_count = NUM_ERROR_CORRECTION_BLOCKS[self.ecl][self.version]
        ecc_len = ECC_CODEWORDS_PER_BLOCK[self.ecl][self.version]
        raw = _raw_modules(self.version) // 8
        short_blocks = blocks_count - raw % blocks_count
        short_len = raw // blocks_count
        divisor = _rs_divisor(ecc_len)
        blocks: list[list[int]] = []
        k = 0
        for i in range(blocks_count):
            length = short_len - ecc_len + (0 if i < short_blocks else 1)
            chunk = data[k:k + length]
            k += length
            ecc = _rs_remainder(chunk, divisor)
            if i < short_blocks:
                chunk.append(0)
            blocks.append(chunk + ecc)
        result: list[int] = []
        for i in range(len(blocks[0])):
            for j, block in enumerate(blocks):
                if i != short_len - ecc_len or j >= short_blocks:
                    result.append(block[i])
        return result

    def _draw_codewords(self, data: list[int]) -> None:
        i = 0
        right = self.size - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(self.size):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = self.size - 1 - vert if upward else vert
                    if not self.function[y][x] and i < len(data) * 8:
                        self.modules[y][x] = bool((data[i >> 3] >> (7 - (i & 7))) & 1)
                        i += 1
            right -= 2

    def _apply_mask(self, mask: int) -> None:
        tests = (
            lambda x, y: (x + y) % 2 == 0,
            lambda x, y: y % 2 == 0,
            lambda x, y: x % 3 == 0,
            lambda x, y: (x + y) % 3 == 0,
            lambda x, y: (x // 3 + y // 2) % 2 == 0,
            lambda x, y: x * y % 2 + x * y % 3 == 0,
            lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
            lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
        )
        test = tests[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.function[y][x] and test(x, y):
                    self.modules[y][x] = not self.modules[y][x]

    def _penalty(self) -> int:
        size, m = self.size, self.modules
        score = 0
        lines = [m[y] for y in range(size)] + [[m[y][x] for y in range(size)] for x in range(size)]
        pattern_a = [True, False, True, True, True, False, True, False, False, False, False]
        pattern_b = pattern_a[::-1]
        for line in lines:
            run, color = 0, None
            for value in line:
                if value == color:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + run - 5
                    color, run = value, 1
            if run >= 5:
                score += 3 + run - 5
            for start in range(size - 10):
                window = line[start:start + 11]
                if window == pattern_a or window == pattern_b:
                    score += 40
        for y in range(size - 1):
            for x in range(size - 1):
                if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        dark = sum(sum(row) for row in m)
        total = size * size
        score += 10 * (abs(dark * 20 - total * 10) // total)
        return score

    # -- output -----------------------------------------------------------
    def svg(self, *, border: int = 4, dark: str = "#07100f", light: str = "#ffffff", title: str = "") -> str:
        dim = self.size + border * 2
        parts = [f"M{x + border},{y + border}h1v1h-1z" for y in range(self.size) for x in range(self.size)
                 if self.modules[y][x]]
        label = f"<title>{escape(title)}</title>" if title else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" shape-rendering="crispEdges" '
                f'role="img" aria-label="{escape(title or "QR code")}">{label}<rect width="100%" height="100%" '
                f'fill="{light}"/><path d="{"".join(parts)}" fill="{dark}"/></svg>')


def qr_svg(text: str, *, title: str = "", ecl: str = "M") -> str:
    return QrCode(text.encode("utf-8"), ecl).svg(title=title)
