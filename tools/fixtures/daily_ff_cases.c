/* These assertions execute the translated production handler and pool logic. */
static int hit(str dtype) {
    current=80; event=1; active=2;
    uh_DailySurvivorTeamFF(12,100,dtype);
    event=0; return current;
}
int main(void) {
    UH_DailyFFEnsure();
    assert(uh_dailyffwant[0]==3);
    for(int p=0;p<4;p++) {
        int count=0;
        for(int i=0;i<256;i++) count+=uh_dailyffselected[p][i];
        assert(count==uh_dailyffwant[p]);
        if(p) assert(count>=6 && count<=10);
    }
    assert(!uh_dailyffselected[0][0] && !uh_dailyffselected[0][1]);
    assert(!uh_dailyffselected[0][2] && !uh_dailyffselected[0][50]);
    assert(UH_DailyFFBaselineBlocks("nEgAsUpErArM"));
    assert(!UH_DailyFFBaselineBlocks("Falling"));
    assert(!UH_DailyFFBaselineBlocks("AnUnknownAddonType"));
    assert(!strcmp(UH_DailyFFAttackWeapon("LeafSlash1",1),"LeafBladeWep"));
    assert(!strcmp(UH_DailyFFAttackWeapon("Decoy_F_04A",50),"DecoyCopy_04"));
    assert(UH_DailyFFMakeOrigin("QwantShiny","LeafBladeWep")==0);
    assert(UH_DailyFFMakeOrigin("AnUnknownAddonClass","LeafBladeWep")==0);
    int token=UH_DailyFFMakeOrigin("Qwant","LeafBladeWep");
    assert(token>0); int slot=token%1024-1;
    uh_dailyffselected[1][slot]=1;
    active=2; uh_DailyFFStamp(); assert(marker[2]==token+UH_DAILY_FF_OWNER);
    held="ToxicWep"; /* Switching weapons cannot change an existing shot. */
    assert(hit("LeafBladeSlice")==80);
    uh_dailyffselected[1][slot]=0; assert(hit("LeafBladeSlice")==0);
    uh_dailyffselected[1][slot]=1;
    copyon=0; assert(hit("LeafBladeSlice")==0); copyon=1;
    friends=0; assert(hit("LeafBladeSlice")==0); friends=1;
    sourcepn=victimpn; assert(hit("LeafBladeSlice")==0); sourcepn=0;
    sourcepn=-1; assert(hit("LeafBladeSlice")==80);
    sourcepn=0; /* The separate teamdamage handler scales recorded creators. */
    assert(hit("Suplex")==0 && hit("FlySuplex")==0 && hit("KickChamp_SlideKick")==0);
    assert(hit("NegaSuperArm")==0);
    assert(hit("Falling")==80 && hit("AnUnknownAddonType")==80);
    active=2; ret=0; uh_DailyFFCanTarget(0,0,AAPTR_TRACER); assert(ret==1);
    scale=0; active=2; uh_DailyFFCanTarget(0,0,AAPTR_TRACER); assert(ret==0); scale=65536;
    protected=0; victimpn=-1; active=2;
    uh_DailyFFCanTarget(0,0,AAPTR_TRACER); assert(ret==1); /* TID-zero NPC */
    protected=1; victimpn=1;
    protected=0; assert(hit("LeafBladeSlice")==80);
    uh_dailyffselected[1][slot]=0; assert(hit("LeafBladeSlice")==0); /* Logical Boss ally */
    postround=1; assert(hit("LeafBladeSlice")==80); postround=0;
    friends=0; assert(hit("LeafBladeSlice")==80); friends=1;
    uh_dailyffselected[1][slot]=1; protected=1;
    lms=0; assert(hit("LeafBladeSlice")==0); lms=1;
    active=2; event=1; current=0;
    uh_DailySurvivorTeamFF(12,100,"LeafBladeSlice"); assert(current==0); event=0;
    /* Static fragments retain their weapon even with no previously stamped tag. */
    marker[2]=0; held="ToxicWep"; assert(hit("LeafBladeSlice")==80);
    attack="AnUnknownProjectile"; assert(hit("LeafBladeSlice")==0);
    int classid=-1;
    for(int i=0;i<128;i++) if(uh_dailyffselected[0][i]) {classid=i; break;}
    assert(classid>=0); pawn=survivors[classid]; attack="GenericShot";
    assert(hit("Buster")==80); classon=0; assert(hit("Buster")==0); classon=1;
    pointer_owner=0; attack="StealthS_RailPuffFX1";
    assert(UH_DailyFFInstantPuff(attack));
    assert(hit("StealthRail")==80);
    classon=0; assert(hit("StealthRail")==0); classon=1;
    attack="UnknownPuff"; assert(hit("StealthRail")==0); pointer_owner=1;
    /* Tiny pools and disabled counts never overrun the candidate array. */
    cfglo=300; cfghi=300; cfgclasses=300; UH_DailyFFEnsure();
    for(int p=0;p<4;p++) assert(uh_dailyffwant[p]==uh_dailyffsize[p]);
    cfglo=0; cfghi=0; cfgclasses=0; UH_DailyFFEnsure();
    for(int p=0;p<4;p++) assert(uh_dailyffwant[p]==0);
    cfglo=6; cfghi=10; cfgclasses=3; date++; UH_DailyFFEnsure();
    assert(uh_dailyffdate==date && uh_dailyffwant[0]==3);
    /* Every multi-weapon pool accepts its selected held weapon for hitscan. */
    for(int pool=1;pool<4;pool++) {
        int index=-1;
        for(int i=0;i<256;i++) if(uh_dailyffselected[pool][i]) {index=i; break;}
        assert(index>=0);
        int id=pool==3 ? 50 : pool;
        pawn=survivors[id]; held=UH_DailyFFWeapon(pool,index); hitscan=1;
        assert(hit(pool==1 ? "LeafBladeSlice" : pool==2 ? "NegaBuster" : "DecoyBot")==80);
        uh_dailyffselected[pool][index]=0;
        assert(hit(pool==1 ? "LeafBladeSlice" : pool==2 ? "NegaBuster" : "DecoyBot")==0);
        uh_dailyffselected[pool][index]=1;
    }
    /* Rebuilding with identical inputs reproduces the same pools. */
    int saved[4][256]; memcpy(saved,uh_dailyffselected,sizeof(saved));
    uh_dailyffdate=0; UH_DailyFFEnsure();
    assert(!memcmp(saved,uh_dailyffselected,sizeof(saved)));
    /* Addons opt in explicitly; IDs cannot alias a Shiny or vanilla class. */
    ret=0; uh_RegisterDailyFFClass("AddonOneShiny"); assert(ret==0);
    uh_RegisterDailyFFClass("Qwant"); assert(ret==0);
    uh_RegisterDailyFFClass("AddonOne"); assert(ret==129);
    uh_RegisterDailyFFClass("addonone"); assert(ret==129 && uh_dailyffaddoncount==1);
    uh_RegisterDailyFFClass("AddonTwo"); assert(ret==130 && uh_dailyffaddoncount==2);
    int oldsize=uh_dailyffsize[0]; UH_DailyFFEnsure(); assert(uh_dailyffsize[0]==oldsize+2);
    uh_RegisterDailyFFDamageType("AddonDamage");
    uh_RegisterDailyFFDamageType("addondamage"); assert(uh_dailyffaddontypecount==1);
    assert(UH_DailyFFBaselineBlocks("AddonDamage"));
    pawn="AddonOne"; attack="AddonProjectile"; hitscan=0; marker[2]=0;
    token=UH_DailyFFMakeOrigin(pawn,""); assert(token==129*1024);
    assert(UH_DailyFFMakeOrigin("AddonOneShiny","")==0);
    uh_dailyffselected[0][128]=1;
    active=2; uh_DailyFFStamp(); assert(marker[2]==token+UH_DAILY_FF_OWNER);
    assert(hit("AddonDamage")==80);
    friends=0;assert(hit("AddonDamage")==80);friends=1;
    sourcepn=victimpn;assert(hit("AddonDamage")==80);sourcepn=0;
    pawn="AddonOneShiny"; assert(hit("AddonDamage")==80); /* Frozen normal shot. */
    uh_dailyffselected[0][128]=0; assert(hit("AddonDamage")==0);
    uh_dailyffselected[0][128]=1; classon=0; assert(hit("AddonDamage")==0);classon=1;
    marker[2]=1; assert(hit("AddonDamage")==0); /* Frozen excluded origin. */
    marker[2]=token+UH_DAILY_FF_OWNER; sourcepn=-1;assert(hit("AddonDamage")==80);sourcepn=0;
    /* Registration overflow is rejected without corrupting existing slots. */
    uh_dailyffaddoncount=127;
    for(int i=2;i<127;i++)uh_dailyffaddonactor[i]="ReservedAddon";
    uh_dailyffaddonactor[126]="LastAddon";
    uh_RegisterDailyFFClass("AddonTwo"); assert(ret==130);
    uh_RegisterDailyFFClass("AddonThree"); assert(ret==0 && uh_dailyffaddoncount==127);
    token=UH_DailyFFMakeOrigin("LastAddon","");
    assert(token==255*1024 && token/UH_DAILY_FF_OWNER==0);
    uh_dailyffaddoncount=2;
    puts("Daily FF: pool counts, clamping, baseline immunity, provenance, safe interactions and rollover PASS");
    return 0;
}
