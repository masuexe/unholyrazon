#!/usr/bin/env python3
"""Run the actual LMS teamdamage ACS handler against controlled C engine stubs."""
from pathlib import Path
import ctypes
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TeamDamageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="uh-teamdamage-")
        directory = Path(cls.scratch.name)
        handler = (ROOT / "src/acs_source/unholy/uh_teamdamage.acs").read_text()
        handler = handler.replace('#include "uh_teamff_defs.acs"',
            (ROOT / 'src/acs_source/_includes/mod_api/uh_teamff_defs.acs').read_text())
        handler, count = re.subn(
            r'script "uh_LogicalTeamDamage" \(int evt, int dmg, int dmgtype\) EVENT',
            "void handler(int evt, int dmg, int dmgtype)", handler,
        )
        assert count == 1
        handler = re.sub(r"\bterminate\s*;", "return;", handler)
        source = r'''
#include <stdint.h>
#include <string.h>
#define GAMEEVENT_ACTOR_DAMAGED_PREMOD 12
#define AAPTR_DAMAGE_TARGET 1
#define AAPTR_DAMAGE_SOURCE 2
#define AAPTR_DAMAGE_INFLICTOR 4
static int lms, scale, victim, shooter, friends, result, pointer;
static int origin;
int GetCVar(const char *name) { return !strcmp(name, "lastmanstanding") ? lms : scale; }
int GetEventResult(void) { return result; }
int SetActivator(int tid, int ptr) { pointer = ptr; return 1; }
int PlayerNumber(void) { return pointer == AAPTR_DAMAGE_TARGET ? victim : shooter; }
int ACS_NamedExecuteWithResult(const char *name, ...) { return !strcmp(name, "uh_DailyFFStamp") ? 0 : friends; }
int CheckInventory(const char *name) { return origin; }
int PlayerInGame(int pn) { return pn>=0 && pn<64; }
int max(int a, int b) { return a > b ? a : b; }
int FixedMul(int a, int b) { return (int)(((int64_t)a * b) >> 16); }
void SetResultValue(int value) { result = value; }
'''
        source += handler
        source += r'''
int probe(int mode, int multiplier, int src, int dst, int ally, int current, int event) {
    lms = mode; scale = multiplier; shooter = src; victim = dst;
    friends = ally; result = current; pointer = 0;
    handler(event, 100, 0); /* Raw damage deliberately differs from current. */
    return result;
}
int probe_origin(int metadata, int multiplier, int ally) {
    origin=metadata;
    int value=probe(1,multiplier,-1,1,ally,80,12);
    origin=0;
    return value;
}
'''
        (directory / "probe.c").write_text(source)
        subprocess.run(["cc", "-shared", "-fPIC", "-std=c99", str(directory / "probe.c"),
                        "-o", str(directory / "probe.so")], check=True)
        cls.library = ctypes.CDLL(str(directory / "probe.so"))
        cls.probe = cls.library.probe
        cls.probe.argtypes = [ctypes.c_int] * 7
        cls.probe.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_multiplier_and_truncation(self):
        for multiplier, damage, expected in [(0, 80, 0), (.5, 80, 40), (1, 80, 80),
                                             (2, 80, 160), (.5, 3, 1), (-1, 80, 0)]:
            with self.subTest(multiplier=multiplier, damage=damage):
                self.assertEqual(self.probe(1, int(multiplier * 65536), 0, 1, 1, damage, 12), expected)

    def test_cancelled_hits_stay_cancelled(self):
        self.assertEqual(self.probe(1, 2 * 65536, 0, 1, 1, 0, 12), 0)

    def test_recorded_summon_creator(self):
        probe = self.library.probe_origin
        probe.argtypes = [ctypes.c_int] * 3
        probe.restype = ctypes.c_int
        # Creator slot 0, standard class 1, weapon index 0.
        metadata = 262144 + 2048 + 1
        self.assertEqual(probe(metadata, 32768, 1), 40)
        self.assertEqual(probe(metadata, 0, 1), 0)
        self.assertEqual(probe(metadata, 32768, 0), 80)
        self.assertEqual(probe(0, 32768, 1), 80)

    def test_unrelated_hits_are_unchanged(self):
        # Native TLMS/co-op already applied teamdamage; do not multiply again.
        cases = [(0, 0, 1, 1, 40, 12), (1, 0, 1, 0, 80, 12),
                 (1, 1, 1, 1, 80, 12), (1, -1, 1, 1, 80, 12),
                 (1, 0, -1, 1, 80, 12), (1, 0, 1, 1, 80, 11),
                 (1, 0, 1, 1, 1000000, 12)]
        for mode, src, dst, ally, damage, event in cases:
            with self.subTest(case=(mode, src, dst, ally, damage, event)):
                self.assertEqual(self.probe(mode, 32768, src, dst, ally, damage, event), damage)


if __name__ == "__main__":
    unittest.main()
