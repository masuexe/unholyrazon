#!/usr/bin/env python3
"""Rebuild Void Walker's phase-two KVX frames and GL palette skin from v6c art.

Requires Pillow. Usage: python gen_voidwalker_voxels.py /path/mm8bdm-v6c.pk3
KVX faces +X; VOXELDEF cancels Zandronum's implicit quarter turn. Palette
indices are matched exactly for player translations (VOXELDEF OverridePalette).
"""
import argparse
import io
import math
from pathlib import Path
import re
import struct
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def encode(voxels, size, pivot, palette):
    """Encode visible surface runs, with per-run exposed-face masks."""
    sx, sy, sz = size
    slab = bytearray()
    xoffsets, yoffsets = [], []
    table_size = (sx + 1) * 4 + sx * (sy + 1) * 2
    directions = [(-1, 0, 0), (1, 0, 0), (0, -1, 0),
                  (0, 1, 0), (0, 0, -1), (0, 0, 1)]
    for x in range(sx):
        start = len(slab)
        xoffsets.append(start + table_size)
        for y in range(sy):
            yoffsets.append(len(slab) - start)
            run, top, last_mask = [], 0, 0
            for z in range(sz + 1):
                color = voxels.get((x, y, z))
                mask = sum(1 << i for i, (dx, dy, dz) in enumerate(directions)
                           if (x + dx, y + dy, z + dz) not in voxels) if color is not None else 0
                if run and (not mask or mask != last_mask or len(run) == 255):
                    slab.extend((top, len(run), last_mask))
                    slab.extend(run)
                    run = []
                if mask:
                    if not run:
                        top, last_mask = z, mask
                    run.append(color)
            assert not run
        yoffsets.append(len(slab) - start)
        assert len(slab) - start < 65536
    xoffsets.append(len(slab) + table_size)
    header = struct.pack('<6i', *size, *(round(p * 256) for p in pivot))
    data = header + struct.pack(f'<{len(xoffsets)}i', *xoffsets)
    data += struct.pack(f'<{len(yoffsets)}H', *yoffsets) + slab
    return struct.pack('<i', len(data)) + data + bytes(c >> 2 for c in palette)


def main():
    from PIL import Image
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    args = parser.parse_args()
    with ZipFile(args.base) as archive:
        names = {n.lower(): n for n in archive.namelist()}
        palette = archive.read(names['playpal.pal'])[:768]
        definitions = archive.read(names['textures.skininfo']).decode()
        rows = re.findall(r'^Sprite ASTM[^\r\n]+', definitions, re.M)
        offsets = {}
        for row in rows:
            name, ox, oz = re.search(r'Sprite (\w+).*?Offset (-?\d+), (-?\d+)', row).groups()
            offsets[name] = (int(ox), int(oz))
        def art(frame, rotation):
            name = f'sprites/skins/mm8/astroman/$ast{frame}{rotation}.png'.lower()
            im = Image.open(io.BytesIO(archive.read(names[name])))
            assert im.mode == 'P', 'Keep source palette indices, never quantize RGB'
            # Source PNGs have compact local palettes: their index 3 is cyan,
            # not game index 3. Match exact RGB, preferring the dye source slots.
            rgb = [tuple(palette[i:i+3]) for i in range(0, 768, 3)]
            preferred = [0, 4, 192, 198, 208] + list(range(256))
            local = im.getpalette()
            transparent = im.info.get('transparency')
            mapping = {}
            pixels = list(im.tobytes())
            for index in set(pixels):
                if index == transparent:
                    mapping[index] = 247
                else:
                    color = tuple(local[index*3:index*3+3])
                    mapping[index] = next(i for i in preferred if rgb[i] == color)
            mapped = Image.new('P', im.size)
            mapped.putpalette(palette)
            mapped.putdata([mapping[i] for i in pixels])
            mapped.info['transparency'] = 247
            return mapped
        for frame in 'ABCDEFGH':
            front, back = art(frame, '1'), art(frame, '5')
            side = art(frame, '7'+frame+'3')
            ox, height = offsets['ASTM'+frame+'1']
            bx, bh = offsets['ASTM'+frame+'5']
            # A fixed horizontal origin prevents animation jitter; Z is downwards.
            size = (32, 64, height)
            voxels = {}
            for z in range(height):
                spans = []
                for u in range(front.width):
                    if front.getpixel((u, z)) != front.info.get('transparency', 247):
                        if not spans or spans[-1][-1] != u-1:
                            spans.append([])
                        spans[-1].append(u)
                side_z = z - height + offsets['ASTM'+frame+'7'+frame+'3'][1]
                side_width = 12
                if 0 <= side_z < side.height:
                    pixels = [u for u in range(side.width) if side.getpixel((u, side_z)) != side.info.get('transparency', 247)]
                    if pixels:
                        side_width = max(pixels) - min(pixels) + 1
                for span in spans:
                    center = (span[0] + span[-1]) / 2
                    radius = len(span) / 2
                    depth = min(13, side_width / 2, max(2, radius * .85))
                    colors = [front.getpixel((u, z)) for u in span]
                    body_colors = [c for c in colors if c in (192, 198)]
                    side_color = max(set(body_colors), key=body_colors.count) if body_colors else 0
                    for u in span:
                        half = max(1, round(depth * math.sqrt(max(0, 1-((u-center)/(radius+.3))**2))))
                        y = u - ox + 32
                        for x in range(16-half, 16+half):
                            color = side_color
                            if x == 16+half-1:
                                color = front.getpixel((u, z))
                            elif x == 16-half:
                                bu, bz = u - ox + bx, z - height + bh
                                if 0 <= bu < back.width and 0 <= bz < back.height:
                                    bc = back.getpixel((bu, bz))
                                    if bc != back.info.get('transparency', 247):
                                        color = bc
                            # Index 0 becomes transparent in translated GL textures.
                            voxels[x, y, z] = 247 if color == 0 else color
            out = ROOT / f'src/voxels/ASTV{frame}.kvx'
            out.write_bytes(encode(voxels, size, (16, 32, height), palette))
            print(f'{out.name}: {len(voxels)} solid voxels, {out.stat().st_size} bytes')
        # The built-in FVoxelTexture's translated GetPixels path transposes its
        # atlas. An ordinary indexed PNG supplies the correct column-major pixels
        # and explicit opaque black, without changing the actor's translation.
        atlas = Image.new('P', (16, 16))
        atlas.putpalette(palette)
        atlas.putdata([247 if i == 0 else i for i in range(256)])
        target = ROOT / 'src/models/voidwalker/palette.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(target)
        modeldef = '// Generated by tools/gen_voidwalker_voxels.py.\n'
        modeldef += '// Explicit PNG skin bypasses Zandronum voxel translation atlas bugs.\n'
        modeldef += 'Model VoidWalker {\n  Scale 1 1 1\n  AngleOffset 0\n  Skin 0 "models/voidwalker/palette.png"\n'
        for frame in 'ABCDEFGH':
            modeldef += f'  Model 0 "voxels/ASTV{frame}.kvx"\n  FrameIndex ASTV {frame} 0 0\n'
        modeldef += '}\n'
        (ROOT / 'src/MODELDEF.voidwalker').write_text(modeldef)
        # Real sprites supply correct bounds and a fallback with voxels disabled.
        fallback = '// Generated by tools/gen_voidwalker_voxels.py; v6c Astro Man fallback.\n'
        fallback += '\n'.join(row.replace('ASTM', 'ASTV') for row in rows) + '\n'
        (ROOT / 'src/TEXTURES.voidwalker').write_text(fallback)


if __name__ == '__main__':
    main()
