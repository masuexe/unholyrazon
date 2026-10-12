#!/usr/bin/env python3
"""Execute the actual settlement ACS functions with C stubs; no engine launch.

Checks policy, living sides, deadline priority, cancellation, repeated windows,
forced endings and stale generations. ACC checks syntax separately; this does
not simulate the engine's ACS scheduler or multiplayer delivery.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    definitions = (ROOT / "src/acs_source/unholy/uh_def.acs").read_text()
    definitions = definitions[definitions.index("#define UH_SETTLE_WAIT"):
                              definitions.index("int revivingqueue;")]
    source = (ROOT / "src/acs_source/unholy/uh_settlement.acs").read_text()
    source = source.split('script "ub_ExitFinishedRound"')[0]
    source = re.sub(r"\bfunction\s+", "", source)
    # All included functions use plain integers/strings, no fixed/latent code.
    ff = (ROOT / "src/acs_source/unholy/uh_postround_ff.acs").read_text()
    ff = ff.split('script "uh_RefreshPostRoundFF"')[0].replace("function ", "")
    ff = ff.replace("int row;", "int row; int i;").replace("for (int i =", "for (i =")
    helpers = (ROOT / "src/acs_source/unholy/uh_round_helpers.acs").read_text()
    begin = helpers.index("function void MakeAllPlayersInvun(void)")
    end = helpers.index("// Presets a random number", begin)
    invun = helpers[begin:end].replace("function ", "").replace(
        "until (playernum == 1064)", "while (playernum != 1064)")
    code = STUBS + definitions + ff + invun + source + TESTS
    with tempfile.TemporaryDirectory(prefix="uh-settlement-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(code)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
typedef const char *str;
#define MAX_PLAYERS 64
#define PLS_SURVIVOR 1
#define PLS_BOSS 2
#define PLS_EYE 6
#define APROP_HEALTH 0
#define APROP_DamageFactor 1
#define GAMESTATE_INPROGRESS 2
#define GAMESTATE_INRESULTSEQUENCE 3
#define UH_LOG_INFO 3
bool gameover, isbonuseventactive, versusfightevent;
int tick, engine = GAMESTATE_INPROGRESS, option;
int uh_roundtimerdeadline = 1000;
int playerlifestatusarr[MAX_PLAYERS], hp[MAX_PLAYERS], spec[MAX_PLAYERS];
bool connected[MAX_PLAYERS];
str currentmusiclump = "BATTLE", currentmusictitle = "Battle";
str currentmusicalbum = "Album", currentmusicartist = "Artist";
int currentmusiccontext = 2;
int restores, clears, displays, notices;
int winstreak = 3;
void UH_ShowSettlementResumed(void) { notices++; }
int postff = 1, inventory[MAX_PLAYERS][10], invunwrites;
void SetActorProperty(int tid, int prop, int value) {
  assert(tid >= 1000 && tid < 1064 && prop == APROP_DamageFactor && value == 0);
  invunwrites++;
}
str pawnclasses[MAX_PLAYERS];
str UH_PostRoundProtection(int index);
str GetActorClass(int tid) { return pawnclasses[tid-1000] ? pawnclasses[tid-1000] : "Player"; }
int StrICmp(str a, str b) { return strcasecmp(a,b); }
int protection_index(str name) {
  for (int i=0;i<10;i++) if (!strcmp(name,UH_PostRoundProtection(i))) return i;
  assert(0); return -1;
}
int CheckActorInventory(int tid, str name) { return inventory[tid-1000][protection_index(name)]; }
void TakeActorInventory(int tid, str name, int count) { inventory[tid-1000][protection_index(name)] -= count; }
void GiveActorInventory(int tid, str name, int count) { inventory[tid-1000][protection_index(name)] += count; }
int GetCVar(str name) {
  if (!strcmp(name,"uh_sv_postroundfriendlyfire")) return postff;
  assert(!strcmp(name, "uh_sv_resumeonrevive")); return option;
}
int GetGameModeState(void) { return engine; }
int Timer(void) { return tick; }
bool PlayerInGame(int p) { return connected[p]; }
int PlayerIsSpectator(int p) { return spec[p]; }
int GetActorProperty(int tid, int prop) { assert(prop == APROP_HEALTH); return hp[tid-1000]; }
void ClearHudMessageBold(int id) { assert(id == 66 || id == 67 || id == 100); clears++; }
void UH_PlayTrack(str lump, str title, str album, str artist, int context, int announce) {
  assert(!strcmp(lump, "BATTLE") && !strcmp(title, "Battle"));
  assert(!strcmp(album, "Album") && !strcmp(artist, "Artist"));
  assert(context == 2 && announce == 0); restores++;
}
void ACS_NamedExecute(str name, int map) {
  assert(!strcmp(name, "ub_BossHealthWatcher") && map == 0); displays++;
}
void UH_Log(int level, str text) { assert(level == UH_LOG_INFO && text[0]); }
'''

TESTS = r'''
int main(void) {
  // A disabled option bypasses waiting; bonus/versus/native results always do.
  assert(!UH_CanWaitForRevival()); option = 1;
  assert(UH_CanWaitForRevival());
  isbonuseventactive = true; assert(!UH_CanWaitForRevival()); isbonuseventactive = false;
  versusfightevent = true; assert(!UH_CanWaitForRevival()); versusfightevent = false;
  engine = GAMESTATE_INRESULTSEQUENCE; assert(!UH_CanWaitForRevival()); engine = GAMESTATE_INPROGRESS;

  connected[0] = connected[1] = true; hp[0] = hp[1] = 100;
  playerlifestatusarr[0] = playerlifestatusarr[1] = PLS_SURVIVOR;
  assert(!UH_SettlementHasOpponents());
  playerlifestatusarr[1] = PLS_BOSS; assert(UH_SettlementHasOpponents());
  playerlifestatusarr[1] = PLS_EYE; assert(UH_SettlementHasOpponents());
  hp[1] = 0; assert(!UH_SettlementHasOpponents()); hp[1] = 100;
  spec[1] = 1; assert(!UH_SettlementHasOpponents()); spec[1] = 0;
  connected[1] = false; assert(!UH_SettlementHasOpponents()); connected[1] = true;
  hp[0] = 0;

  tick = 10;
  int first = UH_BeginSettlement(315, true);
  assert(winstreak == 4);
  assert(first == 1 && !gameover && uh_settlementstate[UH_SETTLEMENT_PENDING]);
  assert(UH_CanExitSettlement(0) && !UH_CanExitSettlement(first));
  tick = 50;
  assert(UH_PollSettlement(first) == UH_SETTLE_WAIT);
  // Option changes mid-window affect the next candidate, not this one.
  option = 0; hp[0] = 100;
  assert(UH_PollSettlement(first) == UH_SETTLE_RESUME);
  assert(!gameover && !uh_settlementstate[UH_SETTLEMENT_PENDING]);
  assert(uh_roundtimerdeadline == 1040 && restores == 1 && clears == 3 && displays == 1 && notices == 1);
  assert(UH_PollSettlement(first) == UH_SETTLE_ABORT);
  assert(!UH_CanExitSettlement(first) && winstreak == 3);
  assert(!UH_CanWaitForRevival()); option = 1;

  // A second window invalidates old ownership without disturbing the new one.
  hp[0] = 0;
  int second = UH_BeginSettlement(360, false);
  assert(winstreak == -1);
  assert(second == 2 && UH_PollSettlement(first) == UH_SETTLE_ABORT);
  assert(uh_settlementstate[UH_SETTLEMENT_PENDING]);
  assert(!UH_CanExitSettlement(first) && !UH_CanExitSettlement(second));
  tick = uh_settlementstate[UH_SETTLEMENT_DEADLINE]; hp[0] = 100;
  assert(UH_PollSettlement(second) == UH_SETTLE_RESUME); // exact deadline revival
  assert(uh_roundtimerdeadline == 1400 && restores == 2 && winstreak == 3 && notices == 2);

  hp[0] = 0;
  int third = UH_BeginSettlement(315, true);
  tick = uh_settlementstate[UH_SETTLEMENT_DEADLINE] - 1;
  assert(UH_PollSettlement(third) == UH_SETTLE_WAIT);
  tick++;
  assert(UH_PollSettlement(third) == UH_SETTLE_COMMIT);
  assert(gameover && !uh_settlementstate[UH_SETTLEMENT_PENDING] && winstreak == 4);
  assert(UH_CanExitSettlement(third) && !UH_CanExitSettlement(second));
  assert(UH_PollSettlement(third) == UH_SETTLE_ABORT && winstreak == 4); // single commit

  // Native wins take priority even when both sides have returned.
  gameover = false; hp[0] = 100;
  int fourth = UH_BeginSettlement(315, false); engine = GAMESTATE_INRESULTSEQUENCE;
  assert(UH_PollSettlement(fourth) == UH_SETTLE_COMMIT && gameover);
  assert(restores == 2 && winstreak == -1);

  // External forced endings cannot be cancelled by this controller.
  gameover = false; engine = GAMESTATE_INPROGRESS;
  int fifth = UH_BeginSettlement(315, true); assert(winstreak == 1); gameover = true;
  assert(UH_PollSettlement(fifth) == UH_SETTLE_ABORT && gameover);
  assert(!uh_settlementstate[UH_SETTLEMENT_PENDING] && restores == 2 && winstreak == -1);
  // Boss streak continuation and switching winners both restore the old sign.
  gameover = false; winstreak = -3;
  int sixth = UH_BeginSettlement(315, false); assert(winstreak == -4);
  assert(UH_PollSettlement(sixth) == UH_SETTLE_RESUME && winstreak == -3);
  int seventh = UH_BeginSettlement(360, true); assert(winstreak == 1);
  assert(UH_PollSettlement(seventh) == UH_SETTLE_RESUME && winstreak == -3);
  // Friendly fire: ordinary combat leaves all immunity powers unchanged.
  gameover = false; engine = GAMESTATE_INPROGRESS;
  uh_settlementstate[UH_SETTLEMENT_PENDING] = false;
  UH_RefreshPostRoundFF();
  for (int i=0;i<10;i++) inventory[0][i] = 1;
  UH_RefreshPostRoundFF();
  assert(inventory[0][0] == 1 && inventory[0][9] == 1);
  // Pending settlement removes Survivor/Boss/Eye and bonus-event powers alike.
  uh_settlementstate[UH_SETTLEMENT_PENDING] = true;
  UH_RefreshPostRoundFF();
  for (int i=0;i<10;i++) assert(inventory[0][i] == 0);
  inventory[0][3] = 1; UH_RefreshPostRoundFF(); assert(inventory[0][3] == 0);
  // Cancellation restores exact original powers, including a re-grant.
  uh_settlementstate[UH_SETTLEMENT_PENDING] = false;
  UH_RefreshPostRoundFF();
  for (int i=0;i<10;i++) assert(inventory[0][i] == 1);
  // Final bonus/forced results and native results use the same policy.
  gameover = true; UH_RefreshPostRoundFF(); assert(inventory[0][6] == 0);
  postff = 0; UH_RefreshPostRoundFF(); assert(inventory[0][6] == 1);
  postff = 1; gameover = false; engine = GAMESTATE_INRESULTSEQUENCE;
  UH_RefreshPostRoundFF(); assert(inventory[0][6] == 0);
  // Morphs cannot inherit the preceding pawn's protection snapshot.
  pawnclasses[0] = "OtherClass";
  memset(inventory[0],0,sizeof(inventory[0])); inventory[0][4] = 1;
  UH_RefreshPostRoundFF();
  engine = GAMESTATE_INPROGRESS; UH_RefreshPostRoundFF();
  assert(inventory[0][4] == 1 && inventory[0][0] == 0);
  // Death/departure discards a snapshot instead of granting it on reuse.
  gameover = true; UH_RefreshPostRoundFF(); hp[0] = 0; UH_RefreshPostRoundFF();
  gameover = false; hp[0] = 100; UH_RefreshPostRoundFF(); assert(inventory[0][4] == 0);
  // Special result-wide invulnerability must not block enabled friendly fire.
  postff = 1; MakeAllPlayersInvun(); assert(invunwrites == 0);
  postff = 0; MakeAllPlayersInvun(); assert(invunwrites == 64);
  puts("Round settlement and post-round friendly fire logic: PASS");
  return 0;
}
'''


if __name__ == "__main__":
    main()
