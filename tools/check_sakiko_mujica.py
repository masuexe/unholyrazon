#!/usr/bin/env python3
"""Run the actual Mujica disband ACS under C stubs; ACC checks syntax separately.

Checks member selection, protection removal, finisher cancellation and the
Sakiko-only DEATH hook. Does not simulate the engine scheduler/network.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "src/acs_source/unholy/sakiko_mujica.acs").read_text()
    source = source[source.index("function void DisbandMujica"):
                    source.index("function void ClearMujicaState")]
    lifecycle = (ROOT / "src/acs_source/unholy/uh_lifecycle.acs").read_text()
    death = lifecycle.split('script "ub_Death_ChangeIsAlive" DEATH {')[1]
    death = death.split('script "ub_Disconnect_ChangeIsAlive"')[0]
    hook = re.search(r'if \(!StrICmp\(GetActorClass\(0\), "SakikoTogawa"\)\)\s+'
                     r'DisbandMujica\(\);', death)
    assert hook, "Sakiko DEATH hook must disband the group"
    code = STUBS + source.replace("function ", "")
    code += "void DeathHook(void) { " + hook.group() + " }\n" + TESTS
    with tempfile.TemporaryDirectory(prefix="uh-mujica-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(code)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


STUBS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define APROP_Health 0
int hp[64], member[64], protected[64], damagecalls[64], cancels;
const char *actorclass;
const char *GetActorClass(int tid) { assert(tid == 0); return actorclass; }
int StrICmp(const char *a, const char *b) { return strcasecmp(a, b); }
int slot(int tid) { assert(tid >= 1000 && tid < 1064); return tid - 1000; }
int GetActorProperty(int tid, int prop) {
  assert(prop == APROP_Health); return hp[slot(tid)];
}
int CheckActorInventory(int tid, const char *name) {
  assert(!strcmp(name, "IsAMujicaMember")); return member[slot(tid)];
}
void ACS_NamedExecuteWithResult(const char *name, int mode) {
  assert(!strcmp(name, "rz_SoraNoMusicaCancel") && mode == 1); cancels++;
}
void GiveActorInventory(int tid, const char *name, int count) {
  assert(!strcmp(name, "AntiInvincibleBuddha_P") && count == 1);
  protected[slot(tid)] = 0;
}
void Thing_Damage(int tid, int damage, int type) {
  int p = slot(tid);
  assert(cancels > 0 && member[p] && hp[p] > 0 && !protected[p]);
  assert(damage >= 1000000 && type == 5);
  hp[p] = 0; damagecalls[p]++;
}
'''

TESTS = r'''
int main(void) {
  for (int i = 0; i < 64; i++) hp[i] = 100;
  member[0] = 1; hp[0] = 0;  /* dead Sakiko */
  member[1] = member[63] = 1; protected[1] = protected[63] = 1;
  member[2] = 1; hp[2] = 0;  /* already dead recruit */
  protected[3] = 1;          /* unrelated protected player */
  actorclass = "MegaManU";
  DeathHook();               /* recruit death must not disband */
  assert(!cancels && hp[1] == 100 && hp[63] == 100);
  actorclass = "sAKIKOtOGAWA";
  DeathHook();
  assert(cancels == 1 && hp[1] == 0 && hp[63] == 0);
  assert(damagecalls[1] == 1 && damagecalls[63] == 1);
  for (int i = 0; i < 64; i++) {
    if (i != 1 && i != 63) assert(damagecalls[i] == 0);
    if (!member[i]) assert(hp[i] == 100);
  }
  assert(protected[3] == 1);
  DeathHook();               /* no damage to corpses on a repeated call */
  assert(damagecalls[1] == 1 && damagecalls[63] == 1);
  puts("Sakiko Mujica checks passed (selective death, protection, cancellation, hook).");
  return 0;
}
'''

if __name__ == "__main__":
    main()
