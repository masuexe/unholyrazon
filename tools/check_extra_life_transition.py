#!/usr/bin/env python3
"""Exercise the actual transition ACS with C stubs; ACC checks ACS separately.

Delay injects damage/reentry, death, morph and result-sequence changes. This
checks transaction/cleanup behavior, not engine collision, rendering or netplay.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "src/acs_source/systems/player_properties/extra_life_transition.acs").read_text()
    source = source.replace('script "uh_ExtraLifeTransition" (void)', "void Transition(void)")
    source = source.replace('script "uh_ExtraLifeDeath" DEATH', "void Death(void)")
    source = source.replace("function ", "").replace("terminate;", "return;")
    source = source.replace("str body", "const char *body")
    source = source.replace("32.0", "(32 * 65536)")
    source = re.sub(r'Log\(s:"[^"]*"\);', 'failures++;', source)
    pain = (ROOT / "src/actors/player/classbase/root/ClassBase_UH00.dec").read_text()
    assert 'A_JumpIfInventory("PlayerPropertyExtraLifeMortis", 1, "MedicMortis")' in pain
    dickhead = (ROOT / "src/actors/items/tow/Dickhead.dec").read_text().split("actor Dickhead :")[1]
    assert 'A_GiveInventory("MortisBlessing_P", 1)' in dickhead
    assert "AutoUnholyInsuranceItem" not in dickhead
    with tempfile.TemporaryDirectory(prefix="uh-extra-life-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(STUBS + source + TESTS)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define APROP_Health 0
#define APROP_Invulnerable 1
#define PROP_TOTALLYFROZEN 1
#define GAMESTATE_INRESULTSEQUENCE 3
#define ELP_MORTIS 2
#define INPUT_BUTTONS 1
#define BT_ATTACK 1
#define BT_ALTATTACK 2
#define WARPF_TESTONLY 512
struct Entry { const char *name; int value; } inv[40], flags[40];
int ni, nf, hp, x, y, z, elapsed, attempts, blocked, failures, spent;
int event, state, buttons, connected, spectator, frozen, fx, healed, earlyfire;
const char *actorclass;
void Transition(void);
void Death(void);
int *Cell(struct Entry *entries, int *count, const char *name) {
  for (int i = 0; i < *count; i++)
    if (!strcmp(entries[i].name, name)) return &entries[i].value;
  assert(*count < 40);
  entries[*count].name = name;
  entries[*count].value = 0;
  return &entries[(*count)++].value;
}
int CheckInventory(const char *name) { return *Cell(inv, &ni, name); }
void GiveInventory(const char *name, int amount) {
  if (!strcmp(name, "UH_ArtiTeleport_P")) {
    assert(!frozen);
    assert(*Cell(flags, &nf, "SOLID"));
    assert(*Cell(flags, &nf, "NOTELESTOMP"));
    assert(!*Cell(flags, &nf, "THRUSPECIES"));
    assert(!*Cell(flags, &nf, "THRUACTORS"));
    attempts++;
    if (attempts > blocked) { x = 500; y = 600; z = 0; }
    return;
  }
  *Cell(inv, &ni, name) += amount;
}
void TakeInventory(const char *name, int amount) {
  int *value = Cell(inv, &ni, name);
  *value = *value > amount ? *value - amount : 0;
}
void ChangeFlag(const char *name, int value) { *Cell(flags, &nf, name) = value; }
int CheckFlag(int tid, const char *name) { assert(!tid); return *Cell(flags, &nf, name); }
int PlayerNumber(void) { return 0; }
int PlayerInGame(int player) { assert(!player); return connected; }
int PlayerIsSpectator(int player) { assert(!player); return spectator; }
int SetActivatorToPlayer(int player) { assert(!player); return connected; }
int GetActorProperty(int tid, int prop) {
  assert(!tid); return prop == APROP_Health ? hp : CheckFlag(0, "INVULNERABLE");
}
void SetActorProperty(int tid, int prop, int value) {
  assert(!tid && prop == APROP_Invulnerable); ChangeFlag("INVULNERABLE", value);
}
int GetGameModeState(void) { return state; }
const char *GetActorClass(int tid) { assert(!tid); return actorclass; }
int StrICmp(const char *a, const char *b) { return strcasecmp(a, b); }
int GetActorX(int tid) { assert(!tid); return x; }
int GetActorY(int tid) { assert(!tid); return y; }
int GetActorZ(int tid) { assert(!tid); return z; }
void SetActorVelocity(int tid, int a, int b, int c, int add, int bob) {
  assert(!(tid | a | b | c | add | bob));
}
void SetActorPosition(int tid, int a, int b, int c, int fog) {
  assert(!tid && !fog); x = a; y = b; z = c;
}
void SetPlayerProperty(int who, int value, int prop) {
  assert(!who && prop == PROP_TOTALLYFROZEN); frozen = value;
}
int Warp(int tid, int a, int b, int c, int angle, int test) {
  assert(!(tid | a | b | c | angle) && test == WARPF_TESTONLY); return 1;
}
void SpawnForced(const char *name, int a, int b, int c) {
  assert(!strcmp(name, "FakeDeathFX") && a == x && b == y && c == z + 32 * 65536); fx++;
}
void ActivatorSound(const char *name, int volume) { assert(!strcmp(name, "*death") && volume == 127); }
int GetPlayerInput(int who, int input) { assert(who == -1 && input == INPUT_BUTTONS); return buttons; }
int ACS_NamedExecuteWithResult(const char *name, int player, int toggle, ...) {
  assert(!player || !strcmp(name, "uh_Health"));
  if (!strcmp(name, "uh_extralifeplayer")) {
    if (toggle) GiveInventory("PlayerPropertyExtraLifeMortis", 1);
    else {
      assert(CheckInventory("PlayerPropertyInvulnerable") > 0);
      TakeInventory("PlayerPropertyExtraLifeMortis", 1); spent++;
    }
    return 0;
  }
  if (!strcmp(name, "uh_Health")) { assert(player == 6 && toggle == 1000); hp = 1000; healed++; return 0; }
  const char *property = NULL;
  if (!strcmp(name, "core_invulnerableplayer")) property = "PlayerPropertyInvulnerable";
  if (!strcmp(name, "core_freezeplayer")) property = "PlayerPropertyFrozen";
  if (!strcmp(name, "core_nopushplayer")) property = "NoPushFlag";
  if (!strcmp(name, "core_nogravityplayer")) property = "PlayerPropertyNoGravity";
  if (!strcmp(name, "core_invisibleplayer")) property = "PlayerPropertyInvisible";
  assert(property);
  if (toggle) GiveInventory(property, 1); else TakeInventory(property, 1);
  if (!strcmp(name, "core_freezeplayer")) frozen = CheckInventory(property) > 0;
  return 0;
}
void Delay(int ticks) {
  assert(ticks == 1); elapsed++;
  if (elapsed <= 35) {
    assert(CheckInventory("PlayerPropertyInvulnerable"));
    assert(frozen && !CheckFlag(0, "SOLID") && hp == 1);
    Transition(); // Repeated lethal hits must not spend another life.
  }
  if (event == 1 && elapsed == 5) { hp = 0; Death(); }
  if (event == 2 && elapsed == 5) state = GAMESTATE_INRESULTSEQUENCE;
  if (event == 3 && elapsed == 5) actorclass = "DifferentBody";
  if (event == 4 && elapsed == 5) { connected = 0; ni = 0; frozen = 0; }
  if (event == 5 && elapsed == 36) buttons = earlyfire;
}
'''

TESTS = r'''
void Reset(void) {
  ni = nf = 0; hp = 1; x = y = z = 0;
  elapsed = attempts = blocked = failures = spent = event = state = buttons = 0;
  spectator = frozen = fx = healed = earlyfire = 0; connected = 1;
  actorclass = "MegaManU";
  GiveInventory("PlayerPropertyExtraLifeMortis", 2);
  ChangeFlag("SOLID", true);
}
void Clean(void) {
  assert(!CheckInventory("UH_ExtraLifeLease_F"));
  assert(!CheckInventory("UH_ExtraLifePhase_F"));
  assert(!CheckInventory("PlayerPropertyFrozen") && !frozen);
  assert(!CheckInventory("PlayerPropertyInvulnerable"));
  assert(!CheckInventory("PlayerPropertyInvisible"));
  assert(!CheckInventory("PlayerPropertyNoGravity"));
  assert(!CheckInventory("NoPushFlag"));
  assert(CheckFlag(0, "SOLID"));
}
int main(void) {
  Reset(); Transition(); Clean();
  assert(spent == 1 && fx == 1 && elapsed == 53 && healed == 1 && x == 500);
  assert(CheckInventory("PlayerPropertyExtraLifeMortis") == 1);
  Reset(); blocked = 3; Transition(); Clean(); assert(attempts == 4 && !failures);
  Reset(); blocked = 100; Transition(); Clean();
  assert(attempts == 16 && failures == 1 && !x && hp == 1000);
  assert(CheckInventory("PlayerPropertyExtraLifeMortis") == 2);
  for (int e = 1; e <= 3; e++) {
    Reset(); event = e; Transition(); Clean(); assert(!attempts && !healed && elapsed == 5);
  }
  Reset(); event = 4; Transition(); assert(elapsed == 5 && !attempts && !healed);
  for (int button = 1; button <= 2; button++) {
    Reset(); event = 5; earlyfire = button; Transition(); Clean(); assert(elapsed == 36);
  }
  Reset(); hp = 2; Transition(); Clean(); assert(!spent && !elapsed);
  Reset(); TakeInventory("PlayerPropertyExtraLifeMortis", 2); Transition(); Clean(); assert(!spent);
  Reset(); spectator = 1; Transition(); Clean(); assert(!spent);
  Reset();
  GiveInventory("PlayerPropertyFrozen", 1); GiveInventory("PlayerPropertyInvulnerable", 1);
  GiveInventory("PlayerPropertyInvisible", 1); GiveInventory("PlayerPropertyNoGravity", 1);
  GiveInventory("NoPushFlag", 1); ChangeFlag("THRUSPECIES", true); ChangeFlag("THRUACTORS", true);
  Transition();
  assert(CheckInventory("PlayerPropertyFrozen") == 1 && frozen);
  assert(CheckInventory("PlayerPropertyInvulnerable") == 1);
  assert(CheckInventory("PlayerPropertyInvisible") == 1);
  assert(CheckInventory("PlayerPropertyNoGravity") == 1 && CheckInventory("NoPushFlag") == 1);
  assert(CheckFlag(0, "THRUSPECIES") && CheckFlag(0, "THRUACTORS"));
  Reset(); ChangeFlag("SOLID", false); ChangeFlag("NOGRAVITY", true);
  ChangeFlag("INVISIBLE", true); ChangeFlag("INVULNERABLE", true);
  Transition();
  assert(!CheckFlag(0, "SOLID") && CheckFlag(0, "NOGRAVITY"));
  assert(CheckFlag(0, "INVISIBLE") && CheckFlag(0, "INVULNERABLE"));
  assert(!CheckInventory("UH_ExtraLifeLease_F") && !frozen);
  puts("extra-life transition: transaction, retries, cancellation, grace and property ownership passed");
}
'''

if __name__ == "__main__":
    main()
