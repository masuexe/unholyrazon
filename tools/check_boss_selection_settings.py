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
#include <stdlib.h>
#include <stdarg.h>
typedef const char *str;
#define UHBOSS_FAIL -9999
#define UHBOSS_POOL_COMMON 1
#define UHBOSS_POOL_RARE 2
#define UHBOSS_POOL_SPECIAL 3
#define UHBOSS_POOL_ULTRA 4
#define UHBOSS_POOL_EX 5
#define MAX_BOSSES 5
#define UH_BR_MODE 0
#define UH_BR_WEIGHT 1
#define UH_BR_MIN 2
#define UH_BR_MAX 3
#define UH_BR_DISABLED 0
#define UH_BR_FORCED 1
#define UH_BR_RANDOM 2
#define UHBOSS_POOL_NONE 0
#define UHBOSS_FORCE_TRUE_RANDOM -666
#define BOSSDATA_NUM 0
#define AAPTR_NULL 0
#define ShowMeTheRCON(...) ((void)0)
#define UH_BOSSROUND_MAX (MAX_BOSSES * 2)
int uh_bosslastlineup[6], uh_bosspreviouslineup[6];
int uh_bossroundpicked[UH_BOSSROUND_MAX], uh_bossroundpickedcount;
int pools[6][8], sizes[6], counts[64];
bool shadowtricksarr[5];
int rarebosschance;
int overrides[33][4], enabled[33], players=8, forced_limits;
int bossdataarr[5][1], multibosscheck, requests[5], exit_requests;
bool shadowfakeoutactive, shadowrevealactive, gameover, bosschoiceconfirmed, bosschoicereassign;
int TrueRandomBoss(void);
bool CheckBossList(int id);
str number(int value) { char s[32]; snprintf(s,sizeof(s),"%d",value); return strdup(s); }
str concat(int count,...) {
 va_list ap; size_t size=1; va_start(ap,count);
 for(int i=0;i<count;i++) size+=strlen(va_arg(ap,str));
 va_end(ap); char *s=calloc(size,1); va_start(ap,count);
 for(int i=0;i<count;i++) strcat(s,va_arg(ap,str));
 va_end(ap); return s;
}
int PlayerCount(void) { return players; }
void ResetBossComboState(void) {}
void SetActivator(int a,int b) { (void)a; (void)b; }
void SetPlayerProperty(int a,int b,int c) { assert(a==1 && b==0 && c==4); }
void ACS_NamedExecute(str name,int map,int delay) {
 assert(!strcmp(name,"ub_ExitFinishedRound") && map==0 && delay==105); exit_requests++;
}
void ACS_NamedExecuteWithResult(str name) { assert(!strcmp(name,"uh_RefreshPostRoundFF")); }
const char *names[] = {"uh_sv_bossselectmode", "uh_sv_bossavoidrepeat",
 "uh_sv_bossavoidduplicates", "uh_sv_bossrarelimit", "uh_sv_bossshadowchance",
 "uh_sv_bossfullultrachance", "uh_sv_bossfullspecialchance",
 "uh_sv_bossfullexchance", "uh_sv_bossfullrarechance"};
int defaults[] = {0,0,0,25,10,5,1,15,30}, settings[9];
int multiboss_thresholds[] = {6,9,12,15};
int GetCVar(str name) {
 if(!strncmp(name,"uh_sv_multiboss_minplayers",26)) return multiboss_thresholds[atoi(name+26)-2];
 if(!strcmp(name,"uh_sv_bossforcedplayerlimits")) return forced_limits;
 if(!strncmp(name,"uh_sv_forcedboss",16)) return requests[atoi(name+16)-1];
 for(int i=0;i<9;i++) if(!strcmp(name,names[i])) return settings[i];
 assert(!"unexpected CVAR"); return 0;
}
void SetCVar(str name,int value) { assert(!strncmp(name,"uh_sv_forcedboss",16)); requests[atoi(name+16)-1]=value; }
int GetBossPoolCount(int pool) { return sizes[pool]; }
int GetBossPoolId(int pool,int index) { return pools[pool][index]; }
bool IsBossDefined(int id) { return id>=-1 && id<32; }
bool IsBossEnabled(int id) { return IsBossDefined(id) && enabled[id+1]; }
str GetBossActor(int id) {
 assert(IsBossDefined(id)); static char actors[33][12];
 snprintf(actors[id+1],sizeof(actors[0]),"%d",id); return actors[id+1];
}
int GetBossRarity(int id) {
 for(int pool=1;pool<6;pool++) for(int i=0;i<sizes[pool];i++) if(pools[pool][i]==id) return pool;
 return UHBOSS_POOL_NONE;
}
int UH_BR_Get(str actor,int field) { return overrides[atoi(actor)+1][field]; }
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
 for(int i=0;i<33;i++) { enabled[i]=1; for(int f=0;f<4;f++) overrides[i][f]=-1; }
 for(int i=0;i<5;i++) requests[i]=UHBOSS_FAIL;
 forced_limits=0; players=8; exit_requests=0; multibosscheck=1;
 gameover=bosschoiceconfirmed=bosschoicereassign=shadowfakeoutactive=shadowrevealactive=false;
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
 // Every Razon3 default threshold keeps the current uniform draw range.
 for(int p=0;p<=64;p++) {
   int limit=p>=15?5:p>=12?4:p>=9?3:p>=6?2:1;
   roll_count=0;
   assert(AutoBossCountForPlayers(p)==limit);
   rolls[0]=1; roll_count=1; roll_index=0;
   assert(AutoBossCountForPlayers(p)==1);
 }
 roll_count=0;
 // Host can unlock three bosses at ten players; changes persist across draws.
 multiboss_thresholds[1]=10;
 assert(AutoBossCountForPlayers(9)==2);
 assert(AutoBossCountForPlayers(10)==3);
 assert(AutoBossCountForPlayers(10)==3);
 // Zero/negative disables that tier and higher, even if their gates are met.
 multiboss_thresholds[1]=0;
 multiboss_thresholds[2]=10;
 assert(AutoBossCountForPlayers(10)==2);
 assert(AutoBossCountForPlayers(64)==2);
 multiboss_thresholds[1]=-1;
 assert(AutoBossCountForPlayers(64)==2);
 // Out-of-order thresholds cannot skip a lower tier; oversized values clamp.
 multiboss_thresholds[0]=999; multiboss_thresholds[1]=1;
 assert(AutoBossCountForPlayers(63)==1);
 assert(AutoBossCountForPlayers(64)==5);
 multiboss_thresholds[0]=0;
 assert(AutoBossCountForPlayers(64)==1);
 multiboss_thresholds[0]=6; multiboss_thresholds[1]=9; multiboss_thresholds[2]=12;
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
 sizes[1]=0; assert(TrueRandomBoss()==UHBOSS_FAIL);
 // Disabled/forced-only rows cannot leak through either random mode or an
 // empty-tier Common fallback. Registry-disabled rows stay unavailable.
 reset(); settings[3]=0;
 overrides[1][UH_BR_MODE]=UH_BR_DISABLED;
 overrides[2][UH_BR_MODE]=UH_BR_FORCED;
 assert(PickStandardBoss(0)==-1);
 overrides[0][UH_BR_MODE]=UH_BR_DISABLED;
 assert(PickStandardBoss(0)==UHBOSS_FAIL);
 assert(!SetUpBossSelection_Func());
 assert(PickBossPoolPass(1,UHBOSS_FAIL,false)==UHBOSS_FAIL);
 settings[5]=100; assert(TrueRandomBoss()==UHBOSS_FAIL);
 overrides[1][UH_BR_MODE]=UH_BR_RANDOM; enabled[1]=0;
 assert(!CanPickSpecifiedBoss(0) && !CanPickRandomBoss(0,8));
 // Player ranges are inclusive and mandatory for random draws. Specified
 // requests bypass only player bounds by default, never disabled mode.
 reset(); sizes[1]=1; overrides[1][UH_BR_MIN]=8; overrides[1][UH_BR_MAX]=12;
 assert(CanPickRandomBoss(0,8) && CanPickRandomBoss(0,12));
 assert(!CanPickRandomBoss(0,7) && !CanPickRandomBoss(0,13));
 players=7; requests[0]=0;
 assert(ConfiguredForceBossChange("uh_sv_forcedboss1",false)==0 && requests[0]==UHBOSS_FAIL);
 forced_limits=1; requests[0]=0;
 assert(ConfiguredForceBossChange("uh_sv_forcedboss1",false)==UHBOSS_FAIL && requests[0]==UHBOSS_FAIL);
 forced_limits=0; overrides[1][UH_BR_MODE]=UH_BR_DISABLED; requests[0]=0;
 assert(ConfiguredForceBossChange("uh_sv_forcedboss1",false)==UHBOSS_FAIL);
 // Combo's legacy explicit-id resolver is deliberately independent.
 requests[0]=0; assert(ForceBossChange("uh_sv_forcedboss1",false)==0);
 // Custom signed ids use the same policy, and forcing true-random still has
 // to satisfy random player limits even when explicit-id limits are off.
 reset(); overrides[0][UH_BR_MODE]=UH_BR_FORCED; requests[0]=-1;
 assert(ConfiguredForceBossChange("uh_sv_forcedboss1",false)==-1);
 assert(!CanPickRandomBoss(-1,8) && CanPickSpecifiedBoss(-1));
 for(int id=-1;id<=2;id++) overrides[id+1][UH_BR_MIN]=9;
 requests[0]=UHBOSS_FORCE_TRUE_RANDOM;
 assert(ConfiguredForceBossChange("uh_sv_forcedboss1",false)==UHBOSS_FAIL);
 // A random override cannot promote a registry row that has no pool.
 overrides[4][UH_BR_MODE]=UH_BR_RANDOM;
 assert(!CanPickRandomBoss(3,8));
 // Winner cards are specified choices: they allow forced-only rows, filter
 // disabled rows, and obey the configured specified-player policy.
 reset(); overrides[1][UH_BR_MODE]=UH_BR_DISABLED;
 overrides[2][UH_BR_MODE]=UH_BR_FORCED; overrides[0][UH_BR_MIN]=9; forced_limits=1;
 assert(PickBonusBossOption(1,UHBOSS_FAIL,UHBOSS_FAIL)==1);
 assert(PickBonusBossOption(1,1,UHBOSS_FAIL)==UHBOSS_FAIL);
 forced_limits=0; assert(PickBonusBossOption(1,1,UHBOSS_FAIL)==-1);
 // Both strategies respect weights; the minority of minimum-count bosses
 // wins only its share. A higher appearance count is excluded in mode 0.
 reset(); sizes[1]=2; overrides[1][UH_BR_WEIGHT]=1; overrides[2][UH_BR_WEIGHT]=3;
 int frequency[2]={0,0};
 for(int roll=1;roll<=4;roll++) {
   rolls[0]=roll; roll_count=1; roll_index=0;
   int id=PickLeastSeenBossFromPool(1,UHBOSS_FAIL); assert(id==0 || id==1); frequency[id]++;
 }
 assert(frequency[0]==1 && frequency[1]==3);
 counts[2]=20; roll_count=0;
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==0);
 settings[0]=1; rolls[0]=3; roll_count=1; roll_index=0;
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==1);
 // Weight totals remain in range at the per-boss maximum, and player bounds
 // do not relax when avoiding a previous/duplicate boss exhausts the pool.
 reset(); sizes[1]=2; overrides[1][UH_BR_WEIGHT]=overrides[2][UH_BR_WEIGHT]=1000000;
 rolls[0]=1000001; roll_count=1; assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==0);
 overrides[1][UH_BR_MIN]=overrides[2][UH_BR_MIN]=9; settings[1]=settings[2]=1;
 assert(PickLeastSeenBossFromPool(1,UHBOSS_FAIL)==UHBOSS_FAIL);
 // No-candidate termination is idempotent, schedules the existing exit owner
 // once, and restores the preceding committed lineup without adding history.
 reset(); CommitBossHistorySlot(-1); UH_BossRoundReset();
 int old_count=GetBossPickCount(-1);
 AbortBossSelection("test"); AbortBossSelection("again");
 assert(gameover && exit_requests==1 && GetBossPickCount(-1)==old_count);
 assert(uh_bosslastlineup[0]==1 && uh_bosslastlineup[1]==-1);
 puts("PASS: automatic count thresholds/boundaries, boss selection defaults, weighted ties/strategies, override/player gates, signed requests, Combo isolation, repeat fallback, pity/tier probabilities and empty-pool abort");
 return 0;
}
'''


def main():
    helpers = (ROOT / "src/acs_source/unholy/uh_boss_selection_helpers.acs").read_text()
    round_helpers = (ROOT / "src/acs_source/unholy/uh_round_helpers.acs").read_text()
    choice = (ROOT / "src/acs_source/unholy/uh_boss_choice.acs").read_text()
    names = ("ForceBossChange", "CheckBossList", "GetBossSelectionMode", "GetBossSelectionWeight",
             "GetBossSelectionMinPlayers", "GetBossSelectionMaxPlayers", "BossSelectionMeetsPlayerLimits",
             "CanPickRandomBoss", "CanPickSpecifiedBoss", "ConfiguredForceBossChange", "AbortBossSelection",
             "CommitBossHistorySlot", "UH_BossRoundReset", "UH_BossRoundRecord",
             "UH_BossRoundSeen", "BossSelectionSetting", "BossWasInPreviousLineup",
             "PickBossPoolPass", "PickLeastSeenBossFromPool", "PickStandardBoss",
             "RollFullBossPool", "TrueRandomBoss", "SetUpBossSelection_Func")
    acs = function(round_helpers, "RandomPercent") + "\n" + "\n".join(
        function(helpers, name) for name in names)
    acs += function(choice, "PickBonusBossOption")
    # Remove logging only; selection, state updates and RNG calls are intact.
    acs = re.sub(r"UH_Log\(.*?\);", "", acs, flags=re.S)
    acs = acs.replace("GetCVAR(", "GetCVar(")
    cvars = (ROOT / "src/CVARINFO.server").read_text()
    settings = re.findall(r'server (?:int|bool) (uh_sv_boss(?:selectmode|avoidrepeat|avoidduplicates|rarelimit|shadowchance|full\w+chance)) = (\w+);', cvars)
    assert len(settings) == 9, settings
    expected = ("0", "false", "false", "25", "10", "5", "1", "15", "30")
    assert tuple(value for _, value in settings) == expected, settings
    assert "server bool uh_sv_bossforcedplayerlimits = false;" in cvars
    flow = (ROOT / "src/acs_source/unholy/uh_bossselect.acs").read_text()
    assert "!CanPickSpecifiedBoss(bosschoiceid)" in flow
    assert "strongmancheck[0] >= 0 && !CanPickSpecifiedBoss(strongmancheck[0])" in flow
    assert "if (!SetUpBossSelection_Func())" in flow
    assert flow.index('AbortBossSelection("ordinary round")') < flow.index("CommitSelectedBossHistory();")
    assert 'AbortBossSelection("Shadow reveal"); terminate;' in flow
    event = (ROOT / "src/acs_source/unholy/uh_events.acs").read_text()
    assert event.index('AbortBossSelection("True Power event")') < event.index('// UnholyBoss1')
    assert "CanPickSpecifiedBoss(options[pick])" in choice
    combo = (ROOT / "src/acs_source/unholy/uh_boss_combos.acs").read_text()
    assert "ConfiguredForceBossChange" not in combo and "CanPickSpecifiedBoss" not in combo
    thresholds = re.findall(r'server int uh_sv_multiboss_minplayers[2-5] = (\d+);', cvars)
    assert thresholds == ["6", "9", "12", "15"], thresholds
    acs += function(round_helpers, "GetClampedCVar") + "\n" + function(combo, "AutoBossCountForPlayers")
    with tempfile.TemporaryDirectory(prefix="uh-boss-settings-") as tmp:
        path = Path(tmp)
        (path / "test.c").write_text(STUBS + translate(acs) + TESTS)
        subprocess.run(["gcc", "-D_POSIX_C_SOURCE=200809L", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


if __name__ == "__main__":
    main()
