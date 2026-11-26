#!/usr/bin/env python3
"""Run the actual ACS visibility predicates under C stubs, without an engine.

Checks client/server agreement, FFA privacy, normal teams, one-vs-all and
automap observer rules. ACC separately checks syntax; this does not model
network delivery or the ACS scheduler.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    match = re.search(r"function\s+\w+\s+" + name + r"\([^)]*\)\s*\{", source)
    assert match, name
    depth = 1
    end = match.end()
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end].replace("function ", "") + "\n"


def check_automap_xray_wiring(xray: str, mautomap: str) -> None:
    """Verify ACS wiring between X-Ray state, renderer gating and MAUTOMAP."""
    xray_requirements = (
        ('script "uh_HasXRayVision"', "missing uh_HasXRayVision script"),
        ('script "uh_CanXRayRevealTarget"', "missing uh_CanXRayRevealTarget script"),
        ('ACS_NamedExecute("core_automap_player_markers", 0)',
         "UH_EnsureXRayRenderer does not ensure core_automap_player_markers"),
        ('CheckAutomap() == AUTOMAP_OFF',
         "UH_XRayVisionManager does not suppress 3D labels while automap is open"),
    )
    for snippet, message in xray_requirements:
        if snippet not in xray:
            raise SystemExit(f"error: {message} in projectile_and_xray.acs")

    mautomap_requirements = (
        ('ACS_NamedExecuteWithResult("uh_HasXRayVision", cpn)',
         "MAUTOMAP does not query uh_HasXRayVision"),
        ('else if (viewerHasXRay && ACS_NamedExecuteWithResult("uh_CanXRayRevealTarget", cpn, pln))',
         "MAUTOMAP Unholy branch does not reveal X-Ray targets via uh_CanXRayRevealTarget"),
        ('if (should_reveal || (viewerHasXRay && ACS_NamedExecuteWithResult("uh_CanXRayRevealTarget", cpn, pln)))',
         "MAUTOMAP non-Unholy branch does not reveal X-Ray targets via uh_CanXRayRevealTarget"),
        ('SpawnForced("PlayerPawn_Revealed_MapMarker"',
         "MAUTOMAP no longer spawns PlayerPawn_Revealed_MapMarker for revealed players"),
    )
    for snippet, message in mautomap_requirements:
        if snippet not in mautomap:
            raise SystemExit(f"error: {message} in MAUTOMAP.acs")


def main():
    team = (ROOT / "src/acs_source/_imports/uhteamrt.acs").read_text()
    automap = (ROOT / "src/acs_source/hud/automap_markers.acs").read_text()
    xray = (ROOT / "src/acs_source/systems/shared/projectile_and_xray.acs").read_text()
    mautomap = (ROOT / "src/acs_source/v6b_overrides/corescripts/systems/MAUTOMAP.acs").read_text()
    check_automap_xray_wiring(xray, mautomap)
    constants = "\n".join(
        re.sub(r"^#libdefine\b", "#define", line)
        for line in re.findall(
            r"^#(?:lib)?define (?:PLS_\w+|UH_SCOREPOLICY_\w+|UH_TI_REV_\w+|UH_TI_POLICY_REV_SLOT)\s+.*$",
            team, re.M))
    xray_constants = "\n".join(re.findall(
        r"^#define (?:UH_XRAY_STEALTH_ALPHA_MAX|UH_XRAY_DIRECT_SIGHT_ALPHA_MIN)\s+.*$",
        xray, re.M))
    assert xray_constants.count("#define") == 2, "missing X-Ray threshold constants"
    constants = constants + "\n" + xray_constants
    functions = "".join(function(team, name) for name in (
        "UH_AreDisplayTeammates", "UH_Ti_ServerTeammatesForSplit", "UH_Ti_AcceptRevision"))
    receiver = team.replace('script "uh_ti_sync_policy" (int policy, int revision) CLIENTSIDE',
                            'function void ReceivePolicy(int policy, int revision)')
    functions += function(receiver, "ReceivePolicy").replace("terminate;", "return;")
    # TLMS bottom counters: the counts must use the same relation as the bar,
    # exclude the viewer, and ignore dead or freed slots.
    tlms = (ROOT / "src/acs_source/hud/tlms_display.acs").read_text()
    functions += "".join(function(tlms, name) for name in (
        "UH_Tlms_IsAlive", "UH_Tlms_Viewer", "UH_Tlms_CountAllies",
        "UH_Tlms_CountEnemies"))
    functions += "".join(function(xray, name) for name in (
        "UH_IsXRayTargetStealthed", "UH_IsActorXRayStealthed",
        "UH_ShouldShowXRay3D", "UH_HasXRayVision", "UH_CanXRayRevealTarget"))
    code = STUBS + constants + "\n" + functions + function(automap, "UH_AM_CanSee") + TESTS
    with tempfile.TemporaryDirectory(prefix="uh-team-visibility-") as directory:
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
#define MAX_PLAYERS 64
#define UH_AM_PLAYER_TID 1000
#define APROP_Health 0
#define APROP_Alpha 3
#define APROP_RenderStyle 16
#define STYLE_None 0
#define STYLE_Normal 1
#define STYLE_Fuzzy 2
#define STYLE_Translucent 3
int uhtirole[MAX_PLAYERS], uhsrvrole[MAX_PLAYERS], uhtilife[MAX_PLAYERS * 2 + 1];
int uhtiscorepolicy, uhtiova, uhtiovatarget;
int spectator[MAX_PLAYERS];
int in_game[MAX_PLAYERS];
int health[MAX_PLAYERS];
int alpha[MAX_PLAYERS];
int render_style[MAX_PLAYERS];
int invisible_flag[MAX_PLAYERS];
int xray_on[MAX_PLAYERS];
int two_xray_on[MAX_PLAYERS];
int active_tid = -1;
bool stats[MAX_PLAYERS];
int clears;
void UH_Ti_EnsureClientInitialized(void) {}
void UH_Ti_ClearStats(int pn) { stats[pn] = false; clears++; }
int PlayerIsSpectator(int pn) { return spectator[pn]; }
int PlayerInGame(int pn) { return (pn >= 0 && pn < MAX_PLAYERS) ? in_game[pn] : 0; }
int SetActivatorToPlayer(int pn) {
  if (pn < 0 || pn >= MAX_PLAYERS || !in_game[pn]) return 0;
  active_tid = UH_AM_PLAYER_TID + pn;
  return 1;
}
int GetActorProperty(int tid, int prop) {
  int p = (tid == 0 ? active_tid : tid) - UH_AM_PLAYER_TID;
  if (p < 0 || p >= MAX_PLAYERS) return 0;
  if (prop == APROP_Health) return health[p];
  if (prop == APROP_Alpha) return alpha[p];
  if (prop == APROP_RenderStyle) return render_style[p];
  return 0;
}
int CheckFlag(int tid, const char *flag) {
  int p = (tid == 0 ? active_tid : tid) - UH_AM_PLAYER_TID;
  if (p < 0 || p >= MAX_PLAYERS) return 0;
  if (strcmp(flag, "INVISIBLE") == 0) return invisible_flag[p];
  return 0;
}
int CheckInventory(const char *item) {
  int p = active_tid - UH_AM_PLAYER_TID;
  if (p < 0 || p >= MAX_PLAYERS) return 0;
  if (strcmp(item, "UH_XRayVisionOn_F") == 0) return xray_on[p];
  if (strcmp(item, "UH_TwoPlayerXRayOn_F") == 0) return two_xray_on[p];
  return 0;
}
'''

TESTS = r'''
int main(void) {
  int roles[] = {PLS_NULL, PLS_SURVIVOR, PLS_BOSS, PLS_EYE};
  int checks = 0;
  // All role pairs, all defined policies and split targets. FFA must never
  // inherit the ordinary Survivor/Survivor or Boss/Boss team relationship.
  for (int policy = UH_SCOREPOLICY_INVALID; policy <= UH_SCOREPOLICY_MULTITEAM; policy++) {
    uhtiscorepolicy = policy;
    for (int a = 0; a < 4; a++) for (int b = 0; b < 4; b++) {
      uhtirole[0] = uhsrvrole[0] = roles[a];
      uhtirole[1] = uhsrvrole[1] = roles[b];
      for (int ova = 0; ova < 2; ova++) for (int target = -1; target <= 2; target++) {
        uhtiova = ova; uhtiovatarget = target;
        bool expected = false;
        if (policy != UH_SCOREPOLICY_FFA && policy != UH_SCOREPOLICY_INVALID
            && a && b) {
          expected = ova ? target == 2
            : roles[a] == roles[b] && roles[a] != PLS_EYE;
        }
        assert(UH_AreDisplayTeammates(0, 1) == expected);
        assert(UH_Ti_ServerTeammatesForSplit(0, 1, ova, target, policy) == expected);
        assert(!UH_AreDisplayTeammates(0, 0));
        assert(!UH_Ti_ServerTeammatesForSplit(0, 0, ova, target, policy));
        checks++;
      }
    }
  }
  assert(!UH_AreDisplayTeammates(-1, 1));
  assert(!UH_AreDisplayTeammates(0, MAX_PLAYERS));
  // The latest status/policy must win even when same-tic scripts run newest
  // first. Each subject is independent; cleared slots retain their revision.
  int stamp = MAX_PLAYERS;
  assert(UH_Ti_AcceptRevision(stamp, 102));
  assert(!UH_Ti_AcceptRevision(stamp, 101));
  assert(!UH_Ti_AcceptRevision(stamp, 102));
  assert(UH_Ti_AcceptRevision(stamp, 103));
  assert(UH_Ti_AcceptRevision(stamp + 1, 1));
  assert(UH_Ti_AcceptRevision(UH_TI_POLICY_REV_SLOT, 205));
  assert(!UH_Ti_AcceptRevision(UH_TI_POLICY_REV_SLOT, 204));
  assert(UH_Ti_AcceptRevision(stamp, 0)); // local debug call
  assert(uhtilife[stamp] == 103);
  uhtilife[stamp] = UH_TI_REV_MASK;
  assert(UH_Ti_AcceptRevision(stamp, 1)); // wrap
  assert(!UH_Ti_AcceptRevision(stamp, UH_TI_REV_MASK));
  // Execute the actual policy receiver: newest FFA wins over an older NORMAL
  // snapshot, old teammate health is purged, and duplicate policy snapshots
  // leave fresh stats intact rather than causing display flicker.
  uhtilife[UH_TI_POLICY_REV_SLOT] = 0;
  uhtiscorepolicy = UH_SCOREPOLICY_NORMAL;
  stats[1] = true;
  ReceivePolicy(UH_SCOREPOLICY_FFA, 400);
  assert(uhtiscorepolicy == UH_SCOREPOLICY_FFA && !stats[1]);
  int before = clears;
  ReceivePolicy(UH_SCOREPOLICY_NORMAL, 399);
  assert(uhtiscorepolicy == UH_SCOREPOLICY_FFA && clears == before);
  stats[1] = true;
  ReceivePolicy(UH_SCOREPOLICY_FFA, 401);
  assert(stats[1] && clears == before);
  ReceivePolicy(999, 402);
  assert(uhtiscorepolicy == UH_SCOREPOLICY_INVALID && !stats[1]);
  // Living FFA players cannot see other positions, regardless of role.
  uhtiova = 0;
  for (int a = 1; a < 4; a++) for (int b = 1; b < 4; b++) {
    uhtirole[0] = uhtilife[0] = roles[a];
    health[0] = 100;
    uhtirole[1] = uhtilife[1] = roles[b];
    uhtiscorepolicy = UH_SCOREPOLICY_FFA;
    assert(UH_AM_CanSee(0, 0));
    assert(!UH_AM_CanSee(0, 1));
    uhtilife[0] = PLS_DEAD;
    assert(!UH_AM_CanSee(0, 1)); // stale death snapshot after revival
    health[0] = 0;
    assert(UH_AM_CanSee(0, 1));
    health[0] = 100;
    uhtilife[0] = roles[a]; spectator[0] = 1;
    assert(UH_AM_CanSee(0, 1));
    spectator[0] = 0;
    uhtiscorepolicy = UH_SCOREPOLICY_NORMAL;
    assert(UH_AM_CanSee(0, 1) == (roles[a] == roles[b] && roles[a] != PLS_EYE));
    checks++;
  }
  // TLMS counters: the viewer is excluded, dead/freed slots are excluded, and
  // the relation is exactly the teammate-bar relation.
  for (int i = 0; i < MAX_PLAYERS; i++) {
    uhtilife[i] = PLS_NULL; uhtirole[i] = PLS_NULL; spectator[i] = 0;
  }
  uhtiscorepolicy = UH_SCOREPOLICY_NORMAL;
  uhtiova = 0; uhtiovatarget = -1;
  uhtirole[0] = uhtilife[0] = PLS_SURVIVOR;  // viewer
  uhtirole[1] = uhtilife[1] = PLS_SURVIVOR;  // ally
  uhtirole[2] = uhtilife[2] = PLS_SURVIVOR;  // ally
  uhtirole[3] = uhtilife[3] = PLS_BOSS;      // enemy
  uhtirole[4] = PLS_SURVIVOR; uhtilife[4] = PLS_DEAD;  // dead: never counted
  uhtirole[5] = uhtilife[5] = PLS_EYE;       // Eye never forms a display team
  assert(UH_Tlms_IsAlive(0) && !UH_Tlms_IsAlive(4));
  assert(UH_Tlms_CountAllies(0) == 2);
  assert(UH_Tlms_CountEnemies(0) == 2);
  // FFA: nobody is a teammate.
  uhtiscorepolicy = UH_SCOREPOLICY_FFA;
  assert(UH_Tlms_CountAllies(0) == 0);
  assert(UH_Tlms_CountEnemies(0) == 4);
  // 1-vs-all: the frozen target is alone; everyone else shares one side.
  uhtiscorepolicy = UH_SCOREPOLICY_ONEVSALL; uhtiova = 1; uhtiovatarget = 3;
  assert(UH_Tlms_CountAllies(0) == 3);
  assert(UH_Tlms_CountEnemies(0) == 1);
  assert(UH_Tlms_CountAllies(3) == 0);
  assert(UH_Tlms_CountEnemies(3) == 4);
  // Viewer resolution: a living camera is the viewer, a dead or spectating one
  // has no side, and the camera player wins over the console player.
  uhtiscorepolicy = UH_SCOREPOLICY_NORMAL; uhtiova = 0; uhtiovatarget = -1;
  assert(UH_Tlms_Viewer(1000, 0) == 0);
  assert(UH_Tlms_Viewer(1001, 0) == 1);
  assert(UH_Tlms_Viewer(-1, 0) == 0);
  assert(UH_Tlms_Viewer(-1, -1) == -1);
  spectator[0] = 1;
  assert(UH_Tlms_Viewer(1000, 0) == -1);
  assert(UH_Tlms_Viewer(-1, 0) == -1);
  spectator[0] = 0;
  uhtilife[0] = PLS_DEAD;
  assert(UH_Tlms_Viewer(1000, 0) == -1);
  uhtilife[0] = PLS_SURVIVOR;
  checks++;

  // X-Ray stealth suppression and automap reveal eligibility.
  assert(UH_IsXRayTargetStealthed(STYLE_None, 65536, false));
  assert(UH_IsXRayTargetStealthed(STYLE_Translucent, 0, false));
  assert(UH_IsXRayTargetStealthed(STYLE_Translucent, 6554, false));  // 0.1 Ghost Eye / fade
  assert(UH_IsXRayTargetStealthed(STYLE_Normal, 65536, true));       // +INVISIBLE
  assert(!UH_IsXRayTargetStealthed(STYLE_Translucent, 16384, false));  // 0.25 ALPHA_MIN
  assert(!UH_IsXRayTargetStealthed(STYLE_Translucent, 32768, false));  // 0.5 xray probe
  assert(!UH_IsXRayTargetStealthed(STYLE_Fuzzy, 52428, false));        // 0.8 spawn protection
  assert(!UH_IsXRayTargetStealthed(STYLE_Normal, 65536, false));

  // Stealthed targets hide 3D X-Ray both behind walls and in direct sight.
  assert(!UH_ShouldShowXRay3D(STYLE_None, 65536, false, false));
  assert(!UH_ShouldShowXRay3D(STYLE_None, 65536, false, true));
  assert(!UH_ShouldShowXRay3D(STYLE_Translucent, 0, false, false));
  assert(!UH_ShouldShowXRay3D(STYLE_Translucent, 6554, false, true));
  assert(!UH_ShouldShowXRay3D(STYLE_Normal, 65536, true, false));
  assert(!UH_ShouldShowXRay3D(STYLE_Normal, 65536, true, true));
  assert(UH_ShouldShowXRay3D(STYLE_Normal, 65536, false, false));
  assert(!UH_ShouldShowXRay3D(STYLE_Normal, 65536, false, true));
  assert(UH_ShouldShowXRay3D(STYLE_Translucent, 32768, false, false));
  assert(UH_ShouldShowXRay3D(STYLE_Translucent, 32768, false, true));
  checks++;

  for (int i = 0; i < MAX_PLAYERS; i++) {
    in_game[i] = 1;
    health[i] = 100;
    alpha[i] = 65536;
    render_style[i] = STYLE_Normal;
    invisible_flag[i] = 0;
    spectator[i] = 0;
    xray_on[i] = 0;
    two_xray_on[i] = 0;
  }

  // UH_HasXRayVision requires living non-spectator viewer with an X-Ray token.
  assert(!UH_HasXRayVision(-1));
  assert(!UH_HasXRayVision(0));
  xray_on[0] = 1;
  assert(UH_HasXRayVision(0));
  xray_on[0] = 0;
  two_xray_on[0] = 1;
  assert(UH_HasXRayVision(0));
  spectator[0] = 1;
  assert(!UH_HasXRayVision(0));
  spectator[0] = 0;
  health[0] = 0;
  assert(!UH_HasXRayVision(0));
  health[0] = 100;
  in_game[0] = 0;
  assert(!UH_HasXRayVision(0));
  in_game[0] = 1;

  // UH_CanXRayRevealTarget requires living distinct target not stealthed.
  assert(!UH_CanXRayRevealTarget(0, 0));
  assert(UH_CanXRayRevealTarget(0, 1));
  SetActivatorToPlayer(1);
  assert(!UH_IsActorXRayStealthed(0));
  alpha[1] = 0;
  assert(UH_IsActorXRayStealthed(0));
  assert(!UH_CanXRayRevealTarget(0, 1));
  alpha[1] = 6554;
  assert(!UH_CanXRayRevealTarget(0, 1));
  alpha[1] = 16384;
  assert(UH_CanXRayRevealTarget(0, 1));
  render_style[1] = STYLE_None;
  assert(!UH_CanXRayRevealTarget(0, 1));
  render_style[1] = STYLE_Normal;
  invisible_flag[1] = 1;
  assert(!UH_CanXRayRevealTarget(0, 1));
  invisible_flag[1] = 0;
  health[1] = 0;
  assert(!UH_CanXRayRevealTarget(0, 1));
  health[1] = 100;
  in_game[1] = 0;
  assert(!UH_CanXRayRevealTarget(0, 1));
  in_game[1] = 1;

  // Policy matrix: teammates remain visible when stealthed; X-Ray reveals
  // non-allies only when viewer has X-Ray and target is not stealthed.
  int xpolicies[] = {UH_SCOREPOLICY_NORMAL, UH_SCOREPOLICY_FFA, UH_SCOREPOLICY_ONEVSALL};
  uhtiova = 0; uhtiovatarget = -1;
  uhtirole[0] = uhtilife[0] = PLS_SURVIVOR;
  uhtirole[1] = uhtilife[1] = PLS_SURVIVOR;  // teammate in NORMAL
  uhtirole[2] = uhtilife[2] = PLS_BOSS;      // opponent in NORMAL
  for (int pi = 0; pi < 3; pi++) {
    uhtiscorepolicy = xpolicies[pi];
    if (xpolicies[pi] == UH_SCOREPOLICY_ONEVSALL) {
      uhtiova = 1; uhtiovatarget = 2;
    } else {
      uhtiova = 0; uhtiovatarget = -1;
    }
    alpha[1] = 0;  // stealthed player 1: teammate stays visible in NORMAL, hidden to X-Ray otherwise
    alpha[2] = 65536;
    bool ally_visible = UH_AM_CanSee(0, 1);
    bool ally_xray = !ally_visible && UH_HasXRayVision(0) && UH_CanXRayRevealTarget(0, 1);
    assert(ally_visible == (xpolicies[pi] == UH_SCOREPOLICY_NORMAL));
    assert(!ally_xray);
    bool foe_xray_visible = !UH_AM_CanSee(0, 2) && UH_HasXRayVision(0) && UH_CanXRayRevealTarget(0, 2);
    assert(foe_xray_visible);
    alpha[2] = 6554;  // stealthed opponent disappears
    bool foe_xray_hidden = !UH_AM_CanSee(0, 2) && UH_HasXRayVision(0) && UH_CanXRayRevealTarget(0, 2);
    assert(!foe_xray_hidden);
    checks++;
  }

  printf("team visibility: %d policy/split/role cases passed\n", checks);
  return 0;
}
'''

if __name__ == "__main__":
    main()
