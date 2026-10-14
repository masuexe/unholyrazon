#!/usr/bin/env python3
"""Run Eden's actual integer-only client tracker with C engine stubs.

Checks spawn item gains, subsequent changes, pawn/view changes and expiry.
ACC compilation and in-game layout/network checks remain separate.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

STUBS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef const char *str;
#define UH_IMAGE_ID_BASE -19730000
#define APROP_Health 0
int pn, tick, health = 100, ready = 1, start = 101;
int attrs[6] = {10, 12, 30, 35, 40, 25};
int bases[6] = {10, 12, 30, 35, 40, 25};
int clears;
int PlayerNumber(void) {return pn;}
int Timer(void) {return tick;}
int GetActorProperty(int tid, int prop) {
  assert(tid == 0 && prop == APROP_Health); return health;
}
void ClearHudMessageBold(int id) {
  assert(id <= UH_IMAGE_ID_BASE - 170 && id >= UH_IMAGE_ID_BASE - 181);
  clears++;
}
int CheckInventory(str name);
'''

TESTS = r'''
int CheckInventory(str name) {
  if (!strcmp(name, "EdenHudStartTic")) return start;
  if (!strcmp(name, "EdenInitFlag")) return ready;
  for (int i = 0; i < 6; i++) {
    if (!strcmp(name, eden_hud_attr[i])) return attrs[i];
    if (!strcmp(name, eden_hud_base_attr[i])) return bases[i];
  }
  assert(0); return 0;
}
int main(void) {
  // Unready and non-player cameras cannot fabricate attribute gains.
  tick = 100; ready = 0;
  assert(UpdateEdenStatDeltas() == -1);
  ready = 1; pn = -1;
  assert(UpdateEdenStatDeltas() == -1);
  pn = 64; assert(UpdateEdenStatDeltas() == -1); pn = 0;
  // Big Eye at spawn: +30 damage only, never the random base stats.
  attrs[3] = 65;
  assert(UpdateEdenStatDeltas() == 0);
  assert(eden_delta_val[0][3] == 30 && eden_delta_until[0][3] == 170);
  for (int i = 0; i < 6; i++) if (i != 3) assert(!eden_delta_until[0][i]);
  // Repeated calls in the same tic and unchanged ticks do not refresh expiry.
  UpdateEdenStatDeltas(); tick++; UpdateEdenStatDeltas();
  assert(eden_delta_until[0][3] == 170);
  // Tears uses the displayed rate: more tears is a positive difference.
  attrs[2] += 15; attrs[0] -= 3; tick++; UpdateEdenStatDeltas();
  assert(eden_delta_val[0][2] == 15 && eden_delta_val[0][0] == -3);
  // A second change replaces the first rather than showing a stale total.
  attrs[3] = 60; tick++; UpdateEdenStatDeltas();
  assert(eden_delta_val[0][3] == -5 && eden_delta_until[0][3] == 173);
  // Absolute time expires at exactly 70 tics; no draw-count dependence.
  for (; tick < 173; tick++) UpdateEdenStatDeltas();
  assert(tick >= eden_delta_until[0][3]);
  // A different established pawn is silent, and player caches stay separate.
  pn = 1; start = 1; attrs[3] = 99; UpdateEdenStatDeltas();
  assert(!eden_delta_until[1][3] && eden_last_attr[0][3] == 60);
  pn = 0; start = 101; tick++; UpdateEdenStatDeltas();
  assert(!eden_delta_until[0][3] && eden_last_attr[0][3] == 99);
  // A weapon/camera gap rebases instead of inventing an unseen reroll.
  tick += 10; attrs[3] = 40; UpdateEdenStatDeltas();
  assert(!eden_delta_until[0][3] && eden_last_attr[0][3] == 40);
  // Morph/new life gets its own baseline even in the same player slot.
  tick++; start = tick + 1; bases[3] = 50; attrs[3] = 20;
  UpdateEdenStatDeltas(); assert(eden_delta_val[0][3] == -30);
  // Death removes tracking; a same-body revive must not replay spawn gains.
  health = 0; tick++; assert(UpdateEdenStatDeltas() == -1);
  health = 100; tick++; UpdateEdenStatDeltas();
  assert(!eden_delta_until[0][3]);
  // New respawn without passives is silent. Missing init stamp is also gated.
  tick++; start = tick + 1; attrs[3] = bases[3]; UpdateEdenStatDeltas();
  assert(!eden_delta_until[0][3]);
  start = 0; assert(UpdateEdenStatDeltas() == -1);
  ClearEdenStatDeltas(); assert(clears == 12);
  puts("Eden stat delta tracker checks passed");
  return 0;
}
'''


def main():
    source = (ROOT / "src/acs_source/hud/eden_bars.acs").read_text()
    source = source[source.index("#define EDEN_ATTR_COUNT"):
                    source.index("function void DrawEdenStatDeltas")]
    source = source.replace("function ", "")
    with tempfile.TemporaryDirectory(prefix="uh-eden-deltas-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(STUBS + source + TESTS)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


if __name__ == "__main__":
    main()
