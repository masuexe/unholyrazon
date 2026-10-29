#!/usr/bin/env python3
"""Exercise the actual UH weapon/team translation function under C stubs.

ACC checks language syntax; the v6c runtime palette probe covers real palette
registration. This check isolates the player-team-color server option and UH
weapon/mugshot bookkeeping without requiring a rendered sprite comparison.
"""
from pathlib import Path
import subprocess
import tempfile
from check_team_visibility import function

ROOT = Path(__file__).resolve().parents[1]
STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define CLR_ICEDEATH 10000
#define CLR_PREVCOLOR -1
#define TCLR_NONE 0
#define TCLR_DEFAULT 500
int IsTeamGame, tick, startupteam, team, enabled;
int notrans, noweapon, charge, body, mug, ready;
int Timer(void) { return tick; }
int PlayerTeam(void) { return team; }
int GetCVar(const char *name) { assert(!strcmp(name,"mm8bdm_sv_playerteamcolor")); return enabled; }
int CheckInventory(const char *name) {
  if (!strcmp(name,"NoTeamTranslation")) return notrans;
  if (!strcmp(name,"NoWeaponTranslation")) return noweapon;
  assert(!strcmp(name,"UH_ChargeColor_F")); return charge;
}
int ACS_NamedExecuteWithResult(const char *name, int value) {
  if (!strcmp(name,"core_checkmode")) return startupteam;
  assert(!strcmp(name,"uh_SyncMugFromWeaponDye")); mug=value; return 0;
}
void Thing_SetTranslation(int tid, int dye) { assert(tid==0); body=dye; }
void SetInventory(const char *name, int dye) { assert(!strcmp(name,"UH_LastReadyDye")); ready=dye; }
'''
TESTS = r'''
int main(void) {
  int checks=0;
  for (IsTeamGame=0;IsTeamGame<=1;IsTeamGame++)
  for (tick=0;tick<=1;tick++)
  for (startupteam=0;startupteam<=1;startupteam++)
  for (enabled=0;enabled<=1;enabled++)
  for (notrans=0;notrans<=1;notrans++)
  for (charge=0;charge<=1;charge++)
  for (int t=0;t<5;t++) {
    team=t==4?255:t;
    body=mug=ready=-99;
    UH_ApplyWeaponTranslation(123,TCLR_NONE);
    int expected=((IsTeamGame || (!tick && startupteam)) && enabled && !notrans && team<4)
      ? TCLR_DEFAULT+team:123;
    assert(body==expected);
    assert(mug==123);
    assert(ready==(charge?-99:123));
    checks++;
  }
  noweapon=1; body=mug=ready=-99;
  UH_ApplyWeaponTranslation(123,700);
  assert(body==-99 && mug==-99 && ready==-99);
  noweapon=0;
  UH_ApplyWeaponTranslation(CLR_PREVCOLOR,700);
  assert(body==-99 && mug==-99 && ready==-99);
  printf("v6c color contract: %d option/team/startup/charge combinations passed\n",checks);
}
'''

def main():
    source=(ROOT/'src/acs_source/v6b_overrides/corescripts/systems/COLOTRNS.acs').read_text()
    code=STUBS+function(source,'UH_ApplyWeaponTranslation')+TESTS
    with tempfile.TemporaryDirectory(prefix='uh-v6c-color-') as directory:
        path=Path(directory)
        (path/'test.c').write_text(code)
        subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(path/'test.c'),'-o',str(path/'test')],check=True)
        subprocess.run([str(path/'test')],check=True)

if __name__=='__main__':main()
