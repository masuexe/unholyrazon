#!/usr/bin/env python3
"""Compare the actual ACS ammo-scaling helper with a Python integer oracle."""
import ctypes
import itertools
from pathlib import Path
import random
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/acs_source/v6b_overrides/corescripts/systems/weapon_ammo_capacity_math.acs'
MAX = 2147483647


def main():
    source = SOURCE.read_text().replace('function int ', 'int ')
    boundary = [0, 1, 2, 3, 17, 28, 32767, 32768, 65535, 65536,
                98304, 131072, 1000000007, 1500000000, MAX - 1, MAX]
    cases = list(itertools.product(boundary, boundary, boundary))
    rng = random.Random(0x6C)
    cases.extend((rng.randrange(MAX + 1), rng.randrange(1, MAX + 1),
                  rng.randrange(MAX + 1)) for _ in range(50000))
    with tempfile.TemporaryDirectory(prefix='uh-ammo-math-') as scratch:
        path = Path(scratch)
        (path / 'math.c').write_text(source)
        subprocess.run(['cc', '-std=c99', '-shared', '-fPIC', '-O2', '-Wall',
                        '-Wextra', '-Werror', '-fsanitize=undefined',
                        '-fno-sanitize-recover=undefined', str(path / 'math.c'),
                        '-o', str(path / 'math.so')], check=True)
        lib = ctypes.CDLL(str(path / 'math.so'))
        scale = lib.updateFactor
        scale.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        scale.restype = ctypes.c_int
        for value, old, factor in cases:
            expected = (0 if value <= 0 or factor <= 0 else value if old <= 0
                        else min(MAX, (2 * value * factor + old) // (2 * old)))
            actual = scale(value, old, factor)
            if actual != expected:
                raise AssertionError((value, old, factor, actual, expected))
    print(f'Ammo scaling: {len(cases)} boundary/random cases pass with UBSan')


if __name__ == '__main__':
    main()
