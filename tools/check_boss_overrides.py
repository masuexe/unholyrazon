#!/usr/bin/env python3
"""Exercise actual actor-keyed storage and host command ACS with C stubs.

This checks transactions and command queues, not engine networking. ACC checks
ACS syntax separately; source checks pin server-only entry points and this
integration with the effective selection getters.
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
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#include <stdint.h>
typedef const char *str;
str saved="", queue="", output[4096];
int can_write=1, busy, writes, lines;
int StrLen(str s) { return strlen(s); }
int GetChar(str s,int p) { return p>=0 && p<StrLen(s)?s[p]:0; }
int StrCmp(str a,str b) { return strcmp(a,b); }
int StrICmp(str a,str b) { return strcasecmp(a,b); }
str StrMid(str s,int start,int count) {
 char *copy=calloc(count+1,1); memcpy(copy,s+start,count); return copy;
}
str number(int value) {
 char s[32]; snprintf(s,sizeof(s),"%d",value); return strdup(s);
}
str concat(int count,...) {
 va_list ap; size_t size=1; va_start(ap,count);
 for(int i=0;i<count;i++) size+=strlen(va_arg(ap,str));
 va_end(ap); char *s=calloc(size,1); va_start(ap,count);
 for(int i=0;i<count;i++) strcat(s,va_arg(ap,str));
 va_end(ap); return s;
}
void log_text(str s) { assert(lines<4096); output[lines++]=s; }
str GetCVarString(str name) {
 if(!strcmp(name,"uh_sv_bossrules")) return saved;
 assert(!strcmp(name,"uh_boss_commands")); return queue;
}
int SetCVarString(str name,str value) {
 if(!strcmp(name,"uh_boss_commands")) { queue=value; return 1; }
 assert(!strcmp(name,"uh_sv_bossrules"));
 if(!can_write) return 0;
 saved=value; writes++; return 1;
}
void SetCVar(str name,int value) {
 assert(!strcmp(name,"uh_boss_configbusy")); busy=value;
}
#define UHBOSS_FAIL -9999
str registered_actor="KnownBoss";
int registered_id=5;
int FindBossByActor(str actor) {
 return StrICmp(actor,registered_actor)?UHBOSS_FAIL:registered_id;
}
str GetBossActor(int id) { assert(id==registered_id); return registered_actor; }
str GetBossName(int id) { assert(id==registered_id); return "Known Boss"; }
int IsBossEnabled(int id) { return id==registered_id; }
#define UHBOSS_POOL_NONE 0
#define UHBOSS_POOL_COMMON 1
#define UHBOSS_POOL_RARE 2
#define UHBOSS_POOL_SPECIAL 3
#define UHBOSS_POOL_ULTRA 4
#define UHBOSS_POOL_EX 5
int GetBossRarity(int id) { (void)id; return 1; }
int PlayerCount(void) { return 8; }
int select_mode, avoid_repeat, avoid_duplicates, appearances, delta, previous;
int GetCVar(str name) {
 if(!strcmp(name,"uh_sv_bossforcedplayerlimits")) return 0;
 if(!strcmp(name,"uh_sv_bossselectmode")) return select_mode;
 if(!strcmp(name,"uh_sv_bossavoidrepeat")) return avoid_repeat;
 if(!strcmp(name,"uh_sv_bossavoidduplicates")) return avoid_duplicates;
 assert(!"unexpected CVAR"); return 0;
}
int GetBossPickCount(int id) { return id==registered_id?appearances:-1; }
int UH_BossRoundSeen(int id) { return id==registered_id?delta:0; }
int BossWasInPreviousLineup(int id) { return id==registered_id && previous; }
int GetBossPoolCount(int pool) { return pool==1?1:0; }
int GetBossPoolId(int pool,int row) { assert(pool==1 && row==0); return registered_id; }
void check_diagnostics(str actor);
void pool_diagnostics(int tier);
void acs_wait(str name,int map,intptr_t arg) {
 assert(map==0);
 if(!strcmp(name,"uh_BossCheckDiagnostics")) check_diagnostics((str)arg);
 else { assert(!strcmp(name,"uh_BossPoolDiagnostics")); pool_diagnostics((int)arg); }
}
#define ACS_NamedExecuteWait(name,map,arg) acs_wait(name,map,(intptr_t)(arg))
bool printed(str text) {
 for(int i=0;i<lines;i++) if(strstr(output[i],text)) return true;
 return false;
}
'''

TESTS = r'''
int main(void) {
 // Strict record parsing: delimiters, duplicate keys, bounds and ranges.
 assert(UH_BR_Load() && UH_BR_Count()==0);
 assert(UH_BR_ValidActor("Addon.Boss-1"));
 assert(!UH_BR_ValidActor("Boss;writeini") && !UH_BR_ValidActor("Boss:1"));
 assert(!UH_BR_ValidActor("Boss name") && !UH_BR_ValidActor("Boss|reset"));
 assert(UH_BR_Number("1000000")==1000000);
 assert(UH_BR_Number("1000001")==-2 && UH_BR_Number("999999999999")==-2);
 assert(UH_BR_Number("2garbage")==-2 && UH_BR_Number("+2")==-2);
 assert(UH_BR_Number("-1")==-1 && UH_BR_Number("-2")==-2);
 assert(!UH_BR_ValidValue(-1,0) && !UH_BR_ValidValue(UH_BR_FIELDS,-1));
 const char *bad[]={"KnownBoss:2,1,0,0", "KnownBoss:2,0,0,0;",
  "KnownBoss:3,1,0,0;", "KnownBoss:2,1000001,0,0;", "KnownBoss:2,1,65,0;",
  "KnownBoss:2,1,0,65;", "KnownBoss:2,1,8,7;", "KnownBoss:2,1,0,0,0;",
  "KnownBoss:2,1,0;", "KnownBoss:2,1,0,0;knownboss:1,1,0,0;",
  "Boss name:2,1,0,0;", "KnownBoss:2,1,x,0;"};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) assert(!UH_BR_Parse(bad[i],1));
 saved="KnownBoss:2,3,8,12;AddonBoss:1,-1,-1,0;";
 assert(UH_BR_Load() && UH_BR_Count()==2);
 assert(UH_BR_Get("knownboss",UH_BR_WEIGHT)==3);
 assert(UH_BR_Get("missing",UH_BR_WEIGHT)==-1);
 assert(UH_BR_Get("KnownBoss",-1)==-1);
 // A malformed reload keeps the last valid bank and cached lookup usable.
 assert(UH_BR_Get("KnownBoss",UH_BR_MIN)==8);
 saved="KnownBoss:2,1,9,2;";
 assert(!UH_BR_Load() && UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==3);
 assert(!UH_BR_Edit("KnownBoss",UH_BR_WEIGHT,4));
 saved="KnownBoss:2,3,8,12;AddonBoss:1,-1,-1,0;"; assert(UH_BR_Load());
 str before=saved;
 assert(!UH_BR_Edit("KnownBoss",UH_BR_MAX,7) && !strcmp(saved,before));
 assert(!UH_BR_Edit("KnownBoss",UH_BR_WEIGHT,0));
 can_write=0;
 assert(!UH_BR_Edit("KnownBoss",UH_BR_WEIGHT,9));
 assert(UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==3 && !strcmp(saved,before));
 can_write=1;
 assert(UH_BR_Edit("knownboss",UH_BR_WEIGHT,9) && UH_BR_Count()==2);
 assert(UH_BR_Get("KNOWNBOSS",UH_BR_WEIGHT)==9);
 assert(UH_BR_Edit("KnownBoss",UH_BR_MAX,0));
 assert(UH_BR_Edit("KnownBoss",UH_BR_MIN,64));
 assert(UH_BR_Edit("KnownBoss",UH_BR_MIN,-1));
 assert(UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==9);
 // Round/map reload reconstructs solely from archived actor names, even if
 // addon registration order changes the current signed id.
 registered_id=-1; uh_br_seen="!new map";
 assert(UH_BR_Load() && UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==9);
 registered_id=-7;
 assert(UH_BR_Get(GetBossActor(registered_id),UH_BR_WEIGHT)==9);
 // Commands canonicalize known names; missing addons remain stored/pending.
 UH_BC_Run("set:knownboss:mode:disabled:");
 assert(UH_BR_Get("KnownBoss",UH_BR_MODE)==0);
 UH_BC_Run("set:KnownBoss:mode:forced:");
 assert(UH_BR_Get("KnownBoss",UH_BR_MODE)==1);
 UH_BC_Run("set:KnownBoss:mode:random:");
 assert(UH_BR_Get("KnownBoss",UH_BR_MODE)==2);
 UH_BC_Run("set:KnownBoss:mode:inherit:");
 assert(UH_BR_Get("KnownBoss",UH_BR_MODE)==-1);
 UH_BC_Run("set:FutureBoss:weight:2:");
 assert(UH_BR_Get("FutureBoss",UH_BR_WEIGHT)==2 && printed("Pending:"));
 int snapshot_writes=writes;
 UH_BC_Run("set:FutureBoss:weight:bad:");
 UH_BC_Run("set:FutureBoss:mode:7:");
 UH_BC_Run("set:FutureBoss:weight:3:extra");
 UH_BC_Run("show:FutureBoss:weight::");
 UH_BC_Run("reset:FutureBoss:unknown::");
 assert(writes==snapshot_writes && UH_BR_Get("FutureBoss",UH_BR_WEIGHT)==2);
 UH_BC_Run("reset:FutureBoss:weight::");
 assert(UH_BR_Get("FutureBoss",UH_BR_WEIGHT)==-1);
 UH_BC_Run("reset:KnownBoss:::");
 assert(UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==-1);
 assert(printed("effective mode="));
 // Show/list/export/reload do not change stored data.
 snapshot_writes=writes;
 UH_BC_Run("show:AddonBoss:::");
 assert(UH_BC_Run("list::::"));
 UH_BC_Run("export::::"); UH_BC_Run("reload::::");
 assert(writes==snapshot_writes && printed("uh_sv_bossrules"));
 // A real batch queue retains each command, then lists without mutating it.
 queue="set:KnownBoss:weight:2:|set:KnownBoss:minplayers:8:|set:KnownBoss:maxplayers:16:|list::::|";
 drain();
 assert(!busy && !StrLen(queue));
 assert(UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==2);
 assert(UH_BR_Get("KnownBoss",UH_BR_MIN)==8 && UH_BR_Get("KnownBoss",UH_BR_MAX)==16);
 // Missing record terminators and too-large queues are rejected as a unit.
 snapshot_writes=writes;
 queue="set:KnownBoss:weight:5:"; drain();
 assert(!busy && writes==snapshot_writes);
 char *large=calloc(UH_BR_TEXT_CAP+3,1);
 memset(large,'a',UH_BR_TEXT_CAP+1); large[UH_BR_TEXT_CAP]='|'; queue=large;
 drain(); assert(!busy && writes==snapshot_writes);
 // The handler processes at most 256 queued commands.
 queue="";
 for(int i=1;i<=257;i++) queue=concat(3,queue,concat(3,"set:KnownBoss:weight:",number(i),":|"),"");
 drain(); assert(!busy && UH_BR_Get("KnownBoss",UH_BR_WEIGHT)==256);
 // Diagnostics do not edit archived rules or gameplay history. An empty
 // optional-repeat pool relaxes; the forced-only reason remains explicit.
 assert(UH_BR_Edit("KnownBoss",UH_BR_WEIGHT,3));
 appearances=9; delta=2; previous=1; avoid_repeat=avoid_duplicates=1;
 snapshot_writes=writes; before=saved;
 queue="check:KnownBoss:::|pool:common:::|pool::::|"; drain();
 assert(writes==snapshot_writes && !strcmp(saved,before));
 assert(appearances==9 && delta==2 && previous==1);
 assert(printed("Optional repeat exclusions relax") && printed("appearances=9"));
 assert(printed("candidates=1 draw weight=3"));
 assert(UH_BC_Run("pool:invalid:::")==0 && UH_BC_Run("pool:rare:extra::")==0);
 assert(UH_BC_Run("check:KnownBoss:extra::")==0);
 UH_BC_Run("set:KnownBoss:mode:forced:");
 lines=0; check_diagnostics("KnownBoss");
 assert(printed("Random blocked: forced-only mode."));
 // Capacity is bounded; resets release rows for another actor.
 saved="";
 for(int i=0;i<UH_BR_CAP;i++) saved=concat(3,saved,concat(3,"B",number(i),":-1,1,-1,-1;"),"");
 assert(UH_BR_Load() && UH_BR_Count()==256);
 before=saved;
 assert(!UH_BR_Edit("Overflow",UH_BR_WEIGHT,1) && !strcmp(saved,before));
 assert(!UH_BR_Parse(concat(2,saved,"Overflow:-1,1,-1,-1;"),1-uh_br_bank));
 assert(UH_BR_Edit("B0",-1,-1) && UH_BR_Count()==255);
 assert(UH_BR_Edit("Overflow",UH_BR_WEIGHT,1) && UH_BR_Count()==256);
 assert(UH_BR_Edit("B1",UH_BR_WEIGHT,-1) && UH_BR_Count()==255);
 // Export contains short commands and omits the internal multiline marker.
 saved=""; assert(UH_BR_Load());
 for(int i=0;i<100;i++) assert(UH_BR_Edit(concat(2,"ExportBoss_",number(i)),UH_BR_WEIGHT,1));
 str archived=saved;
 assert(StrLen(archived)>2048 && GetChar(archived,0)==10);
 snapshot_writes=writes; lines=0; UH_BC_Run("export::::");
 assert(!strcmp(output[0],"uh_sv_bossrules \"\""));
 str prefix="eval + $uh_sv_bossrules \"", suffix="\" uh_sv_bossrules", rebuilt="";
 for(int i=1;i<lines-1;i++) {
   assert(StrLen(output[i])<4095 && !strncmp(output[i],prefix,strlen(prefix)));
   int n=StrLen(output[i])-StrLen(prefix)-StrLen(suffix);
   assert(n>0 && n<=1024);
   assert(!strcmp(output[i]+StrLen(output[i])-StrLen(suffix),suffix));
   rebuilt=concat(2,rebuilt,StrMid(output[i],StrLen(prefix),n));
 }
 assert(!strcmp(output[lines-1],"uh_boss_reload"));
 assert(!strcmp(rebuilt,UH_BR_Data(archived)));
 assert(writes==snapshot_writes && !strcmp(saved,archived));
 // Normalize direct long loads. Failed writes preserve the current bank and
 // retry successfully when writes become available again.
 saved=rebuilt; can_write=0; assert(!UH_BR_Load()); can_write=1;
 assert(UH_BR_Load() && !strcmp(saved,archived));
 snapshot_writes=writes; assert(UH_BR_Load() && writes==snapshot_writes);
 // Text capacity is independent of record count; rejection is transactional.
 saved="";
 str key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
 for(int i=0;i<110;i++) saved=concat(3,saved,concat(4,key,number(i),":", "2,1000000,64,64;"),"");
 assert(StrLen(saved)<UH_BR_TEXT_CAP && UH_BR_Load());
 while(true) {
   before=saved;
   if(!UH_BR_Edit(concat(2,key,number(UH_BR_Count())),UH_BR_WEIGHT,1000000)) break;
 }
 assert(!strcmp(saved,before) && UH_BR_Count()<UH_BR_CAP);
 saved=large;
 assert(!UH_BR_Load() && UH_BR_Count()>110);
 puts("PASS: boss override transactions, actor identity, strict validation, pending addons, reset/capacity, multiline archives, chunked export, read-only commands and batch queues");
 return 0;
}
'''


def main():
    storage = (ROOT / "src/acs_source/_imports/uhbsset.acs").read_text()
    commands = (ROOT / "src/acs_source/unholy/uh_boss_config.acs").read_text()
    diagnostics = (ROOT / "src/acs_source/unholy/uh_boss_diagnostics.acs").read_text()
    # Make ACS's function-scoped loop variables explicit to the C compiler.
    edit = function(storage, "UH_BR_Edit")
    c_edit = edit.replace("int value) {", "int value) { int row, f;")
    c_edit = c_edit.replace("for (int row =", "for (row =").replace("for (int f =", "for (f =")
    storage = storage.replace(edit, c_edit)
    handler = commands[commands.index('script "uh_BossConfigCommands"'):commands.index('script "uh_BossConfigWatch"')]
    handler = handler.replace('script "uh_BossConfigCommands" (void)', "void drain(void)")
    functions = "\n".join(function(commands, name) for name in
                          ("UH_BC_Field", "UH_BC_ModeName", "UH_BC_Token", "UH_BC_Show", "UH_BC_Export", "UH_BC_Run"))
    assert '#import "uhdt.acs"' not in storage
    for name in ("uh_BossConfigCommands", "uh_BossConfigWatch"):
        assert not re.search(r'script "' + name + r'"[^\n]*(?:NET|CLIENTSIDE)', commands)
    assert "Delay(1);" in handler and "uh_boss_configbusy" in handler
    helpers = (ROOT / "src/acs_source/unholy/uh_boss_selection_helpers.acs").read_text()
    getters = "\n".join(function(helpers, name) for name in
                        ("GetBossSelectionMode", "GetBossSelectionWeight", "GetBossSelectionMinPlayers",
                         "GetBossSelectionMaxPlayers", "BossSelectionMeetsPlayerLimits", "CanPickRandomBoss", "CanPickSpecifiedBoss", "BossSelectionSetting"))
    diag_functions = function(diagnostics, "UH_BD_Tier") + function(diagnostics, "UH_BD_Eligible")
    diag_scripts = diagnostics[diagnostics.index('script "uh_BossCheckDiagnostics"'):]
    diag_scripts = diag_scripts.replace('script "uh_BossCheckDiagnostics" (int actor)', "void check_diagnostics(str actor)")
    diag_scripts = diag_scripts.replace('script "uh_BossPoolDiagnostics" (int tier) {', "void pool_diagnostics(int tier) { int i, id, count;")
    pool_start = diag_scripts.index("void pool_diagnostics")
    diag_scripts = diag_scripts[:pool_start] + diag_scripts[pool_start:].replace("for (int i =", "for (i =").replace("int id =", "id =").replace("int count =", "count =")
    for forbidden in ("random(", "PickBossPoolPass(", "TrueRandomBoss(", "ForceBossChange(",
                      "SetCVar(", "SetCVarString(", "CommitBossHistorySlot(", "IncrementBossPickCount("):
        assert forbidden not in diagnostics
    aliases = (ROOT / "src/KEYCONF").read_text()
    for op in ("set", "show", "reset", "list", "export", "reload", "check", "pool"):
        assert f"eval + $uh_boss_commands {op}:%1:%2:%3:%4|" in aliases
    assert 'alias uh_boss_save "wait 1; uh_boss_save_check"' in aliases
    assert 'local string uh_sv_bossrules = "";' in (ROOT / "src/CVARINFO.server").read_text()
    assert 'local noarchive string uh_boss_commands = "";' in (ROOT / "src/CVARINFO.ipc").read_text()
    assert "UHBSSET" not in (ROOT / "src/LOADACS").read_text()
    with tempfile.TemporaryDirectory(prefix="uh-boss-overrides-") as tmp:
        path = Path(tmp)
        (path / "test.c").write_text(STUBS + translate(storage + getters + diag_functions + functions + diag_scripts + handler) + TESTS)
        subprocess.run(["gcc", "-D_POSIX_C_SOURCE=200809L", "-std=c99", "-Wall",
                        "-Wextra", "-Werror", str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


if __name__ == "__main__":
    main()
