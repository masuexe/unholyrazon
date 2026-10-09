#!/usr/bin/env python3
"""Run the actual integer/string-only ACS settings code with C test stubs.

This is a logic regression test, not an engine/network test. ACC compilation
checks ACS syntax separately. No fixed-point or latent ACS code is translated.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    match = re.search(r"function (?:int|bool|str|void) " + name + r"\(", source)
    start = source.index("{", match.start())
    end, depth = start + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end]


def format_calls(source):
    """Translate ACS s:/i: formatting to C string concatenation."""
    pattern = re.compile(r"\b(StrParam|Log)\(")
    while match := pattern.search(source):
        pos = match.end()
        start, depth, quote = pos, 1, False
        parts = []
        while depth:
            ch = source[pos]
            if ch == '"' and source[pos - 1] != "\\":
                quote = not quote
            if not quote:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if (ch == "," and depth == 1) or depth == 0:
                    parts.append(source[start:pos].strip())
                    start = pos + 1
            pos += 1
        args = []
        for part in parts:
            assert part[:2] in ("s:", "i:"), part
            args.append(part[2:] if part[:2] == "s:" else f"number({part[2:]})")
        expression = f"concat({len(args)}, " + ", ".join(args) + ")"
        if match[1] == "Log":
            expression = "log_text(" + expression + ")"
        source = source[:match.start()] + expression + source[pos:]
    return source


def translate(source):
    source = re.sub(r"^#(?:library|include|import).*\n", "", source, flags=re.M)
    source = source.replace("#libdefine", "#define").replace("function ", "")
    # ACS loop variables are function-scoped. Make that scope explicit in C.
    source = source.replace("bool UH_ER_EditCore(str stem, int field, int value, str exstem) {",
                            "bool UH_ER_EditCore(str stem, int field, int value, str exstem) { int row, f;")
    begin = source.find("bool UH_ER_EditCore(")
    if begin >= 0:
        source = source[:begin] + source[begin:].replace("for (int row =", "for (row =").replace("for (int f =", "for (f =")
    source = re.sub(r'script "uh_EventConfigPrint" \(void\) CLIENTSIDE \{.*?\}', "", source, flags=re.S)
    source = source.split('script "uh_EventConfigWatch" OPEN')[0]
    source = source.replace('script "uh_EventConfigCommands" (void)', "void drain(void)")
    source = source.replace("terminate;", "return;")
    source = source.replace("Delay(1);", "/* Separate ACS tic in engine. */")
    source = source.replace("for (field = 0;", "for (int field = 0;")
    source = re.sub(r"\brandom\(", "acs_random(", source)
    return format_calls(source)


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
typedef const char *str;
str saved = "", queue = "";
int minimum_setting = 12, ex_setting = 3, can_write = 1;
int select_mode, avoid_repeat=1, forced_limits, ex_limits, players=8;
int roll_override;
int PlayerCount(void) { return players; }
int acs_random(int low, int high) {
    assert(high>=low);
    if(roll_override) { assert(roll_override>=low && roll_override<=high); return roll_override; }
    return high;
}
str output[2048]; int lines;
int StrLen(str s) { return strlen(s); }
int GetChar(str s, int p) { return p >= 0 && p < StrLen(s) ? s[p] : 0; }
int StrCmp(str a, str b) { return strcmp(a,b); }
int StrICmp(str a, str b) { return strcasecmp(a,b); }
str StrMid(str s, int start, int count) {
    char *copy = calloc(count+1,1); memcpy(copy,s+start,count); return copy;
}
str number(int n) { char buf[32]; snprintf(buf,sizeof(buf),"%d",n); return strdup(buf); }
str concat(int count, ...) {
    va_list ap; size_t size = 1; va_start(ap,count);
    for(int i=0;i<count;i++) size += strlen(va_arg(ap,str)); va_end(ap);
    char *s = calloc(size,1); va_start(ap,count);
    for(int i=0;i<count;i++) strcat(s,va_arg(ap,str)); va_end(ap); return s;
}
void log_text(str s) { assert(lines < 2048); output[lines++]=s; }
str GetCVarString(str name) { return !strcmp(name,"uh_event_commands") ? queue : saved; }
int SetCVarString(str name, str value) {
    if(!can_write) return 0;
    if(!strcmp(name,"uh_event_commands")) queue = value; else saved = value;
    return 1;
}
int GetCVar(str name) {
    if(!strcmp(name,"uh_sv_bonusminplayers")) return minimum_setting;
    if(!strcmp(name,"uh_sv_bonusexcount")) return ex_setting;
    if(!strcmp(name,"uh_sv_bonusselectmode")) return select_mode;
    if(!strcmp(name,"uh_sv_bonusavoidrepeat")) return avoid_repeat;
    if(!strcmp(name,"uh_sv_bonusforcedplayerlimits")) return forced_limits;
    if(!strcmp(name,"uh_sv_bonusexplayerlimits")) return ex_limits;
    assert(!"Unknown CVAR"); return 0;
}
void SetCVar(str name, int value) { (void)name; (void)value; }
int CheckScript(str name, int unused) { (void)unused; return name[0] != 0; }
#define UH_MAX_BONUS_EVENTS 256
#define UHBE_FAIL -9999
#define UHDB_ROW_ACTIVE 1
#define UHDB_ROW_DISABLED 2
#define UHBE_STR_STEM 0
#define UHBE_STR_NAME 1
#define UHBE_STR_STARTCB 2
#define UHBE_INT_WEIGHT 0
#define UHBE_INT_MINP 1
#define UHBE_INT_MAXP 2
str uh_bestr[256][3]; int uh_bedefined[256], uh_beint[256][3];
int uh_beexbase[256], uh_beexevent[256], uh_beexthreshold[256], uh_beexcount;
int uh_eventpickcount[256], eventexcountarray[256], uh_eventfamilyextra[256];
str uh_eventextargetseen[256]; bool uh_eventextargetknown[256];
int eventdataarr[5];
#define EVENTDATA_EXORIGIN 4
#define UH_LOG_DEBUG 0
#define UH_LOG_WARN 1
#define UHEVENT_FOOTBALL 13
#define UHEVENT_RUNES 113
void UH_Log(int level, str message) { (void)level; log_text(message); }
int GetBonusEventEXTarget(int id);
int GetBonusEventEXThreshold(int id);
int ValidateBonusEventEXTarget(str stem, str changed, str candidate);
void SyncBonusEventEXProgress(int id);
str UH_BE_EXNext(str stem, str changed, str candidate);
str GetBonusEventStem(int id);
str GetBonusEventStartCallback(int id);
int GetBonusEventMode(int id);
bool BonusEventMeetsPlayerLimits(int id, int count);
int GetBonusEventSelectionMode(void);
void test_policy(void);
bool IsBonusEventDefined(int id) { return id>=0 && id<256 && uh_bedefined[id]; }
int FindBonusEventByStem(str stem) {
    for(int i=0;i<256;i++) if(IsBonusEventDefined(i) && !StrICmp(uh_bestr[i][0],stem)) return i;
    return UHBE_FAIL;
}
int FindBonusEventEXRow(int id) { for(int i=0;i<uh_beexcount;i++) if(uh_beexbase[i]==id) return i; return -1; }
str GetBonusEventStem(int id) { return IsBonusEventDefined(id) ? uh_bestr[id][0] : ""; }
str GetBonusEventName(int id) { return uh_bestr[id][1]; }
str GetBonusEventStartCallback(int id) { return uh_bestr[id][2]; }
void register_event(int id, str stem, int weight, int minplayers, int maxplayers) {
    uh_bestr[id][0]=stem; uh_bestr[id][1]=stem; uh_bestr[id][2]="start";
    uh_bedefined[id]=1; uh_beint[id][0]=weight; uh_beint[id][1]=minplayers; uh_beint[id][2]=maxplayers;
}
bool has_output(str text) {
    for(int i=0;i<lines;i++) if(strstr(output[i],text)) return true;
    return false;
}
'''

TESTS = r'''
int main(void) {
    register_event(0,"ffa",1,0,0); register_event(1,"demoneye_parade",1,12,0);
    register_event(2,"boss_ffa",1,0,0); register_event(3,"satan_seal_ffa",0,0,0);
    register_event(200,"addon_a",7,4,20); uh_beexcount=1; uh_beexbase[0]=0; uh_beexevent[0]=3; uh_beexthreshold[0]=3;
    assert(UH_ER_Load()); assert(UH_ER_Count()==0);
    assert(GetBonusEventMinPlayers(1)==12); minimum_setting=8; assert(GetBonusEventMinPlayers(1)==8);
    assert(GetBonusEventMinPlayers(200)==4);
    queue="set:boss_ffa:weight:2:|set:demoneye_parade:minplayers:6:|set:boss_ffa:maxplayers:10:|";
    drain(); assert(!StrLen(queue)); assert(GetBonusEventWeight(2)==2);
    assert(GetBonusEventMinPlayers(1)==6); assert(GetBonusEventMaxPlayers(2)==10);
    assert(UH_BonusEligible(2,10,-1)); assert(!UH_BonusEligible(2,11,-1));
    assert(!UH_BonusEligible(1,5,-1)); assert(UH_BonusEligible(1,6,-1));
    assert(!UH_BonusEligible(1,6,1));
    UH_EC_Run("set:boss_ffa:mode:forced:"); assert(GetBonusEventMode(2)==UH_ER_FORCED);
    assert(!UH_BonusEligible(2,2,-1));
    UH_EC_Run("set:boss_ffa:mode:disabled:"); assert(GetBonusEventMode(2)==UH_ER_DISABLED);
    // EX-only rows stay forceable until explicitly made random, even with a weight override.
    UH_EC_Run("set:satan_seal_ffa:weight:3:"); assert(GetBonusEventMode(3)==UH_ER_FORCED);
    UH_EC_Run("set:satan_seal_ffa:mode:random:"); assert(GetBonusEventMode(3)==UH_ER_RANDOM);
    assert(GetBonusEventWeight(3)==3);
    UH_EC_Run("reset:satan_seal_ffa:weight::"); assert(GetBonusEventWeight(3)==1);
    UH_EC_Run("set:satan_seal_ffa:mode:disabled:"); assert(ResolveBonusEventEX(0)==UHBE_FAIL);
    uh_eventpickcount[0]=5; uh_eventpickcount[3]=2; uh_eventfamilyextra[0]=2; assert(GetBonusEventFamilyPickCount(0)==7);
    eventexcountarray[0]=2; UH_EC_Run("reset:satan_seal_ffa:::");
    assert(eventexcountarray[0]==2 && uh_eventpickcount[3]==2);
    assert(GetBonusEventMode(3)==UH_ER_FORCED); assert(ResolveBonusEventEX(0)==3);
    // Unknown addons persist by stem, independently of registration id/order.
    UH_EC_Run("set:late_addon:weight:9:"); UH_EC_Run("set:late_addon:minplayers:2:");
    register_event(221,"late_addon",1,12,0); assert(GetBonusEventWeight(221)==9);
    assert(GetBonusEventMinPlayers(221)==2);
    uh_bedefined[221]=0; register_event(219,"late_addon",1,12,0); assert(GetBonusEventWeight(219)==9);
    str good = saved;
    UH_EC_Run("set:boss_ffa:weight:0:"); assert(!StrCmp(saved,good));
    UH_EC_Run("set:boss_ffa:weight:2oops:"); assert(!StrCmp(saved,good));
    UH_EC_Run("set:boss_ffa:minplayers:65:"); assert(!StrCmp(saved,good));
    UH_EC_Run("set:boss_ffa:minplayers:11:"); assert(!StrCmp(saved,good));

    UH_EC_Run("set::weight:2:"); assert(!StrCmp(saved,good));
    UH_EC_Run("set:boss_ffa:weight:2:extra"); assert(!StrCmp(saved,good));
    saved="boss_ffa:2,4,12,8;"; assert(!UH_ER_Load()); assert(GetBonusEventWeight(2)==2);
    assert(!UH_ER_Edit("boss_ffa",UH_ER_WEIGHT,5));
    saved="boss_ffa:2,4,-1,-1;BOSS_FFA:2,5,-1,-1;"; assert(!UH_ER_Load());
    saved="boss_ffa:2,4,-1,-1"; assert(!UH_ER_Load());
    char long_data[16386]; memset(long_data,'x',sizeof(long_data)-1); long_data[sizeof(long_data)-1]=0;
    saved=long_data; assert(!UH_ER_Load()); assert(GetBonusEventWeight(2)==2);
    saved=good; assert(UH_ER_Load());
    UH_EC_Run("show:demoneye_parade:::"); assert(has_output("minplayers=6 [override]"));
    UH_EC_Run("reset:demoneye_parade:minplayers::"); assert(GetBonusEventMinPlayers(1)==8);
    UH_EC_Run("show:demoneye_parade:::"); assert(has_output("global uh_sv_bonusminplayers"));
    UH_EC_Run("reset:boss_ffa:::"); assert(GetBonusEventWeight(2)==1);
    assert(GetBonusEventMode(2)==UH_ER_RANDOM); assert(GetBonusEventMaxPlayers(2)==0);
    // A new map's empty cache reloads the archived data.
    uh_er_bank=0; uh_er_counts[0]=uh_er_counts[1]=0; uh_er_seen=""; uh_er_valid=true;
    assert(GetBonusEventWeight(219)==9);
    can_write=0; assert(!UH_ER_Edit("addon_a",UH_ER_WEIGHT,5)); can_write=1;
    assert(GetBonusEventWeight(200)==7);
    saved=""; assert(UH_ER_Load()); assert(UH_ER_Count()==0);
    assert(GetBonusEventWeight(219)==1);
    // Per-event EX controls: progression, pause, target replacement and frozen origin.
    UH_EC_Run("set:ffa:ex_count:2:"); assert(GetBonusEventEXThreshold(0)==2);
    SyncBonusEventEXProgress(0); eventexcountarray[0]=1;
    UH_EC_Run("set:ffa:ex_count:0:"); assert(ExEventChecker(0)==0 && eventexcountarray[0]==1);
    UH_EC_Run("set:ffa:ex_count:2:"); assert(ExEventChecker(0)==0 && eventexcountarray[0]==2);
    assert(ExEventChecker(0)==3 && eventexcountarray[0]==0);
    eventexcountarray[0]=2;
    UH_EC_Run("set:satan_seal_ffa:mode:disabled:");
    assert(ExEventChecker(0)==0 && eventexcountarray[0]==2);
    UH_EC_Run("reset:satan_seal_ffa:mode::");
    assert(ExEventChecker(0)==3);
    eventexcountarray[0]=1;
    UH_EC_Run("set:ffa:ex_target:boss_ffa:"); assert(GetBonusEventEXTarget(0)==2);
    assert(eventexcountarray[0]==0);
    eventexcountarray[0]=1; UH_EC_Run("set:ffa:ex_target:BOSS_FFA:");
    assert(eventexcountarray[0]==1);
    str exgood=saved;
    UH_EC_Run("set:ffa:ex_count:101:"); assert(!StrCmp(saved,exgood));
    UH_EC_Run("set:ffa:ex_count:-1:"); assert(!StrCmp(saved,exgood));
    // A new relation for an addon uses its per-event count, not the built-in global.
    UH_EC_Run("set:addon_a:ex_target:boss_ffa:");
    assert(GetBonusEventEXTarget(200)==2 && GetBonusEventEXThreshold(200)==0);
    UH_EC_Run("set:addon_a:ex_count:4:");
    assert(GetBonusEventEXThreshold(200)==4);
    UH_EC_Run("set:boss_ffa:ex_target:addon_a:");
    assert(!StrLen(UH_ER_Target("boss_ffa"))); // Indirect cycle ffa->boss->addon->boss.
    UH_EC_Run("reset:addon_a:::"); exgood=saved;
    UH_EC_Run("set:ffa:ex_target:ffa:"); assert(!StrCmp(saved,exgood));
    UH_EC_Run("set:boss_ffa:ex_target:ffa:"); assert(!StrCmp(saved,exgood));
    uh_bestr[200][2]="";
    UH_EC_Run("set:ffa:ex_target:addon_a:"); assert(!StrCmp(saved,exgood));
    uh_bestr[200][2]="start";
    UH_EC_Run("set:ffa:ex_target:pending_ex:"); assert(GetBonusEventEXTarget(0)==3);
    assert(has_output("addon is missing"));
    register_event(222,"pending_ex",0,0,0); SyncBonusEventEXProgress(0);
    assert(GetBonusEventEXTarget(0)==222 && eventexcountarray[0]==0);
    // Missing bases also retain settings until registration, independent of numeric ids.
    UH_EC_Run("set:missing_base:ex_target:missing_target:");
    UH_EC_Run("set:missing_base:ex_count:5:");
    register_event(223,"missing_base",1,0,0);
    assert(GetBonusEventEXTarget(223)==UHBE_FAIL);
    register_event(224,"missing_target",0,0,0);
    assert(GetBonusEventEXTarget(223)==224 && GetBonusEventEXThreshold(223)==5);
    // Reloaded invalid edges stay pending and retain the original registered target.
    saved="ffa:-1,-1,-1,-1,2,boss_ffa;boss_ffa:-1,-1,-1,-1,2,ffa;";
    assert(UH_ER_Load()); assert(GetBonusEventEXTarget(0)==3);
    saved=exgood; assert(UH_ER_Load()); SyncBonusEventEXProgress(0);
    uh_eventpickcount[2]=40;
    assert(GetBonusEventFamilyPickCount(0)==7); // New target's old history is not imported.
    eventdataarr[EVENTDATA_EXORIGIN]=1;
    UH_EC_Run("set:ffa:ex_target:satan_seal_ffa:");
    CommitBonusEventHistory(2); assert(GetBonusEventFamilyPickCount(0)==8);
    assert(eventdataarr[EVENTDATA_EXORIGIN]==0);
    UH_EC_Run("reset:ffa:ex_target::"); assert(GetBonusEventEXTarget(0)==3);
    UH_EC_Run("reset:ffa:ex_count::"); assert(GetBonusEventEXThreshold(0)==3);
    assert(GetBonusEventFamilyPickCount(0)==8);
    // Extended serialization and legacy rows both load without loss.
    assert(UH_ER_EditTarget("ffa","pending_ex")); str roundtrip=saved;
    uh_er_seen="!reload"; assert(UH_ER_Load()); assert(!StrCmp(UH_ER_Target("ffa"),"pending_ex"));
    saved="ffa:-1,-1,-1,-1,4,ffa;"; assert(!UH_ER_Load());
    saved="ffa:-1,-1,-1,-1,101,pending_ex;"; assert(!UH_ER_Load());
    saved="ffa:-1,-1,-1,-1,4;"; assert(!UH_ER_Load());
    saved=roundtrip; assert(UH_ER_Load());
    saved=""; assert(UH_ER_Load());
    // All capacity slots can be reused after reset; over-capacity edits are atomic.
    for(int i=0;i<256;i++) assert(UH_ER_Edit(concat(2,"pending_",number(i)),UH_ER_WEIGHT,1));
    assert(!UH_ER_Edit("too_many",UH_ER_WEIGHT,1));
    assert(UH_ER_Edit("pending_0",-1,-1)); assert(UH_ER_Edit("replacement",UH_ER_WEIGHT,1));
    assert(UH_ER_Count()==256);
    test_policy();
    puts("PASS: ACS settings logic, EX progression/pause, target validation, pending addons, frozen history, persistence, legacy format, capacity and selection policies");
}
'''


POLICY_TESTS = r'''
void test_policy(void) {
    saved=""; assert(UH_ER_Load());
    memset(uh_bedefined,0,sizeof(uh_bedefined));
    register_event(0,"ffa",1,0,0); register_event(1,"heavy",3,0,0);
    uh_eventpickcount[0]=0; uh_eventpickcount[1]=20;
    uh_eventfamilyextra[0]=uh_eventfamilyextra[1]=0;
    uh_beexcount=0;
    select_mode=0; avoid_repeat=1; forced_limits=ex_limits=0;
    assert(PickConfiguredBonusEvent(8,-1)==0);
    assert(PickConfiguredBonusEvent(8,0)==1); // Previous event is excluded before fairness.
    avoid_repeat=0; assert(PickConfiguredBonusEvent(8,0)==0);
    // Pure weighted mode covers the complete 1:3 interval, even with unequal histories.
    select_mode=1;
    for(int roll=1;roll<=4;roll++) {
        roll_override=roll;
        assert(PickConfiguredBonusEvent(8,-1)==(roll==1 ? 0 : 1));
    }
    roll_override=0;
    select_mode=-10; assert(GetBonusEventSelectionMode()==0);
    select_mode=10; assert(GetBonusEventSelectionMode()==1);
    select_mode=0; uh_eventpickcount[1]=0;
    for(int roll=1;roll<=4;roll++) {
        roll_override=roll;
        assert(PickConfiguredBonusEvent(8,-1)==(roll<=3 ? 1 : 0)); // Reservoir tie weight.
    }
    roll_override=0;
    // Repeat policy and single-candidate retry work in both strategies.
    assert(UH_ER_Edit("heavy",UH_ER_MODE,UH_ER_DISABLED));
    for(select_mode=0;select_mode<=1;select_mode++) {
        avoid_repeat=1; assert(PickConfiguredBonusEvent(8,0)==0);
        avoid_repeat=0; assert(PickConfiguredBonusEvent(8,0)==0);
        assert(UH_ER_Edit("ffa",UH_ER_MODE,UH_ER_DISABLED));
        assert(PickConfiguredBonusEvent(8,-1)==UHBE_FAIL);
        assert(UH_ER_Edit("ffa",UH_ER_MODE,-1));
    }
    // Forced selections use effective min/max but do not require random mode.
    register_event(2,"forced_only",0,12,16);
    players=8; forced_limits=0; assert(ResolveForcedBonusEvent(2)==2);
    forced_limits=1; assert(ResolveForcedBonusEvent(2)==-1);
    LogForcedBonusEventRejection(2,"CVAR"); assert(has_output("players=8 minplayers=12 maxplayers=16"));
    players=12; assert(ResolveForcedBonusEvent(2)==2);
    players=16; assert(ResolveForcedBonusEvent(2)==2);
    players=17; assert(ResolveForcedBonusEvent(2)==-1);
    assert(UH_ER_Edit("forced_only",UH_ER_MIN,4));
    players=4; assert(ResolveForcedBonusEvent(2)==2);
    assert(UH_ER_Edit("forced_only",UH_ER_MAX,0));
    players=64; assert(ResolveForcedBonusEvent(2)==2);
    assert(UH_ER_Edit("forced_only",UH_ER_MODE,UH_ER_DISABLED));
    forced_limits=0; assert(ResolveForcedBonusEvent(2)==-1);
    assert(UH_ER_Edit("forced_only",UH_ER_MODE,-1));
    // Legacy ids use normalized target limits too.
    register_event(13,"football_ffa",1,12,0); register_event(113,"rune_ffa",0,12,0);
    players=8; forced_limits=1;
    assert(ResolveForcedBonusEvent(50)==-1 && ResolveForcedBonusEvent(150)==-1);
    players=12; assert(ResolveForcedBonusEvent(50)==13 && ResolveForcedBonusEvent(150)==113);
    // A blocked EX neither advances a partial count nor consumes a ready count.
    assert(UH_ER_Edit("forced_only",-1,-1));
    uh_beexcount=1; uh_beexbase[0]=0; uh_beexevent[0]=2; uh_beexthreshold[0]=3;
    SyncBonusEventEXProgress(0); ex_setting=3; players=8; ex_limits=1;
    eventexcountarray[0]=1; assert(ExEventChecker(0)==0 && eventexcountarray[0]==1);
    eventexcountarray[0]=3; assert(ExEventChecker(0)==0 && eventexcountarray[0]==3);
    players=17; assert(ExEventChecker(0)==0 && eventexcountarray[0]==3);
    UH_EC_Run("show:ffa:::"); assert(has_output("target does not meet the player limits"));
    players=12; assert(ExEventChecker(0)==2 && eventexcountarray[0]==0);
    players=8; ex_limits=0; eventexcountarray[0]=3;
    assert(ExEventChecker(0)==2 && eventexcountarray[0]==0);
    // A live target override is used by the EX range policy.
    ex_limits=1; assert(UH_ER_Edit("forced_only",UH_ER_MIN,4));
    eventexcountarray[0]=1; assert(ExEventChecker(0)==0 && eventexcountarray[0]==2);
    eventexcountarray[0]=3;
    assert(UH_ER_Edit("forced_only",UH_ER_MODE,UH_ER_DISABLED));
    assert(ExEventChecker(0)==0 && eventexcountarray[0]==3);
    select_mode=1; avoid_repeat=0;
    UH_EC_Run("policy::::"); assert(has_output("uh_sv_bonusselectmode=1 (weighted random)"));
    assert(has_output("uh_sv_bonusavoidrepeat=0"));
    UH_EC_Run("show:ffa:::"); assert(has_output("target is disabled"));
}
'''


def main():
    registry = (ROOT / "src/acs_source/_imports/uhdt.acs").read_text()
    helpers = (ROOT / "src/acs_source/unholy/uh_event_helpers.acs").read_text()
    storage = (ROOT / "src/acs_source/_imports/uhbeset.acs").read_text()
    commands = (ROOT / "src/acs_source/unholy/uh_event_config.acs").read_text()
    getters = "\n".join(function(registry, name) for name in (
        "GetBonusEventWeight", "GetBonusEventMinPlayers", "GetBonusEventMaxPlayers",
        "GetBonusEventMode", "UH_BonusEligible", "ResolveBonusEventEX",
        "GetBonusEventEXThreshold", "UH_BE_EXNext", "ValidateBonusEventEXTarget", "GetBonusEventEXTarget",
        "BonusEventMeetsPlayerLimits", "GetBonusEventSelectionMode", "PickBonusEvent"))
    cvars = (ROOT / "src/CVARINFO.server").read_text()
    for declaration in (
        "server int uh_sv_bonusselectmode = 0;", "server bool uh_sv_bonusavoidrepeat = true;",
        "server bool uh_sv_bonusforcedplayerlimits = false;", "server bool uh_sv_bonusexplayerlimits = false;"
    ):
        assert declaration in cvars
    events = (ROOT / "src/acs_source/unholy/uh_events.acs").read_text()
    selection, frozen = events.split("  else if (perform != -2)", 1)
    assert "PickConfiguredBonusEvent(PlayerCount()" in selection
    assert 'CheckClearCVar("uh_sv_bonuseventnum", -1)' in selection
    assert "eventdataarr[EVENTDATA_FORCED] = -1;" in selection
    assert "ResolveForcedBonusEvent" not in frozen and "ExEventChecker" not in frozen
    # Permission gate and frozen-event behavior are engine-facing source checks.
    assert 'script "uh_EventConfigCommands" (void) {' in commands
    assert not re.search(r'uh_EventConfigCommands"[^\n]*(?:NET|CLIENTSIDE)', commands)
    start = function(registry, "RunBonusEventStart")
    assert "GetBonusEventMode" not in start
    aliases = (ROOT / "src/KEYCONF").read_text()
    for command in ("set", "reset", "show", "list", "reload", "export", "policy"):
        assert f"eval + $uh_event_commands {command}:%1:%2:%3:%4|" in aliases
    assert 'alias uh_event_save "wait 1; uh_event_save_check"' in aliases
    assert 'test || $uh_event_configbusy != $uh_event_commands' in aliases
    assert "Delay(1);" in commands
    assert 'script "uh_EventConfigWatch" OPEN {' in commands
    assert "pukename uh_EventConfigCommands" not in aliases
    source = STUBS + translate(storage) + translate(getters)
    source += translate("\n".join(function(helpers, name) for name in (
        "GetBonusEventFamilyPickCount", "SyncBonusEventEXProgress", "ExEventChecker", "CommitBonusEventHistory",
        "PickLeastSeenBonusEvent", "PickConfiguredBonusEvent", "NormalizeForcedBonusEvent",
        "ResolveForcedBonusEvent", "LogForcedBonusEventRejection")))
    source += translate(commands) + POLICY_TESTS + TESTS
    with tempfile.TemporaryDirectory(prefix="uh-event-settings-") as tmp:
        path = Path(tmp)
        (path / "test.c").write_text(source)
        subprocess.run(["gcc", "-D_POSIX_C_SOURCE=200809L", "-std=c99", "-Wall", "-Wextra",
                        "-Werror", "-Wno-misleading-indentation", str(path / "test.c"),
                        "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


if __name__ == "__main__":
    main()
