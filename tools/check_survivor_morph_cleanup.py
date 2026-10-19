#!/usr/bin/env python3
"""Run the real survivor cleanup ACS under C inventory/stacker stubs.

ACC checks the language separately. These cases exercise interrupted attacks,
external layers, forced flight's coupled counters and repeated cleanup/end calls.
They do not simulate engine collision, weapon prediction or multiplayer packets.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    reset = (ROOT / "src/acs_source/systems/tools/morph_reset.acs").read_text()
    source = (ROOT / "src/acs_source/systems/tools/survivor_morph_cleanup.acs").read_text()
    tables = "\n".join(re.findall(
        r'(?:str|int) uh_morphpropstack(?:name|script|off|extra)\[.*?\] = \{.*?\};',
        reset, re.S))
    assert tables.count(" = {") == 4
    source = re.sub(r'script "(\w+)"', r'void \1', source).replace("function ", "")
    assert reset.count("UH_ClearSurvivorMorphState();") == 3
    # The two deliberately retained behaviors must not acquire cleanup receipts.
    for name in ("negaman_copyweps/NegaSuperArm.dec", "megaman_copyweps/mm2/timestopper.dec"):
        text = (ROOT / "src/actors/classes/survivors" / name).read_text()
        assert "uh_SurvivorProperty" not in text
        assert "uh_SurvivorAirLock" not in text
    assert '"PlayerPropertyCantUseItems"' not in source
    assert 'TakeInventory("IsPerformingSuplex"' not in source
    # Every emitted family selector has an actual receipt actor and a table row.
    # Ignore comment string literals by reading just the initializer.
    markers = re.findall(r'"([^"]*)"', source.split("= {", 1)[1].split("};", 1)[0])
    assert len(markers) == 27
    actors = (ROOT / "src/actors/unepic/ClassMorph.dec").read_text()
    for path in (ROOT / "src/actors").rglob("*"):
        if not path.is_file() or path.suffix not in (".dec", ".txt"):
            continue
        for family in re.findall(r'"uh_SurvivorProperty", (\d+),', path.read_text()):
            marker = markers[int(family)]
            assert marker and f"actor {marker} :" in actors, (path, family)
    with tempfile.TemporaryDirectory(prefix="uh-survivor-morph-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(STUBS + tables + source + TESTS)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define str const char *
#define StrLen(s) ((int)strlen(s))
#define UH_MORPH_PROPSTACK_COUNT 27
#define USP_TOGGLEON 1
#define USP_TOGGLEOFF_NONE 4
struct Entry { const char *name; int count; } inv[128];
int ni, limit = 100, calls, pn;
bool frozen, stopped;
int *Cell(const char *name) {
  for (int i = 0; i < ni; i++)
    if (!strcmp(inv[i].name, name)) return &inv[i].count;
  assert(ni < 128);
  inv[ni].name = name;
  return &inv[ni++].count;
}
int PlayerNumber(void) { return pn; }
int CheckInventory(const char *name) { return *Cell(name); }
void GiveInventory(const char *name, int amount) { *Cell(name) += amount; }
void TakeInventory(const char *name, int amount) {
  int *cell = Cell(name);
  *cell = *cell > amount ? *cell - amount : 0;
}
int ACS_NamedExecuteWithResult(const char *script, int player, int toggle, int extra);
'''

TESTS = r'''
void Bump(int family, int delta) {
  const char *name = uh_morphpropstackname[family];
  int count = CheckInventory(name);
  *Cell(name) = delta > 0 ? (count < limit ? count + 1 : count) : (count > 0 ? count - 1 : 0);
}
int ACS_NamedExecuteWithResult(const char *script, int player, int toggle, int extra) {
  assert(player == 0);
  calls++;
  int family = -1;
  for (int i = 0; i < 27; i++)
    if (!strcmp(script, uh_morphpropstackscript[i])) { family = i; break; }
  assert(family >= 0);
  bool on = family == 15 ? toggle == 1 : toggle > 0;
  int delta = on ? 1 : -1;
  if (family == 3) {
    if (extra) { Bump(3, delta); Bump(5, delta); }
    Bump(4, delta); Bump(6, delta);
  } else if (family == 5) {
    if (extra) Bump(5, delta);
    Bump(6, delta);
  } else Bump(family, delta);
  frozen = CheckInventory("PlayerPropertyFrozen") > 0;
  stopped = CheckInventory("PlayerPropertyStopped") > 0;
  return 0;
}
void Reset(void) { memset(inv, 0, sizeof(inv)); ni = calls = pn = 0; limit = 100; }
int main(void) {
  // Interrupt every supported movement family, both alone and over an external
  // layer. Cleanup twice and a stale weapon-end must not remove that layer.
  int families[] = {0, 1, 2, 3, 4, 6, 15, 22};
  for (unsigned i = 0; i < sizeof(families)/sizeof(*families); i++) {
    int f = families[i];
    for (int external = 0; external <= 1; external++) {
      Reset();
      if (external) ACS_NamedExecuteWithResult(uh_morphpropstackscript[f], 0, 1, f == 3);
      UH_SetSurvivorProperty(f, 1, f == 3);
      UH_SetSurvivorProperty(f, f == 15 ? 1 : 2, f == 3);
      assert(CheckInventory(uh_survivorstackmarker[f]) == 2);
      UH_ClearSurvivorMorphState();
      assert(CheckInventory(uh_morphpropstackname[f]) == external);
      int oldcalls = calls;
      UH_ClearSurvivorMorphState();
      UH_SetSurvivorProperty(f, f == 15 ? 4 : 0, f == 3);
      assert(calls == oldcalls);
      assert(CheckInventory(uh_morphpropstackname[f]) == external);
      if (f == 3 || f == 4) assert(CheckInventory("PlayerPropertyNoGravity") == external);
      if (f == 0) assert(frozen == (bool)external);
      if (f == 1) assert(stopped == (bool)external);
    }
  }
  // Normal attack end followed by morph is also a no-op for external freezes.
  Reset(); GiveInventory("PlayerPropertyFrozen", 1);
  UH_SetSurvivorProperty(0, 1, 0); UH_SetSurvivorProperty(0, 0, 0);
  UH_ClearSurvivorMorphState(); assert(CheckInventory("PlayerPropertyFrozen") == 1);
  // Coupled forced flight + separate no-gravity must return exactly their own
  // counters, leaving an independently acquired flight layer intact.
  Reset(); ACS_NamedExecuteWithResult("core_flyplayer", 0, 1, 0);
  UH_SetSurvivorProperty(3, 1, 1); UH_SetSurvivorProperty(6, 2, 0);
  UH_ClearSurvivorMorphState();
  assert(CheckInventory("PlayerPropertyFlight") == 1);
  assert(CheckInventory("PlayerPropertyNoGravity") == 1);
  assert(!CheckInventory("PlayerPropertyFlightForced"));
  assert(!CheckInventory("PlayerPropertyNoGravityForced"));
  // Air locks, Miu receipts and the indefinite Lim/Decoy slow are retired;
  // the two deliberately preserved item/carry effects remain intact.
  Reset(); GiveInventory("DisabledAirJumps", 1);
  UH_SetSurvivorAirLock(1); UH_SetSurvivorAirLock(1);
  GiveInventory("PowerLimFiringSlow", 1); GiveInventory("MiuRavagerActive_F", 1);
  GiveInventory("MiuRavagerStopped_F", 1); GiveInventory("Lim_M2Frozen_F", 1);
  GiveInventory("PlayerPropertyCantUseItems", 2); GiveInventory("IsPerformingSuplex", 1);
  UH_ClearSurvivorMorphState(); UH_SetSurvivorAirLock(0);
  assert(CheckInventory("DisabledAirJumps") == 1);
  assert(!CheckInventory("PowerLimFiringSlow") && !CheckInventory("MiuRavagerActive_F"));
  assert(!CheckInventory("MiuRavagerStopped_F") && !CheckInventory("Lim_M2Frozen_F"));
  assert(CheckInventory("PlayerPropertyCantUseItems") == 2 && CheckInventory("IsPerformingSuplex") == 1);
  // Saturation is not ownership. An unsuccessful increment cannot later pop
  // an existing freeze, including on repeated cleanup calls.
  Reset(); limit = 1; GiveInventory("PlayerPropertyFrozen", 1);
  UH_SetSurvivorProperty(0, 1, 0); UH_ClearSurvivorMorphState();
  assert(!CheckInventory("UH_SurvivorFrozen_F") && CheckInventory("PlayerPropertyFrozen") == 1);
  Reset(); pn = -1; UH_SetSurvivorProperty(0, 1, 0); UH_SetSurvivorAirLock(1);
  assert(calls == 0 && !CheckInventory("DisabledAirJumps"));
  puts("Survivor morph cleanup checks passed.");
  return 0;
}
'''

if __name__ == "__main__":
    main()
