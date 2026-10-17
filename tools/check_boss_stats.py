#!/usr/bin/env python3
"""Check Boss win-rate stats wiring and execute its integer-only ACS logic.

ACC compilation checks syntax separately. This test does not simulate engine
networking, map loading, settlement timing, or the special wipe scripts.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

from check_bonus_event_settings import function, translate

ROOT = Path(__file__).resolve().parents[1]


def require(text, needle, label):
    assert needle in text, f"missing {label}: {needle!r}"


def static_checks():
    definitions = (ROOT / "src/acs_source/unholy/uh_def.acs").read_text()
    expected = {
        130: "uh_bossstatswins",
        131: "uh_bossstatswinscustom",
        132: "uh_bossstatslosses",
        133: "uh_bossstatslossescustom",
        134: "uh_bossstatsrounds",
        135: "uh_bossstatsbosswins",
        136: "uh_bossstatsrecorded",
        137: "uh_bossstatslastrequest",
    }
    for slot, name in expected.items():
        require(definitions, f"{slot}:{name}", f"world slot {slot}")

    include = (ROOT / "src/acs_source/unholy/unholy.acs").read_text()
    require(include, '#include "uh_boss_stats.acs"', "stats include in unholy")

    stats = (ROOT / "src/acs_source/unholy/uh_boss_stats.acs").read_text()
    require(stats, 'script "uh_BossStats" (int mode, int id) NET',
            "player-callable NET query script")
    require(stats, "UH_BossStatsRecordRound", "record entry")
    require(stats, "UH_BossStatsReset", "reset entry")
    code_only = "\n".join(line.split("//")[0] for line in stats.splitlines())
    assert "uh_bosscustomcount" not in code_only, (
        "do not read uhdt's map variable from unholy; it consumes a map slot")

    # Result accounting must happen only at committed endings.
    lifecycle = (ROOT / "src/acs_source/unholy/uh_lifecycle.acs").read_text()
    assert lifecycle.count("UH_BossStatsRecordRound(false);") == 1
    assert lifecycle.count("UH_BossStatsRecordRound(true);") == 1
    arena = (ROOT / "src/acs_source/unholy/uh_arena_fx.acs").read_text()
    assert arena.count("UH_BossStatsRecordRound(false);") == 1
    mujica = (ROOT / "src/acs_source/unholy/sakiko_mujica.acs").read_text()
    assert mujica.count("UH_BossStatsRecordRound(false);") == 1

    selection = (ROOT / "src/acs_source/unholy/uh_bossselect.acs").read_text()
    require(selection, "uh_bossstatsrecorded = false;", "per-round guard reset")
    require(selection, "uh_bossstatslastrequest = 0;", "query cooldown reset")

    config = (ROOT / "src/acs_source/unholy/uh_boss_config.acs").read_text()
    require(config, 'StrICmp(op, "statsreset")', "host reset operation")

    keyconf = (ROOT / "src/KEYCONF").read_text()
    require(keyconf, 'alias uh_bossstats "pukename uh_BossStats"',
            "player alias")
    require(keyconf, "statsreset:", "host reset alias")

    assert (ROOT / "docs/boss-stats.md").exists(), "missing docs/boss-stats.md"


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
typedef const char *str;
#define UH_MAX_VANILLA_BOSS 8
#define UH_MAX_CUSTOM_BOSS 4
#define MAX_BOSSES 5
#define UH_LOG_DEBUG 0
#define UH_LOG_INFO 1
int uh_bossstatswins[8], uh_bossstatslosses[8];
int uh_bossstatswinscustom[4], uh_bossstatslossescustom[4];
int uh_bossstatsrounds, uh_bossstatsbosswins, uh_bossstatslastrequest;
bool uh_bossstatsrecorded;
bool isbonuseventactive, bonuseventended, versusfightevent;
int uh_bosslastlineup[6];
str number(int n) { char b[32]; snprintf(b,sizeof(b),"%d",n); return strdup(b); }
str concat(int count, ...) {
  va_list ap; size_t size = 1; va_start(ap,count);
  for(int i=0;i<count;i++) size += strlen(va_arg(ap,str));
  va_end(ap); char *s = calloc(size,1); va_start(ap,count);
  for(int i=0;i<count;i++) strcat(s,va_arg(ap,str));
  va_end(ap); return s;
}
void log_text(str s) { (void)s; }
void UH_Log(int level, str msg) { (void)level; (void)msg; }
bool IsBossDefined(int id) { return (id >= 0 && id < 8) || (id <= -1 && id > -5); }
str GetBossName(int id) { static char b[32]; snprintf(b,sizeof(b),"Boss%d",id); return b; }
int UH_BossCustomIndex(int id) { return -1 - id; }
'''

TESTS = r'''
void reset_state(void) {
  memset(uh_bossstatswins,0,sizeof(uh_bossstatswins));
  memset(uh_bossstatslosses,0,sizeof(uh_bossstatslosses));
  memset(uh_bossstatswinscustom,0,sizeof(uh_bossstatswinscustom));
  memset(uh_bossstatslossescustom,0,sizeof(uh_bossstatslossescustom));
  memset(uh_bosslastlineup,0,sizeof(uh_bosslastlineup));
  uh_bossstatsrounds = uh_bossstatsbosswins = 0;
  uh_bossstatsrecorded = false;
  isbonuseventactive = bonuseventended = versusfightevent = false;
}

void test_rate(void) {
  assert(!strcmp(UH_BS_RateText(0,0), "-"));
  assert(!strcmp(UH_BS_RateText(1,2), "50.0%"));
  assert(!strcmp(UH_BS_RateText(2,3), "66.6%"));
  assert(!strcmp(UH_BS_RateText(3,3), "100.0%"));
}

void test_record(void) {
  reset_state();
  // Ordinary Boss-side win with a duplicated combo member: each distinct id once.
  uh_bosslastlineup[0] = 3;
  uh_bosslastlineup[1] = 1;
  uh_bosslastlineup[2] = 2;
  uh_bosslastlineup[3] = 1;
  UH_BossStatsRecordRound(false);
  assert(uh_bossstatswins[1] == 1);
  assert(uh_bossstatswins[2] == 1);
  assert(uh_bossstatslosses[1] == 0);
  assert(uh_bossstatsrounds == 1);
  assert(uh_bossstatsbosswins == 1);
  assert(uh_bossstatsrecorded);

  // One record per round even if another ending path calls again.
  UH_BossStatsRecordRound(false);
  assert(uh_bossstatsrounds == 1);
  assert(uh_bossstatswins[1] == 1);

  // Survivor win: vanilla + custom both get a loss.
  uh_bossstatsrecorded = false;
  uh_bosslastlineup[0] = 2;
  uh_bosslastlineup[1] = -1;
  uh_bosslastlineup[2] = 3;
  UH_BossStatsRecordRound(true);
  assert(uh_bossstatslossescustom[0] == 1);
  assert(uh_bossstatslosses[3] == 1);
  assert(uh_bossstatswinscustom[0] == 0);
  assert(uh_bossstatsrounds == 2);
  assert(uh_bossstatsbosswins == 1);

  // Bonus and versus rounds are excluded.
  uh_bossstatsrecorded = false;
  uh_bosslastlineup[0] = 1;
  uh_bosslastlineup[1] = 4;
  isbonuseventactive = true;
  UH_BossStatsRecordRound(false);
  assert(!uh_bossstatsrecorded);
  assert(uh_bossstatswins[4] == 0);
  assert(uh_bossstatsrounds == 2);
  isbonuseventactive = false;
  bonuseventended = true;
  UH_BossStatsRecordRound(false);
  assert(!uh_bossstatsrecorded);
  bonuseventended = false;
  versusfightevent = true;
  UH_BossStatsRecordRound(false);
  assert(!uh_bossstatsrecorded);
  versusfightevent = false;

  // Empty line-up records nothing.
  uh_bosslastlineup[0] = 0;
  UH_BossStatsRecordRound(false);
  assert(!uh_bossstatsrecorded);
  assert(uh_bossstatsrounds == 2);

  // Reset clears counters and the round guard, but not the line-up snapshot.
  uh_bosslastlineup[0] = 1;
  uh_bosslastlineup[1] = 1;
  UH_BossStatsReset();
  assert(uh_bossstatswins[1] == 0);
  assert(uh_bossstatslossescustom[0] == 0);
  assert(uh_bossstatsrounds == 0);
  assert(uh_bossstatsbosswins == 0);
  assert(!uh_bossstatsrecorded);
  assert(uh_bosslastlineup[0] == 1);
}

int main(void) {
  test_rate();
  test_record();
  puts("boss stats logic OK");
  return 0;
}
'''


def logic_test():
    source = (ROOT / "src/acs_source/unholy/uh_boss_stats.acs").read_text()
    names = ("UH_BS_Wins", "UH_BS_Losses", "UH_BS_AddWin", "UH_BS_AddLoss",
             "UH_BS_RateText", "UH_BossStatsReset", "UH_BossStatsRecordRound")
    parts = [function(source, name) for name in names]
    code = STUBS + translate("\n".join(parts)) + TESTS
    with tempfile.TemporaryDirectory(prefix="uh-bossstats-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(code)
        subprocess.run(["cc", "-std=c99", "-D_GNU_SOURCE", "-Wall", "-Wextra",
                        "-Werror", str(path / "test.c"), "-o", str(path / "test")],
                       check=True)
        subprocess.run([str(path / "test")], check=True)


def main():
    static_checks()
    logic_test()
    print("boss stats checks OK")


if __name__ == "__main__":
    main()
