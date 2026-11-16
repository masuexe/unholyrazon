#!/usr/bin/env python3
"""Verify Razon 3 parity fixes using compiled C tests + DECORATE contracts.

Covers:
  1. Mercy rounds ("Prepare yourselves!" light-blue banner via UH_PrepareBannerColor)
  2. Spread-rune AirStrike sequential 3-meteor drops continuing after death
  3. Eden Damocles dropping as a persistent floor hazard upon Eden death

Run:  python3 tools/check_razon3_parity_contracts.py [--root PATH]
Exit: 0 clean, 1 failure, 2 usage/parse error.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_function(source: str, signature_prefix: str) -> str:
    start = source.index(signature_prefix)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                fn = source[start : idx + 1]
                fn = re.sub(r"\bfunction\s+", "", fn, count=1)
                return fn.replace("(void)", "(void)")
    raise RuntimeError(f"unterminated function: {signature_prefix}")


def extract_actor_block(source: str, actor_name: str) -> str:
    m = re.search(rf"(?im)^[ \t]*actor\s+{re.escape(actor_name)}\b", source)
    if not m:
        raise RuntimeError(f"missing actor {actor_name}")
    brace = source.index("{", m.end())
    depth = 0
    for idx in range(brace, len(source)):
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[m.start() : idx + 1]
    raise RuntimeError(f"unterminated actor {actor_name}")


def build_c_harness(root: Path) -> str:
    lifecycle = (root / "src/acs_source/unholy/uh_lifecycle.acs").read_text(encoding="utf-8")
    queries = (root / "src/acs_source/systems/tools/player_queries.acs").read_text(encoding="utf-8")
    eden = (root / "src/acs_source/classes/survivors/eden/eden_runtime.acs").read_text(encoding="utf-8")

    prepare_fn = extract_function(lifecycle, "function int UH_PrepareBannerColor(")
    connected_fn = extract_function(queries, "function bool UH_IsConnectedCombatSlot(")
    refresh_fn = extract_function(queries, "function int UH_RefreshTargetOwnerCore(")

    d_start = eden.index("#define EDEN_DAMOCLES_CLEANUP")
    hang_fn = extract_function(eden[d_start:], "function int EdenDamoclesHangStateCore(")
    defines = eden[d_start : eden.index("function int EdenDamoclesHangStateCore(")]

    return STUBS + "\n" + prepare_fn + "\n" + connected_fn + "\n" + refresh_fn + "\n" + defines + "\n" + hang_fn + "\n" + TESTS


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

typedef const char *str;
#define CR_YELLOW 10
#define CR_LIGHTBLUE 21
#define AAPTR_TARGET 2
#define APROP_Health 0

typedef struct Actor {
  int tid;
  struct Actor *target;
  int player_num;
  int is_dead;
  int health;
  char cls[64];
  int c577;
  int active_f;
  int spent_f;
} Actor;

int mercygiven = 0;
int in_game[64];
int spec_mode[64];
Actor *player_mo[64];
Actor actors[16];
int next_unique_tid = 20000;
int unique_tid_allocs = 0;
int set_pointer_calls = 0;
Actor *activator = NULL;

void reset_sim(void) {
  memset(in_game, 0, sizeof(in_game));
  memset(spec_mode, 0, sizeof(spec_mode));
  memset(player_mo, 0, sizeof(player_mo));
  memset(actors, 0, sizeof(actors));
  for (int i = 0; i < 16; i++) actors[i].player_num = -1;
  mercygiven = 0;
  next_unique_tid = 20000;
  unique_tid_allocs = 0;
  set_pointer_calls = 0;
  activator = NULL;
}

int ActivatorTID(void) { return activator ? activator->tid : 0; }
int UniqueTID(void) {
  unique_tid_allocs++;
  return next_unique_tid++;
}
Actor *find_by_tid(int tid) {
  if (tid == 0) return NULL;
  for (int i = 0; i < 16; i++) {
    if (actors[i].tid == tid) return &actors[i];
  }
  return NULL;
}
void Thing_ChangeTID(int oldtid, int newtid) {
  Actor *a = (oldtid == 0) ? activator : find_by_tid(oldtid);
  if (a) a->tid = newtid;
}
int SetActivator(int tid, ...) {
  return 0;
}
int set_activator1(int tid) {
  Actor *a = (tid == 0) ? activator : find_by_tid(tid);
  if (!a) return 0;
  activator = a;
  return 1;
}
int set_activator2(int tid, int ptr) {
  Actor *base = (tid == 0) ? activator : find_by_tid(tid);
  if (!base) return 0;
  if (ptr == AAPTR_TARGET) {
    if (!base->target) return 0;
    activator = base->target;
    return 1;
  }
  activator = base;
  return 1;
}
#define SETACT_N(_1, _2, NAME, ...) NAME
#define SetActivator(...) SETACT_N(__VA_ARGS__, set_activator2, set_activator1)(__VA_ARGS__)

int SetActivatorToPlayer(int pn) {
  if (pn < 0 || pn >= 64) return 0;
  if (!in_game[pn] && spec_mode[pn] == 0) return 0;
  if (!player_mo[pn]) return 0;
  activator = player_mo[pn];
  return 1;
}
int SetPointer(int ptr, int tid) {
  if (!activator || ptr != AAPTR_TARGET) return 0;
  activator->target = find_by_tid(tid);
  set_pointer_calls++;
  return activator->target != NULL;
}
int PlayerNumber(void) { return activator ? activator->player_num : -1; }
int PlayerInGame(int pn) { return (pn >= 0 && pn < 64) ? in_game[pn] : 0; }
int PlayerIsSpectator(int pn) { return (pn >= 0 && pn < 64) ? spec_mode[pn] : 0; }
int CheckActorClass(int tid, str cls) {
  Actor *a = (tid == 0) ? activator : find_by_tid(tid);
  return a && strcmp(a->cls, cls) == 0;
}
int GetActorProperty(int tid, int prop) {
  Actor *a = (tid == 0) ? activator : find_by_tid(tid);
  assert(prop == APROP_Health);
  return a ? a->health : 0;
}
int CheckInventory(str name) {
  if (!activator) return 0;
  if (strcmp(name, "IsDead") == 0) return activator->is_dead;
  if (strcmp(name, "C577Flag") == 0) return activator->c577;
  if (strcmp(name, "EdenDamoclesActive_F") == 0) return activator->active_f;
  if (strcmp(name, "EdenDamoclesSpent_F") == 0) return activator->spent_f;
  assert(0);
  return 0;
}
void GiveInventory(str name, int amt) {
  if (!activator) return;
  if (strcmp(name, "EdenDamoclesSpent_F") == 0) activator->spent_f += amt;
  else if (strcmp(name, "EdenDamoclesActive_F") == 0) activator->active_f += amt;
  else assert(0);
}
void TakeInventory(str name, int amt) {
  if (!activator) return;
  if (strcmp(name, "EdenDamoclesActive_F") == 0) {
    activator->active_f = (activator->active_f > amt) ? (activator->active_f - amt) : 0;
  } else {
    assert(0);
  }
}
int ACS_NamedExecuteWithResult(str name, int arg0) {
  if (strcmp(name, "uh_CheckTargetMatchesSlot") == 0) {
    Actor *saved = activator;
    int res = (arg0 > 0 && arg0 <= 64 && SetActivator(0, AAPTR_TARGET))
                ? (PlayerNumber() == arg0 - 1)
                : 0;
    activator = saved;
    return res;
  }
  assert(0);
  return 0;
}
'''

TESTS = r'''
int main(void) {
  // 1. Mercy prepare banner color
  reset_sim();
  mercygiven = 0;
  assert(UH_PrepareBannerColor() == CR_YELLOW);
  mercygiven = 1;
  assert(UH_PrepareBannerColor() == CR_LIGHTBLUE);

  // 2. Owner refresh helper across live, dead-spectator, and disconnected slots
  reset_sim();
  Actor *watcher = &actors[0];
  Actor *corpse = &actors[1];
  Actor *deadspec_mo = &actors[2];
  corpse->player_num = 3;
  deadspec_mo->player_num = 3;
  in_game[3] = 1;
  spec_mode[3] = 0;
  player_mo[3] = corpse;
  watcher->target = corpse;
  activator = watcher;
  assert(UH_RefreshTargetOwnerCore(4) == 1);
  assert(unique_tid_allocs == 0 && set_pointer_calls == 0);
  assert(watcher->tid == 0 && corpse->tid == 0);

  // Corpse detached on LMS dead-spectator transition: rebind without TID leaks
  in_game[3] = 0;
  spec_mode[3] = 2;
  player_mo[3] = deadspec_mo;
  watcher->target = NULL;
  activator = watcher;
  assert(UH_RefreshTargetOwnerCore(4) == 1);
  assert(watcher->target == deadspec_mo);
  assert(watcher->tid == 0 && deadspec_mo->tid == 0);

  // Voluntary spectator or disconnect must not rebind
  spec_mode[3] = 1;
  watcher->target = NULL;
  activator = watcher;
  assert(UH_RefreshTargetOwnerCore(4) == 0);
  assert(watcher->target == NULL);

  spec_mode[3] = 0;
  watcher->target = NULL;
  activator = watcher;
  assert(UH_RefreshTargetOwnerCore(4) == 0);
  assert(watcher->target == NULL);

  // 3. Eden Damocles hang / death-drop / cleanup state transitions
  reset_sim();
  Actor *sword = &actors[0];
  Actor *eden = &actors[1];
  Actor *spec_body = &actors[2];
  strcpy(eden->cls, "Eden");
  eden->player_num = 2;
  eden->health = 1000;
  eden->c577 = 1;
  eden->active_f = 1;
  in_game[2] = 1;
  player_mo[2] = eden;
  sword->target = eden;

  activator = sword;
  assert(EdenDamoclesHangStateCore(3) == EDEN_DAMOCLES_HANG);

  // Eden dies while holding active C577 -> drop and mark spent
  eden->is_dead = 1;
  eden->health = 0;
  activator = sword;
  assert(EdenDamoclesHangStateCore(3) == EDEN_DAMOCLES_DROP);
  assert(eden->active_f == 0 && eden->spent_f == 1);

  // Shiny Eden without IsDead flag yet (Health <= 0) -> drop
  reset_sim();
  sword = &actors[0];
  eden = &actors[1];
  strcpy(eden->cls, "EdenShiny");
  eden->player_num = 5;
  eden->health = 0;
  eden->is_dead = 0;
  eden->c577 = 1;
  eden->active_f = 1;
  in_game[5] = 1;
  sword->target = eden;
  activator = sword;
  assert(EdenDamoclesHangStateCore(6) == EDEN_DAMOCLES_DROP);
  assert(eden->spent_f == 1);

  // Same-tic detached dead-spectator pawn -> drop
  reset_sim();
  sword = &actors[0];
  spec_body = &actors[2];
  spec_body->player_num = 4;
  in_game[4] = 0;
  spec_mode[4] = 2;
  sword->target = NULL;
  activator = sword;
  assert(EdenDamoclesHangStateCore(5) == EDEN_DAMOCLES_DROP);

  // Live morph (e.g. Boss or strip cleanup) -> cleanup
  reset_sim();
  sword = &actors[0];
  eden = &actors[1];
  strcpy(eden->cls, "VoidWalkerBoss");
  eden->player_num = 1;
  eden->health = 4000;
  eden->c577 = 0;
  eden->active_f = 0;
  in_game[1] = 1;
  sword->target = eden;
  activator = sword;
  assert(EdenDamoclesHangStateCore(2) == EDEN_DAMOCLES_CLEANUP);

  // Voluntary spectator or disconnect -> cleanup
  reset_sim();
  sword = &actors[0];
  spec_mode[1] = 1;
  in_game[1] = 0;
  sword->target = NULL;
  activator = sword;
  assert(EdenDamoclesHangStateCore(2) == EDEN_DAMOCLES_CLEANUP);
  spec_mode[1] = 0;
  activator = sword;
  assert(EdenDamoclesHangStateCore(2) == EDEN_DAMOCLES_CLEANUP);

  printf("razon3 parity ACS C-harness checks passed\n");
  return 0;
}
'''


def check_decorate_and_lifecycle_sources(root: Path) -> list[str]:
    errors: list[str] = []

    # --- Mercy "Prepare yourselves!" banner contract ---
    lifecycle = (root / "src/acs_source/unholy/uh_lifecycle.acs").read_text(encoding="utf-8")
    prepare_lines = [
        line.strip()
        for line in lifecycle.splitlines()
        if "Prepare yourselves!" in line
    ]
    if len(prepare_lines) < 4:
        errors.append(
            f"expected at least 4 'Prepare yourselves!' banners in uh_lifecycle.acs (found {len(prepare_lines)})"
        )
    for line in prepare_lines:
        if "UH_PrepareBannerColor()" not in line:
            errors.append(f"'Prepare yourselves!' does not use UH_PrepareBannerColor(): {line}")
        if "CR_YELLOW" in line:
            errors.append(f"'Prepare yourselves!' hardcodes CR_YELLOW: {line}")
    if "else if (mercygiven)" not in lifecycle:
        errors.append("late-join countdown refresh loop must refresh Mercy 'Prepare yourselves!' banner")

    # --- AirStrike sequential spread + post-death continuation contract ---
    airstrike = (root / "src/actors/items/pandora/AirStrike.dec").read_text(encoding="utf-8")
    for actor_name in (
        "AirStrikeItem",
        "AirStrikeSpread_H",
        "AirStrikeSpreadSilent_H",
        "AirStrikeSpawnRNG_P",
        "AirStrikeSound",
        "AirStrikeTarget",
        "AirStrikeTarget2",
    ):
        try:
            extract_actor_block(airstrike, actor_name)
        except RuntimeError as exc:
            errors.append(f"AirStrike.dec: {exc}")

    if len(errors) == 0:
        item_blk = extract_actor_block(airstrike, "AirStrikeItem")
        if 'A_JumpIfInventory("PlayerPropertySpread", 1, "UseX_Spread")' not in item_blk:
            errors.append("AirStrikeItem::UseX must jump to UseX_Spread on PlayerPropertySpread")
        if 'A_JumpIfInventory("PlayerPropertySpread", 1, "UseX_SilentSpread")' not in item_blk:
            errors.append("AirStrikeItem::UseX_Silent must jump to UseX_SilentSpread on PlayerPropertySpread")
        if 'A_SpawnItemEx("AirStrikeSpread_H"' not in item_blk:
            errors.append("AirStrikeItem must spawn AirStrikeSpread_H for Spread Rune")
        if 'A_SpawnItemEx("AirStrikeSpreadSilent_H"' not in item_blk:
            errors.append("AirStrikeItem must spawn AirStrikeSpreadSilent_H for silent Spread use")

        rng_blk = extract_actor_block(airstrike, "AirStrikeSpawnRNG_P")
        if "AirStrikeTarget_Spread" in rng_blk or "AirStrikeTarget2_Spread" in rng_blk:
            errors.append("AirStrikeSpawnRNG_P must not spawn simultaneous *_Spread targets")

        spread_blk = extract_actor_block(airstrike, "AirStrikeSpread_H")
        for token in (
            'CallACS("uh_GetTargetOwnerSlot")',
            'ACS_NamedExecuteWithResult("uh_RefreshTargetOwnerBySlot", user_owner)',
            'A_SpawnItemEx("AirStrikeTarget"',
            'A_SpawnItemEx("AirStrikeTarget2"',
            'A_SetUserVar("user_wave", user_wave + 1)',
            'A_JumpIf(user_wave >= 3, "Finish")',
            'A_SetUserVar("user_tics", 70)',
            'CallACS("uh_PointerExists", AAPTR_TARGET)',
            'A_SetUserVar("user_dead", 1)',
            'A_Warp(AAPTR_TARGET, 0, 0, 0, 0, WARPF_NOCHECKPOSITION)',
            'A_JumpIf(args[0] != 0, "DropTarget")',
        ):
            if token not in spread_blk:
                errors.append(f"AirStrikeSpread_H missing required logic: {token}")

        silent_blk = extract_actor_block(airstrike, "AirStrikeSpreadSilent_H")
        if not re.search(r"(?m)^\s*Args\s+1\b", silent_blk):
            errors.append("AirStrikeSpreadSilent_H must set Args 1 to suppress warning siren")

        sound_blk = extract_actor_block(airstrike, "AirStrikeSound")
        for token in ("Spawn:", "Spawn2:", 'CallACS("uh_PointerExists", 2)', "HoldPos:"):
            if token not in sound_blk:
                errors.append(f"AirStrikeSound missing {token} to survive owner death")

        t1_blk = extract_actor_block(airstrike, "AirStrikeTarget")
        t2_blk = extract_actor_block(airstrike, "AirStrikeTarget2")
        if 'CallACS("uh_GetTargetOwnerSlot")' not in t1_blk:
            errors.append("AirStrikeTarget::Spawn must capture user_owner")
        for label, blk in (("AirStrikeTarget", t1_blk), ("AirStrikeTarget2", t2_blk)):
            if 'ACS_NamedExecuteWithResult("uh_RefreshTargetOwnerBySlot", user_owner)' not in blk:
                errors.append(f"{label}::Death must call uh_RefreshTargetOwnerBySlot before meteor spawn")

    # --- Eden Damocles death-drop contract ---
    damocles = (root / "src/actors/classes/survivors/eden/main_items/C577_Damocles.dec").read_text(encoding="utf-8")
    ed_blk = extract_actor_block(damocles, "EdenDamocles")
    for token in (
        'CallACS("uh_GetTargetOwnerSlot")',
        'CallACS("rz_EdenDamoclesHangState", user_owner)',
        'A_JumpIf(user_hangstate == 2, "Drop")',
        'A_JumpIf(user_hangstate == 0, "Cleanup")',
    ):
        if token not in ed_blk:
            errors.append(f"EdenDamocles missing required hang/drop dispatch: {token}")

    refresh_count = ed_blk.count('ACS_NamedExecuteWithResult("uh_RefreshTargetOwnerBySlot", user_owner)')
    if refresh_count < 2:
        errors.append("EdenDamocles must call uh_RefreshTargetOwnerBySlot in both Falling and GroundHazard")

    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv[1:])
    root = args.root.resolve()

    errors = check_decorate_and_lifecycle_sources(root)
    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1

    code = build_c_harness(root)
    with tempfile.TemporaryDirectory(prefix="uh-razon3-parity-") as tmpdir:
        src_path = Path(tmpdir) / "test.c"
        bin_path = Path(tmpdir) / "test"
        src_path.write_text(code, encoding="utf-8")
        subprocess.run(
            ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", str(src_path), "-o", str(bin_path)],
            check=True,
        )
        subprocess.run([str(bin_path)], check=True)

    print("ok: Razon 3 parity contracts hold (Mercy Prepare color, post-death Spread AirStrike, Eden Damocles death drop)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
