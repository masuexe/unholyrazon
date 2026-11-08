#!/usr/bin/env python3
"""Exercise KVX offset bases, separated slabs, culling and palette precision."""
import struct
import unittest
import zlib
from pathlib import Path
from gen_voidwalker_voxels import encode


class EncodingTest(unittest.TestCase):
    def test_surface_runs_and_offsets(self):
        voxels = {(x, y, z): 192 for x in range(3) for y in range(3) for z in range(3)}
        voxels[1, 1, 5] = 198
        data = encode(voxels, (3, 3, 6), (1.5, 1.5, 6), bytes([252] * 768))
        self.assertEqual(struct.unpack_from('<i', data)[0], len(data) - 772)
        self.assertEqual(struct.unpack_from('<3i', data, 16), (384, 384, 1536))
        xo = struct.unpack_from('<4i', data, 28)
        yo = struct.unpack_from('<12H', data, 44)
        self.assertEqual(xo[0], 40)
        self.assertEqual(28 + xo[-1], len(data) - 768)
        observed = {}
        for x in range(3):
            for y in range(3):
                p, end = (28 + xo[x] + yo[x*4+y+i] for i in (0, 1))
                while p < end:
                    z, count, mask = data[p:p+3]
                    self.assertGreater(count, 0)
                    self.assertTrue(0 < mask < 64)
                    for dz, color in enumerate(data[p+3:p+3+count]):
                        observed[x, y, z+dz] = (color, mask)
                    p += count + 3
                self.assertEqual(p, end)
        self.assertNotIn((1, 1, 1), observed)  # Interior faces are omitted.
        self.assertEqual(observed[0, 0, 0], (192, 1 | 4 | 16))
        self.assertEqual(observed[1, 1, 5], (198, 63))
        self.assertEqual(data[-768:], bytes([63] * 768))


class PaletteContractTest(unittest.TestCase):
    def test_opaque_atlas_preserves_dye_slots(self):
        root = Path(__file__).resolve().parents[1]
        png = (root / 'src/models/voidwalker/palette.png').read_bytes()
        chunks, p = {}, 8
        while p < len(png):
            n = struct.unpack_from('>I', png, p)[0]
            tag = png[p+4:p+8]
            chunks[tag] = chunks.get(tag, b'') + png[p+8:p+8+n]
            p += n + 12
        self.assertEqual(struct.unpack('>IIBBBBB', chunks[b'IHDR']),
                         (16, 16, 8, 3, 0, 0, 0))
        self.assertNotIn(b'tRNS', chunks)  # Black is opaque.
        rows = zlib.decompress(chunks[b'IDAT'])
        pixels = []
        for y in range(16):
            self.assertEqual(rows[y*17], 0)
            pixels.extend(rows[y*17+1:y*17+17])
        self.assertEqual(pixels[12*16], 192)  # Not the transposed index 12.
        self.assertEqual(pixels[12*16+6], 198)  # Not the transposed index 108.
        self.assertEqual(pixels[0], 247)
        self.assertEqual(chunks[b'PLTE'][247*3:248*3], bytes(3))
        modeldef = (root / 'src/MODELDEF.voidwalker').read_text()
        self.assertIn('Skin 0 "models/voidwalker/palette.png"', modeldef)
        for frame in 'ABCDEFGH':
            self.assertIn(f'FrameIndex ASTV {frame} 0 0', modeldef)
            data = (root / f'src/voxels/ASTV{frame}.kvx').read_bytes()
            sx, sy = struct.unpack_from('<2i', data, 4)
            xo = struct.unpack_from(f'<{sx+1}i', data, 28)
            pos, end = 28 + xo[0], len(data) - 768
            colors = set()
            while pos < end:
                count = data[pos+1]
                colors.update(data[pos+3:pos+3+count])
                pos += 3 + count
            self.assertEqual(pos, end)
            self.assertTrue({192, 198, 247}.issubset(colors))
            self.assertNotIn(0, colors)


if __name__ == '__main__':
    unittest.main()
