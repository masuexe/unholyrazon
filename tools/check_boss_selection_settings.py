#!/usr/bin/env python3
"""Exercise actual integer-only boss-selection ACS with deterministic C stubs.

ACC checks syntax separately. This test does not simulate engine networking,
map loading, or morphing. Reuses the existing ACS-to-C logic-test translator.
"""
from pathlib import Path
import re
import subprocess
import tempfile

from check_bonus_event_settings import function, translate

ROOT = Path(__file__).resolve().parents[1]

STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef const char *str;
#define UHBOSS_FAIL -9999
#define UHBOSS_POOL_COMMON 1
#define UHBOSS_POOL_RARE 2
#define UHBOSS_POOL_SPECIAL 3
#define UHBOSS_POOL_ULTRA 4
#define UHBOSS_POOL_EX 5
#define MAX_BOSSES 5
#define UH_BOSSROUND_MAX (MAX_BOSSES * 2)
int uh_bosslastlineup[6], uh_bosspreviouslineup[6];
int uh_bossroundpicked[UH_BOSSROUND_MAX], uh_bossroundpickedcount;
int pools[6][8], sizes[6], counts[64];
bool shadowtricksarr[5];
int rarebosschance;
const char *names[] = {"uh_sv_bossselectmode", "uh_sv_bossavoidrepeat",
 "uh_sv_bossavoidduplicates", "uh_sv_bossrarelimit", "uh_sv_bossshadowchance",
 "uh_sv_bossfullultrachance", "uh_sv_bossfullspecialchance",
 "uh_sv_bossfullexchance", "uh_sv_bossfullrarechance"};
int defaults[] = {0,0,0,25,10,5,1,15,30}, settings[9];
int GetCVar(str name) {
 for(int i=0;i<9;i++) if(!strcmp(name,names[i])) return settings[i];
 assert(!"unexpected CVAR"); return 0;
}
int GetBossPoolCount(int pool) { return sizes[pool]; }
int GetBossPoolId(int pool,int index) { return pools[pool][index]; }
bool IsBossDefined(int id) { return id>=-1 && id<32; }
int GetBossPickCount(int id) { return IsBossDefined(id)?counts[id+1]:-1; }
void IncrementBossPickCount(int id) { counts[id+1]++; }
int rolls[64], roll_count, roll_index, random_calls;
int acs_random(int low,int high) {
 assert(low<=high); random_calls++;
 int value=roll_index<roll_count?rolls[roll_index++]:high;
 assert(value>=low && value<=high); return value;
}
void reset(void) {
 memcpy(settings,defaults,sizeof(settings));
 memset(sizes,0,sizeof(sizes)); memset(counts,0,sizeof(counts));
 memset(shadowtricksarr,0,sizeof(shadowtricksarr));
 memset(uh_bosslastlineup,0,sizeof(uh_bosslastlineup));
 memset(uh_bosspreviouslineup,0,sizeof(uh_bosspreviouslineup));
 uh_bossroundpickedcount=0; rarebosschance=15;
 roll_count=roll_index=random_calls=0;
 pools[1][0]=0; pools[1][1]=1; pools[1][2]=-1; sizes[1]=3;
 pools[2][0]=2; sizes[2]=1;
}
'''

TESTS = r'''
int main(void) {
 reset();
 // Default fairness includes signed custom ids and the soft round delta.
 counts[1]=2; counts[2]=1;
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==-1);
 UH_BossRoundRecord(-1);
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==1);
 assert(PickLeastSeenBossFromPool(1,-1)==1);
 // Equal-weight mode ignores history and soft deltas. A tie replacement roll
 // picks a highly-used boss that least-seen mode would exclude.
 reset(); counts[2]=20; counts[0]=30; UH_BossRoundRecord(-1);
 settings[0]=1; rolls[0]=1; rolls[1]=1; roll_count=2;
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==-1);
 settings[0]=-8; assert(BossSelectionSetting(names[0],1)==0);
 settings[0]=9; assert(BossSelectionSetting(names[0],1)==1);
 // Final committed identities, including custom bosses, survive round reset;
 // new commits do not change the previous-round snapshot.
 reset(); CommitBossHistorySlot(-1); CommitBossHistorySlot(0);
 CommitBossHistorySlot(UHBOSS_FAIL); UH_BossRoundReset();
 assert(uh_bosspreviouslineup[0]==2 && uh_bosslastlineup[0]==0);
 assert(BossWasInPreviousLineup(-1) && BossWasInPreviousLineup(0));
 CommitBossHistorySlot(1); assert(!BossWasInPreviousLineup(1));
 settings[1]=1; assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==1);
 UH_BossRoundReset(); assert(BossWasInPreviousLineup(1));
 assert(!BossWasInPreviousLineup(-1));
 // Hard exclusions precede fairness; empty optional pools retry, but the
 // caller's mandatory exclusion is never relaxed.
 reset(); settings[2]=1; UH_BossRoundRecord(0);
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==1);
 UH_BossRoundRecord(1); UH_BossRoundRecord(-1);
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==0);
 sizes[1]=1;
 assert(PickLeastSeenBossFromPool(1,0)==UHBOSS_FAIL);
 sizes[1]=0; assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==UHBOSS_FAIL);
 // A five-Shadow round can reserve initial and final bodies without dropping
 // the last reveal, and the bounded record buffer rejects excess writes.
 reset();
 for(int i=0;i<10;i++) UH_BossRoundRecord(i);
 UH_BossRoundRecord(30);
 assert(uh_bossroundpickedcount==10 && UH_BossRoundSeen(9)==1);
 assert(UH_BossRoundSeen(30)==0);
 // Default pity sequence: miss increments, hit resets; a Shadow hit uses
 // Common as its fake body and flags only the chosen slot.
 reset(); sizes[1]=1; rolls[0]=15; roll_count=1;
 assert(PickStandardBoss(0)==0 && rarebosschance==16 && random_calls==1);
 rolls[1]=25; rolls[2]=11; roll_count=3;
 assert(PickStandardBoss(1)==2 && rarebosschance==0);
 rolls[3]=25; rolls[4]=10; roll_count=5;
 assert(PickStandardBoss(2)==0 && shadowtricksarr[2]);
 assert(!shadowtricksarr[0] && !shadowtricksarr[1]);
 // Disabled promotion pauses existing progress. Re-enabling/lowering the
 // ceiling clamps that progress, so reversed Random bounds never occur.
 reset(); sizes[1]=1; settings[3]=0;
 assert(PickStandardBoss(0)==0 && rarebosschance==15 && random_calls==0);
 settings[3]=2; settings[4]=0;
 assert(PickStandardBoss(0)==2 && rarebosschance==0);
 settings[3]=200; assert(BossSelectionSetting(names[3],100)==100);
 rarebosschance=-5; rolls[0]=0; roll_count=1; roll_index=0;
 assert(PickStandardBoss(0)==0 && rarebosschance==1);
 settings[3]=-1; assert(BossSelectionSetting(names[3],100)==0);
 // Sequential tier rolls retain the legacy order, probabilities and number
 // of RNG calls with defaults (boundary rolls shown explicitly).
 reset(); rolls[0]=5; roll_count=1;
 assert(RollFullBossPool()==4 && random_calls==1);
 reset(); rolls[0]=6; rolls[1]=1; roll_count=2;
 assert(RollFullBossPool()==3 && random_calls==2);
 reset(); rolls[0]=6; rolls[1]=2; rolls[2]=15; roll_count=3;
 assert(RollFullBossPool()==5 && random_calls==3);
 reset(); rolls[0]=6; rolls[1]=2; rolls[2]=16; rolls[3]=30; roll_count=4;
 assert(RollFullBossPool()==2 && random_calls==4);
 reset(); assert(RollFullBossPool()==1 && random_calls==4);
 // Every tier can be disabled or made certain. Common and a defined boss 0
 // remain the legacy fallbacks when the drawn tier has no candidates.
 for(int tier=5;tier<=8;tier++) {
   reset(); for(int i=5;i<=8;i++) settings[i]=0;
   settings[tier]=100;
   int expected[]={4,3,5,2}; assert(RollFullBossPool()==expected[tier-5]);
 }
 reset(); for(int i=5;i<=8;i++) settings[i]=-4;
 assert(RollFullBossPool()==1);
 settings[5]=200; assert(RollFullBossPool()==4);
 sizes[1]=1; assert(TrueRandomBoss()==0);
 sizes[1]=0; assert(TrueRandomBoss()==0);
 puts("PASS: boss selection defaults, strategies, signed identities, lineup snapshots, repeat fallback, pity pause/clamps and conditional tier probabilities");
 return 0;
}
'''


def main():
    helpers = (ROOT / "src/acs_source/unholy/uh_boss_selection_helpers.acs").read_text()
    round_helpers = (ROOT / "src/acs_source/unholy/uh_round_helpers.acs").read_text()
    names = ("CommitBossHistorySlot", "UH_BossRoundReset", "UH_BossRoundRecord",
             "UH_BossRoundSeen", "BossSelectionSetting", "BossWasInPreviousLineup",
             "PickBossPoolPass", "PickLeastSeenBossFromPool", "PickStandardBoss",
             "RollFullBossPool", "TrueRandomBoss")
    acs = function(round_helpers, "RandomPercent") + "\n" + "\n".join(
        function(helpers, name) for name in names)
    # Remove logging only; selection, state updates and RNG calls are intact.
    acs = re.sub(r"UH_Log\(.*?\);", "", acs, flags=re.S)
    cvars = (ROOT / "src/CVARINFO.server").read_text()
    settings = re.findall(r'server (?:int|bool) (uh_sv_boss(?:selectmode|avoidrepeat|avoidduplicates|rarelimit|shadowchance|full\w+chance)) = (\w+);', cvars)
    assert len(settings) == 9, settings
    expected = ("0", "false", "false", "25", "10", "5", "1", "15", "30")
    assert tuple(value for _, value in settings) == expected, settings
    with tempfile.TemporaryDirectory(prefix="uh-boss-settings-") as tmp:
        path = Path(tmp)
        (path / "test.c").write_text(STUBS + translate(acs) + TESTS)
        subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


if __name__ == "__main__":
    main()
