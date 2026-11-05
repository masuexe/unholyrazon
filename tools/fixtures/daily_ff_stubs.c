/* Engine/registry stubs for the actual daily_team_ff.acs policy. */
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdint.h>
typedef const char *str;
#define UH_MAX_VANILLA_SURV 128
#define UHCOPY_QWANT 2
#define UHCOPY_NEGA 3
#define GAMEEVENT_ACTOR_DAMAGED_PREMOD 12
#define AAPTR_TARGET 2
#define AAPTR_MASTER 4
#define AAPTR_TRACER 8
#define AAPTR_DAMAGE_TARGET 16
#define AAPTR_DAMAGE_SOURCE 32
#define AAPTR_DAMAGE_INFLICTOR 64
#define APROP_TargetTID 26
int max(int a, int b) {return a > b ? a : b;}
int min(int a, int b) {return a < b ? a : b;}
int FixedMul(int a,int b) {return (int)(((int64_t)a*b)>>16);}
int StrLen(str s) {return strlen(s);}
int GetChar(str s, int i) {return s[i];}
int StrICmp(str a, str b) {
    while (*a && tolower(*a) == tolower(*b)) {a++; b++;}
    return tolower(*a) - tolower(*b);
}
str StrLeft(str s, int n) {static char b[256]; memcpy(b,s,n); b[n]=0; return b;}
str UH_DecoyMoveStem(str s) {
    static char b[256]; strcpy(b,s); int n=strlen(b);
    if (n >= 3 && b[n-3]=='_' && b[n-2]=='W') b[n-3]=0;
    else if (n >= 2 && b[n-2]=='_' && b[n-1]=='W') b[n-2]=0;
    return b;
}
str decoy_name(str actor) {static char b[32]; snprintf(b,sizeof(b),"DecoyCopy_%c%c",actor[8],actor[9]); return b;}
extern str qw[], ng[], survivors[128], uh_decoymovewep[256][3];
int CountCopyWepByKind(int kind);
int CountDecoyBotSlots(void);
str GetCopyWepActorByKindIndex(int kind, int i) {return kind==2 ? qw[i] : ng[i];}
int IsSurvivorDefined(int i) {return i==-1 || i==-2 || i==-3 || (i>=0 && i<128 && survivors[i]!=NULL);}
str GetSurvivorActor(int i) {return survivors[i] ? survivors[i] : "";}
int FindSurvivorByActor(str name) {if(!StrICmp(name,"AddonOne"))return -1; if(!StrICmp(name,"AddonTwo"))return -2; if(!StrICmp(name,"AddonThree"))return -3; for(int i=0;i<128;i++) if(survivors[i] && !StrICmp(name,survivors[i])) return i; return -9999;}
int date=20261105, cfglo=6, cfghi=10, cfgclasses=3, copyon=1, classon=1;
int lms=1, scale=65536, friends=1, active=2, marker[4], protected=1, current=80;
int postround=0;
int pointer_owner=1;
int ret=0, event=0, hitscan=0, inflictor_present=1, sourcepn=0, victimpn=1;
str pawn="Qwant", held="LeafBladeWep", attack="LeafSlash1";
int UH_DateToInt(void) {return date;}
int UH_MegaDailyRandom(int seed, int lo, int hi) {return lo+(seed & 0x7fffffff)%(hi-lo+1);}
int GetCVar(str name) {
    if(!strcmp(name,"lastmanstanding")) return lms;
    if(!strcmp(name,"teamdamage")) return scale;
    if(!strcmp(name,"rz_sv_copy_ff_count_min")) return cfglo;
    if(!strcmp(name,"rz_sv_copy_ff_count_max")) return cfghi;
    if(!strcmp(name,"rz_sv_class_ff_count")) return cfgclasses;
    if(!strcmp(name,"rz_sv_randcopywepteamkill")) return copyon;
    if(!strcmp(name,"rz_sv_randclassteamkill")) return classon;
    assert(0); return 0;
}
int GetEventResult(void) {return current;}
void SetResultValue(int value) {ret=value; if(event) current=value;}
int SetActivator(int tid, int ptr) {
    if(tid) {active=tid==1000 ? 1 : 0; return 1;}
    if(ptr==16) active=0;
    else if(ptr==32) active=1;
    else if(ptr==64) {if(!inflictor_present)return 0; active=hitscan ? 1 : 2;}
    else if(ptr==2 || ptr==4) {if(!pointer_owner)return 0; active=1;}
    else if(ptr==8) active=0;
    else return 0;
    return 1;
}
int PlayerNumber(void) {return active==0 ? victimpn : active==1 ? sourcepn : -1;}
int PlayerInGame(int pn) {return pn>=0 && pn<64;}
int ActivatorTID(void) {return active==0 && victimpn>=0 ? 1001 : active==1 ? 1000 : 0;}
int CheckInventory(str name) {return !strcmp(name,"PowerProtectSurvivor") ? (active==0 && protected) : marker[active];}
int CheckActorInventory(int tid, str name) {return tid==1001 && protected;}
int GetActorProperty(int tid,int prop) {return 1000;}
str GetActorClass(int tid) {return active==1 ? pawn : attack;}
str GetWeapon(void) {return held;}
int IsPointerEqual(int a,int b) {return hitscan;}
void GiveInventory(str name,int amount) {marker[active]=amount;}
void uh_DailyFFPointerOrigin(int ptr,str attack);
void uh_DailyFFStamp(void);
void uh_DailyFFProtectedPointer(int ptr);
int ACS_NamedExecuteWithResult(str name,...) {
    int oldactive=active, oldevent=event, oldret=ret; event=0; ret=0;
    va_list args; va_start(args,name);
    if(!strcmp(name,"uh_DailyFFPointerOrigin")) {
        int ptr=va_arg(args,int); str actor=va_arg(args,str); uh_DailyFFPointerOrigin(ptr,actor);
    } else if(!strcmp(name,"uh_DailyFFStamp")) uh_DailyFFStamp();
    else if(!strcmp(name,"uh_DailyFFProtectedPointer")) uh_DailyFFProtectedPointer(va_arg(args,int));
    else if(!strcmp(name,"uh_AreGameplayTeammates")) ret=friends;
    else if(!strcmp(name,"uh_IsPostRoundFriendlyFire")) ret=postround;
    else assert(0);
    va_end(args); int value=ret; active=oldactive; event=oldevent; ret=oldret; return value;
}
