#!/usr/bin/env python3
"""Run the actual True Power ACS with stubs for HP and morph transactions.

ACC checks language compatibility separately. These cases cannot prove engine
collision, CustomInventory consumption, rendering, or remote-client behaviour.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    repeat = (ROOT / "src/acs_source/classes/shared/true_power.acs").read_text()
    repeat = repeat[repeat.index('script "uh_TruePower_Repeat"'):]
    repeat = repeat.replace('script "uh_TruePower_Repeat" (void)', 'void Repeat(void)')
    morph = (ROOT / "src/acs_source/classes/bosses/higlur_truepower.acs").read_text()
    morph = morph.replace('script "ub_TruePowerHiglur" (void)', 'void Transform(void)')
    source = (repeat + morph).replace('terminate;', 'return;')
    decorate = (ROOT / "src/actors/items/other/TruePower.dec").read_text()
    route = decorate.split('UseX_Silent:', 1)[1].split('No:', 1)[0]
    assert route.index('"UseHiglur"') < route.index('"BAWS"')
    assert route.index('"BAWS"') < route.index('"UseAgain"')
    assert route.index('"UseAgain"') < route.index('"MorphedFlag"')
    assert 'CallACS("uh_TruePower_Repeat")' in route
    assert 'A_JumpIfInventory("IsAFakeBoss", 1, "No")' in route
    assert 'ACS_NamedExecute("ub_TruePowerHiglur", 0)' in route
    cap = (ROOT / 'src/acs_source/_imports/uh_acsutils.acs').read_text()
    assert '#libdefine MAX_HEALTH 30000' in cap
    with tempfile.TemporaryDirectory(prefix='uh-truepower-') as directory:
        path = Path(directory)
        (path / 'test.c').write_text(STUBS + source + TESTS)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        str(path / 'test.c'), '-o', str(path / 'test')], check=True)
        subprocess.run([str(path / 'test')], check=True)


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define APROP_Health 0
#define APROP_SpawnHealth 1
#define MAX_HEALTH 30000
#define UHEALTH_HEAL 6
#define UHBOSS_FAIL -9999
#define BOSSDATA_TID 0
#define BOSSDATA_NUM 1
#define min(a,b) ((a)<(b)?(a):(b))
int pn, hp, cap, baws, flag, fake, generation, tid, connected, spectator;
int interrupted, blocked, missing, cleanups, morphs, refunded, sparkles, syncs;
int result, spawnflag, activeboss, multibosscheck, bossdataarr[2][2], heals;
int playerlifestatusarr[1];
bool refreshhudmessage;
const char *body;
int PlayerNumber(void) { return pn; }
int GetActorProperty(int who, int prop) { assert(!who); return prop ? cap : hp; }
void SetActorProperty(int who, int prop, int value) {
  assert(!who); if (prop) cap = value; else hp = value;
}
int CheckInventory(const char *name) {
  if (!strcmp(name,"TruePowerItemFlag")) return flag;
  if (!strcmp(name,"BAWS")) return baws;
  assert(!strcmp(name,"IsAFakeBoss")); return fake;
}
void SetResultValue(int value) { result=value; }
int CheckActorClass(int who, const char *name) { assert(!who); return !strcmp(body,name); }
int GetPlayerMorphGen(int player) { assert(!player); return generation; }
int SetActivatorToPlayer(int player) { assert(!player); return connected; }
int PlayerIsSpectator(int player) { assert(!player); return spectator; }
void Delay(int tics) {
  assert(tics==1);
  if (interrupted==1) hp=0;
  if (interrupted==2) body="OtherBoss";
  if (interrupted==3) generation++;
  if (interrupted==4) spectator=1;
  if (interrupted==5) connected=0;
}
int FindBossByActor(const char *name) {
  if (!strcmp(name,"SPOOKYGHOSTHITLER")) return 403;
  assert(!strcmp(name,"BalladeGB")); return missing ? UHBOSS_FAIL : 68;
}
int ActivatorTID(void) { return tid; }
int UniqueTID(void) { return 2000; }
void Thing_ChangeTID(int who, int value) { assert(!who); tid=value; }
void ACS_NamedExecuteWithResult(const char *name, int who, int boss) {
  if (!strcmp(name,"uh_Health")) {
    assert(who==UHEALTH_HEAL && boss==2000);
    heals++;
    if (hp>0 && hp<cap) hp=min(hp+boss,cap);
    return;
  }
  assert(!strcmp(name,"ub_UnMorphThisTID") && who==tid && boss==403);
  cleanups++; body="Survivor"; baws=flag=0; generation++; activeboss=UHBOSS_FAIL;
}
int MorphActorToBoss(int who, int boss, const char *flash) {
  assert(who==tid); morphs++;
  if (boss==68) {
    assert(!strcmp(body,"Survivor") && cleanups==1);
    assert(!strcmp(flash,"ShinySparkleFlash"));
    if (blocked) return 0;
    body="BalladeGB"; hp=cap=11;
  } else {
    assert(boss==403 && blocked && !strcmp(flash,""));
    body="SPOOKYGHOSTHITLER"; hp=cap=2000;
  }
  baws=1; activeboss=boss; generation++; return 1;
}
void SetInventory(const char *name, int value) {
  assert(!strcmp(name,"BossSpawnHealthFlag")); spawnflag=value;
}
void GiveInventory(const char *name, int amount) {
  assert(amount==1);
  if (!strcmp(name,"TruePowerItem")) refunded++;
  else if (!strcmp(name,"TruePowerItemFlag")) flag=1;
  else {assert(!strcmp(name,"ShinySparkleItem")); sparkles++;}
}
void UH_TeamInfo_BroadcastStatus(int player, int status) {
  assert(!player && status==playerlifestatusarr[0] && activeboss==68); syncs++;
}
'''

TESTS = r'''
void Reset(void) {
  pn=0; hp=500; cap=1000; baws=flag=fake=0; generation=7; tid=1000;
  connected=1; spectator=interrupted=blocked=missing=0;
  cleanups=morphs=refunded=sparkles=syncs=result=spawnflag=heals=0;
  activeboss=403; multibosscheck=2; refreshhudmessage=false;
  body="SPOOKYGHOSTHITLER";
  bossdataarr[0][0]=1000; bossdataarr[0][1]=403;
  bossdataarr[1][0]=1001; bossdataarr[1][1]=403;
}
int main(void) {
  Reset(); flag=1; Repeat(); assert(result==1 && hp==2500 && cap==3000 && heals==1);
  Repeat(); assert(result==1 && hp==4500 && cap==5000 && heals==2);
  cap=29999; hp=500; Repeat(); assert(cap==30000 && hp==2500);
  Repeat(); assert(cap==30000 && hp==4500 && result==1);
  cap=31000; hp=500; Repeat(); assert(cap==31000 && hp==2500);
  Reset(); flag=1; hp=cap=29999; Repeat(); assert(cap==30000 && hp==30000);
  hp=29950; Repeat(); assert(cap==30000 && hp==30000);
  Repeat(); assert(cap==30000 && hp==30000 && result==1);
  hp=31000; Repeat(); assert(cap==30000 && hp==31000);
  for (int mode=0; mode<4; mode++) {
    Reset(); flag=1;
    if (mode==0) pn=-1;
    if (mode==1) hp=0;
    if (mode==2) flag=0;
    if (mode==3) baws=1;
    int before=hp;
    Repeat(); assert(!result && cap==1000 && hp==before && !heals);
  }
  Reset(); Transform();
  assert(cleanups==1 && morphs==1 && activeboss==68 && baws && flag);
  assert(sparkles==1 && !refunded && syncs==1 && refreshhudmessage);
  assert(bossdataarr[0][1]==68 && bossdataarr[1][1]==403);
  Reset(); blocked=1; Transform();
  assert(cleanups==1 && morphs==2 && activeboss==403 && hp==500 && cap==1000);
  assert(spawnflag==1000 && refunded==1 && !sparkles && !syncs);
  assert(bossdataarr[0][1]==403 && !refreshhudmessage);
  for (int mode=1; mode<=5; mode++) {
    Reset(); interrupted=mode; Transform(); assert(!cleanups && !morphs);
  }
  for (int mode=0; mode<5; mode++) {
    Reset();
    if (mode==0) pn=-1;
    if (mode==1) hp=0;
    if (mode==2) fake=1;
    if (mode==3) body="OtherBoss";
    if (mode==4) missing=1;
    Transform(); assert(!cleanups && !morphs);
  }
  Reset(); tid=0; Transform(); assert(!tid && activeboss==68 && syncs==1);
  assert(bossdataarr[0][1]==403 && bossdataarr[1][1]==403);
  puts("True Power: repeat HP cap/heal, guarded Higlur transaction and rollback PASS");
}
'''

if __name__ == '__main__':
    main()
