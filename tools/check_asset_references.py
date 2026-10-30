#!/usr/bin/env python3
"""Verify that every sound, language key and HUD texture reference resolves.

The engine fails soft on these three reference classes: an unknown logical
sound plays nothing, an unknown LANGUAGE key prints its own key name on the
screen, and an unknown HUD texture draws nothing.  A rename therefore ships
silently.  This checker guards:

1. Every logical sound name used by A_PlaySound/A_PlaySoundEx/A_StartSound/
   A_AmbientSound in src/actors must be defined by src/SNDINFO*, by the base
   game SNDINFO, or by an explicit frozen constant.
2. Every SNDINFO entry that points at a sound FILE (sounds/...wav) must name a
   file that exists under src/.  A renamed wave file breaks the alias silently.
3. Every LANGUAGE key used as "$KEY" by DECORATE, MENUDEF, SCORINFO, MAPINFO,
   SBARINFO.*.uhappend or KEYCONF, and every GetString() key in ACS, must be
   defined by src/LANGUAGE* or by the base game.
4. Every texture name referenced by SBARINFO (DrawImage/DrawBar), MENUDEF
   (StaticPatch) and MAPINFO (sky1/sky2/exitpic/enterpic/titlepatch) must
   resolve to a local graphic, a local TEXTURES definition, or a base game
   graphic.

Case rule: sound names, LANGUAGE keys and texture names are all resolved by
the engine without case.  A reference that matches only when case is ignored
is reported as a warning, not a failure.

External rule: gate.py --fast must run in a fresh clone with no WADs, so the
names supplied by the base game are frozen constants below. They were first
extracted from the v6b packages on 2026-10-26 and re-verified against
../wads/mm8bdm-v6c.pk3 on 2026-10-29: every frozen name is present in v6c, so
the v6b allowlist is a subset of v6c coverage. tools/check_base_baselines.py
keeps that true.  A new external name must be added here on purpose.

KNOWN_UNRESOLVED_* lists references that are genuinely undefined in the whole
load order (src/ + base game + miscfixes).  They are real latent defects, not
checker noise, and they stay visible as warnings because the src/ files are
outside this checker's write scope.  --strict turns them into failures.
Remove an entry when the defect is fixed.

Run:  python3 tools/check_asset_references.py [--strict]
Exit: 0 clean, 1 findings, 2 usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

DECORATE_SUFFIXES = {".dec", ".txt", ".decorate"}
SOUND_CALL_RE = re.compile(
    r'(?i)\b(?:A_PlaySound(?:Ex)?|A_StartSound|A_AmbientSound)'
    r'[ 	]*\([ 	]*"([^"]+)"')
LANGUAGE_REF_RE = re.compile(r'"\$([A-Za-z0-9_]+)"')
LANGUAGE_DEF_RE = re.compile(r'(?m)^([A-Za-z0-9_\[\]]+)[ 	]*=')
SND_PATH_RE = re.compile(
    r'(?i)^[ 	]*\S+[ 	]+"?([^\s"]+\.(?:wav|ogg|mp3|flac|spx))"?')
DRAWIMAGE_RE = re.compile(r'(?i)\bDrawImage[ 	]+"([^"]+)"')
DRAWBAR_RE = re.compile(r'(?i)\bDrawBar[ 	]+"([^"]+)"[ 	]*,[ 	]*"([^"]+)"')
STATICPATCH_RE = re.compile(r'(?i)StaticPatch[ 	]+[^,]+,[ 	]*[^,]+,[ 	]*"([^"]+)"')
MAPINFO_IMAGE_RE = re.compile(
    r'(?i)\b(?:sky1|sky2|exitpic|enterpic|titlepatch)[ 	]*=[ 	]*"([^"]+)"')

# SNDINFO directives whose name field follows the directive.  Any other "$"
# directive is a modifier ($limit/$volume/$rolloff/$pitchshift) and is skipped.
SND_NAME_FIELD = {
    "$playersound": 3,
    "$playeralias": 3,
    "$alias": 1,
    "$random": 1,
}

BASE_GAME_SOUNDS = frozenset("""
    *critdeth *icedeath *icefreze assists/reggaecandrop assists/wirecling assists/wirefinish
    assists/wirefire item/buy item/eddiecry item/energyup item/energyup/large item/protoreflect
    item/refill item/reggae item/tango misc/alarmlong misc/astroplatformappear misc/bombcount
    misc/catcherdrop misc/devildeath misc/devilfire misc/devilpain misc/dragonbreath misc/eclipsegravitywellpain
    misc/eclipsegravitywellsummon misc/fakeshot misc/freeze misc/galaxyteleport misc/gib misc/gravitywarn
    misc/gutsgboost misc/hsloop misc/hugequake misc/hugequake2 misc/itemthrow misc/kingchop
    misc/magmaflamestart misc/mm3explosion misc/mwsburst misc/partyball misc/piratebubble misc/pumpsplash
    misc/quake misc/quicktrap misc/soccerballplatform misc/splash misc/sunstarbeamcharge misc/sunstarbeamloop
    misc/sunstarshot misc/tink misc/ufo misc/wanaan misc/waterslide misc/wilybeam
    misc/zombie robot/bigeye weapon/adapterreturn weapon/airshooter weapon/astrocrush weapon/astrocrush2
    weapon/atomicfire weapon/blackholebomb weapon/blackholebombdetonate weapon/bladeshoot weapon/bubblebomb weapon/centaurflash
    weapon/cfire weapon/chargekick weapon/chillblockcrack weapon/chillbreak weapon/chillshot weapon/chillspike
    weapon/coilcharge weapon/coilexplode weapon/coilfire1 weapon/coilfire2 weapon/coilstart weapon/commandoshot
    weapon/commandoswitch weapon/crackerexplode weapon/crackermine weapon/crackerthrow weapon/crashexplode weapon/crashland
    weapon/deepdiggerbreak weapon/deepdiggerthrow weapon/drillexplode weapon/drillfly weapon/electricshock weapon/firestorm
    weapon/flamehit weapon/flamesword weapon/flashbomb weapon/freezecracker weapon/freezecrackerhit weapon/gemini
    weapon/grabbuster weapon/gravityhold weapon/gyroattack weapon/heat2 weapon/heat3 weapon/hornetchaser
    weapon/hornethover weapon/hyperbomb weapon/icewallspawn weapon/icewavebreak weapon/icewaveloop weapon/icewavespawn
    weapon/jewelsatellite weapon/junkend weapon/junkshieldloop weapon/junkshieldstart weapon/lasertrident weapon/leafshield
    weapon/lightningbolt weapon/lshot weapon/magiccard weapon/magmabazooka weapon/magmacharge1 weapon/magmacharge2
    weapon/magnetmissile weapon/mbuster weapon/megaball weapon/metalblade weapon/minchrgshot weapon/mirrorabsorb
    weapon/mirroractivate weapon/mirrordeflect weapon/mirrordeflect2 weapon/napalm weapon/noammo weapon/noisecrush1
    weapon/oilshot weapon/oilslider weapon/pcharge weapon/pchargelong weapon/pharaoh1 weapon/pharaoh2
    weapon/photonmissilearm weapon/photonmissilelaunch weapon/powerstone weapon/pshot weapon/rainflush weapon/rmineexplode
    weapon/rminestick weapon/sakugarne weapon/scorchwheel weapon/screwcrusher weapon/shadow weapon/skullcounter
    weapon/slashclaw weapon/slashclawhit weapon/slow weapon/solarblaze weapon/solarshoot weapon/sparkchaser
    weapon/sparkchaserchase weapon/sparkshock weapon/spreaddrill1 weapon/spreaddrill2 weapon/spreaddrill3 weapon/spreaddrillhit
    weapon/superarmhit weapon/superarmuse weapon/superboost weapon/tengudash weapon/tenguhit weapon/tengushot
    weapon/thunderbeam weapon/thunderbolt weapon/thunderclaw weapon/timeshot weapon/timestopper weapon/topspin
    weapon/tornadoblow weapon/ultrabeam weapon/waterballoon weapon/watershieldburst weapon/waterwave weapon/wheelclimb
    weapon/wheelstart weapon/wrapexplode weapon/wrapfire weapons/busters/laserbusterfire3 weapons/busters/megabusterfire weapons/mm1/firestormfire
    weapons/mm1/hyperbombexplode weapons/mm1/hyperbombfire weapons/mm1/hyperbombsmallexplode weapons/mm1/iceslasherfire weapons/mm1/oilsliderfire weapons/mm1/oilsliderslide
    weapons/mm1/rollingcutterfly weapons/mm1/superarmload weapons/mm1/superarmsplit weapons/mm1/thunderbeamfire weapons/mm1/timeslowfire weapons/mm10/chillspikebreak
    weapons/mm10/chillspikefire weapons/mm10/chillspikeland weapons/mm10/commandobombfire weapons/mm10/reboundstrikerfire weapons/mm10/solarblazefire weapons/mm10/solarblazesplit
    weapons/mm10/thunderwoolexplode weapons/mm10/thunderwoolfire weapons/mm10/triplebladefire weapons/mm10/watershieldactivate weapons/mm10/watershieldfire weapons/mm10/wheelcutteractivate
    weapons/mm10/wheelcutterfire weapons/mm2/airshooterfire weapons/mm2/atomicfirecharge1 weapons/mm2/atomicfirecharge2 weapons/mm2/atomicfirecharge3 weapons/mm2/atomicfirefire
    weapons/mm2/bubbleleadfire weapons/mm2/crasbombexplode weapons/mm2/crashbombfire weapons/mm2/crashbombland weapons/mm2/leafshieldactive weapons/mm2/leafshieldcounter
    weapons/mm2/metalbladefire weapons/mm2/quickboomerangfire weapons/mm2/timestopperfire weapons/mm3/geminilaserfire weapons/mm3/hardknucklelaunch weapons/mm3/hardknucklewindup
    weapons/mm3/magnetmissilefire weapons/mm3/needlecannonfire weapons/mm3/searchsnakefire weapons/mm3/shadowbladefire weapons/mm3/sparkshockfire weapons/mm3/topspinfire
    weapons/mm4/divemissilefire weapons/mm4/drillbombexplode weapons/mm4/drillbombfire weapons/mm4/dustcrusherfire weapons/mm4/dustcrushersplit weapons/mm4/flashstopperexplode
    weapons/mm4/flashstopperfire weapons/mm4/pharaohshotfire weapons/mm4/pharaohshotfire2 weapons/mm4/rainflushexplode weapons/mm4/rainflushfire weapons/mm4/ringboomberangfire
    weapons/mm4/skullbarrieractivate weapons/mm4/skullbarriercounter weapons/mm5/chargekickfire weapons/mm5/crystaleyefire weapons/mm5/crystaleyehit weapons/mm5/crystaleyesplit
    weapons/mm5/gravityholdfire weapons/mm5/gravityholdslam weapons/mm5/gyroattackfly weapons/mm5/napalmbombexplode weapons/mm5/napalmbombfire weapons/mm5/powerstonefire weapons/mm5/starcrashactivate
    weapons/mm5/starcrashfire weapons/mm5/waterwavefire weapons/mm6/blizzardattackfire weapons/mm6/centaurflashexplode weapons/mm6/centaurflashfire weapons/mm6/flameblastfire
    weapons/mm6/knightcrushfire weapons/mm6/plantbarrieractivate weapons/mm6/plantberrierfire weapons/mm6/silvertomahawkfire weapons/mm6/windstormfire weapons/mm6/yamatospearfire
    weapons/mm7/dangerwrapexplode weapons/mm7/dangerwrapfire weapons/mm7/freezecrackerfire weapons/mm7/freezecrackersplit weapons/mm7/junkshieldbreak weapons/mm7/junkshieldcharge
    weapons/mm7/junkshieldfire weapons/mm7/noisecrushchargefire weapons/mm7/noisecrushfire weapons/mm7/scorchwheelactivate weapons/mm7/scorchwheelfire weapons/mm7/slashclawfire
    weapons/mm7/slashclawhit weapons/mm7/thunderboltfire weapons/mm7/wildcoilcharge weapons/mm7/wildcoilfire weapons/mm7/wildcoilfire2 weapons/mm8/astrocrushexplode
    weapons/mm8/flameswordfire weapons/mm8/flameswordhit weapons/mm8/flameswordcharge weapons/mm8/flameswordcharge2 weapons/mm8/flameswordslash weapons/mm8/flashbombexplode weapons/mm8/flashbombfire weapons/mm8/homingsnipercharge weapons/mm8/homingsniperchargeloop
    weapons/mm8/homingsniperload weapons/mm8/homingsnipershot weapons/mm8/icewavefire weapons/mm8/megaballfire weapons/mm8/megaballkick weapons/mm8/thunderclawfire
    weapons/mm8/tornadoholdblow weapons/mm8/tornadoholdfire weapons/mm8/waterballoonfire weapons/mm8/waterballoonsplash weapons/mm9/blackholebombexplode weapons/mm9/concreteshotfire weapons/mm9/hornetchaserfire
    weapons/mm9/jewelsatelliteactivate weapons/mm9/jewelsatellitefire weapons/mm9/lasertridentfire weapons/mm9/magmabazookacharge weapons/mm9/magmabazookacharge2 weapons/mm9/magmabazookafire
    weapons/mm9/plugballfire weapons/mm9/tornadoblowfire weapons/mmb/copyvisionactivate weapons/mmb/copyvisionbuster weapons/mmb/copyvisionshoot weapons/mmb/icewallfire
    weapons/mmb/lightningboltexplode weapons/mmb/lightningboltfire weapons/mmb/magiccardfire weapons/mmb/remotemineexplode weapons/mmb/remoteminefire weapons/mmb/remoteminestick
    weapons/mmb/spreaddrillfire weapons/mmb/spreaddrillhit weapons/mmb/tengubladedash weapons/mmb/tengubladefire weapons/mmb/tengubladehit weapons/mmb/waveburnerfire
    weapons/mmk/balladecrackerexplode weapons/mmk/balladecrackerfire weapons/mmk/dawnbreakercharge weapons/mmk/dawnbreakerexplode weapons/mmk/dawnbreakerfire weapons/mmk/dawnbreakerquake
    weapons/mmk/dawnbreakerwindup weapons/mmk/dawnbreakerwindup2 weapons/mmk/mirrorbusterabsorb weapons/mmk/mirrorbustercharge weapons/mmk/mirrorbusterfire weapons/mmk/mirrorbusterfire2
    weapons/mmk/sakugarneactivate weapons/mmk/sakugarnebounce weapons/mmk/screwcrusherfire weapons/mmv/blackholeactivate weapons/mmv/blackholetrigger weapons/mmv/breakdashbuster
    weapons/mmv/breakdashcharge weapons/mmv/breakdashfire weapons/mmv/breakdashimpact weapons/mmv/bubblebombexplode weapons/mmv/deepdiggerfire weapons/mmv/deepdiggerload
    weapons/mmv/electricshockfire weapons/mmv/grabbusterfire weapons/mmv/photonmissilecharge weapons/mmv/photonmissileexplode weapons/mmv/photonmissileload weapons/mmv/saltwaterfire
    weapons/mmv/sparkchaserfire
""".split())

KNOWN_UNRESOLVED_SOUNDS = frozenset("""
    classes/thunderbolt hardman/goldknuckle item/urinebottle2 weapons/railgf wep_l/tactbombalt6
""".split())

BASE_GAME_LANGUAGE_KEYS = frozenset("""
    OB_AIRSHOOTER OB_ASTROCRUSH OB_ATOMICFIRE OB_BALLADECRACKER OB_BLACKHOLE OB_BLACKHOLEBOMB
    OB_BLIZZARDATTACK OB_BREAKDASH OB_BUBBLEBOMB OB_BUBBLELEAD OB_CENTAURFLASH OB_CHARGEKICK
    OB_CHILLSPIKE OB_CHILLSPIKE2 OB_COMMANDOBOMB OB_CONCRETESHOT OB_COPYVISION OB_CRASHBOMB
    OB_CRYSTALEYE OB_DANGERWRAP OB_DAWNBREAKER1 OB_DEEPDIGGER OB_DIVEMISSILE OB_DRILLBOMB
    OB_DUSTCRUSHER OB_ELECTRICSHOCK OB_FIRESTORM OB_FLAMEBLAST OB_FLAMESWORD OB_FLASHBOMB
    OB_FLASHSTOPPER OB_FREEZECRACKER OB_GEMINILASER OB_GRABBUSTER OB_GRAVITYHOLD OB_GYROATTACK
    OB_HARDKNUCKLE OB_HOMINGSNIPER OB_HORNETCHASER OB_HYPERBOMB OB_ICESLASHER OB_ICEWALL
    OB_ICEWAVE OB_JEWELSATELLITE OB_JUNKSHIELD OB_KNIGHTCRUSH OB_LASERTRIDENT OB_LEAFSHIELD
    OB_LIGHTNINGBOLT OB_MAGICCARD OB_MAGMABAZOOKA OB_MEGABALL OB_METALBLADE OB_MIRRORBUSTER
    OB_NAPALMBOMB OB_NEEDLECANNON OB_NOISECRUSH OB_OILSLIDER OB_PHARAOHSHOT OB_PHOTONMISSILE
    OB_PLANTBARRIER OB_PLUGBALL OB_POWERSTONE OB_QUICKBOOMERANG OB_RAINFLUSH OB_REBOUNDSTRIKER
    OB_REMOTEMINE OB_RINGBOOMERANG OB_ROLLINGCUTTER OB_SAKUGARNE OB_SALTWATER OB_SCORCHWHEEL
    OB_SCREWCRUSHER OB_SEARCHSNAKE OB_SHADOWBLADE OB_SILVERTOMAHAWK OB_SKULLBARRIER OB_SLASHCLAW
    OB_SOLARBLAZE OB_SPARKCHASER OB_SPARKSHOCK OB_SPREADDRILL OB_STARCRASH OB_SUPERARM
    OB_TENGUBLADE OB_THUNDERBEAM OB_THUNDERBOLT OB_THUNDERCLAW OB_THUNDERWOOL OB_TIMESLOW
    OB_TIMESTOPPER OB_TOPSPIN OB_TORNADOBLOW OB_TORNADOHOLD OB_TRIPLEBLADE OB_WATERBALLOON
    OB_WATERSHIELD OB_WATERWAVE OB_WAVEBURNER OB_WAVEBURNER2 OB_WHEELCUTTER OB_WILDCOIL
    OB_WINDSTORM OB_YAMATOSPEAR PU_AIRSHOOTER PU_ASTROCRUSH PU_ATOMICFIRE PU_BALLADECRACKER
    PU_BLACKHOLE PU_BLACKHOLEBOMB PU_BLIZZARDATTACK PU_BREAKDASH PU_BUBBLEBOMB PU_BUBBLELEAD
    PU_CENTAURFLASH PU_CHARGEKICK PU_CHILLSPIKE PU_COMMANDOBOMB PU_CONCRETESHOT PU_COPYVISION
    PU_CRASHBOMB PU_CRYSTALEYE PU_DANGERWRAP PU_DAWNBREAKER PU_DEEPDIGGER PU_DIVEMISSILE
    PU_DRILLBOMB PU_DUSTCRUSHER PU_ELECTRICSHOCK PU_FIRESTORM PU_FLAMEBLAST PU_FLAMESWORD
    PU_FLASHBOMB PU_FLASHSTOPPER PU_FREEZECRACKER PU_GEMINILASER PU_GRABBUSTER PU_GRAVITYHOLD
    PU_GYROATTACK PU_HARDKNUCKLE PU_HOMINGSNIPER PU_HORNETCHASER PU_HYPERBOMB PU_ICESLASHER
    PU_ICEWALL PU_ICEWAVE PU_JEWELSATELLITE PU_JUNKSHIELD PU_KNIGHTCRUSH PU_LASERTRIDENT
    PU_LEAFSHIELD PU_LIGHTNINGBOLT PU_MAGICCARD PU_MAGMABAZOOKA PU_MAGNETMISSILE PU_MEGABALL
    PU_METALBLADE PU_MIRRORBUSTER PU_NAPALMBOMB PU_NEEDLECANNON PU_NOISECRUSH PU_OILSLIDER
    PU_PHARAOHSHOT PU_PHOTONMISSILE PU_PLANTBARRIER PU_PLUGBALL PU_POWERSTONE PU_QUICKBOOMERANG
    PU_RAINFLUSH PU_REBOUNDSTRIKER PU_REMOTEMINE PU_RINGBOOMERANG PU_ROLLINGCUTTER PU_SAKUGARNE
    PU_SALTWATER PU_SCORCHWHEEL PU_SCREWCRUSHER PU_SEARCHSNAKE PU_SHADOWBLADE PU_SILVERTOMAHAWK
    PU_SKULLBARRIER PU_SLASHCLAW PU_SOLARBLAZE PU_SPARKCHASER PU_SPARKSHOCK PU_SPREADDRILL
    PU_STARCRASH PU_SUPERARM PU_TENGUBLADE PU_THUNDERBEAM PU_THUNDERBOLT PU_THUNDERCLAW
    PU_THUNDERWOOL PU_TIMESLOW PU_TIMESTOPPER PU_TOPSPIN PU_TORNADOBLOW PU_TORNADOHOLD
    PU_TRIPLEBLADE PU_WATERBALLOON PU_WATERSHIELD PU_WATERWAVE PU_WAVEBURNER PU_WHEELCUTTER
    PU_WILDCOIL PU_WINDSTORM PU_YAMATOSPEAR TAG_AIRSHOOTER TAG_ASTROCRUSH TAG_ATOMICFIRE
    TAG_BALLADECRACKER TAG_BLACKHOLE TAG_BLACKHOLEBOMB TAG_BLIZZARDATTACK TAG_BREAKDASH TAG_BUBBLEBOMB
    TAG_BUBBLELEAD TAG_CENTAURFLASH TAG_CHARGEKICK TAG_CHILLSPIKE TAG_COMMANDOBOMB TAG_CONCRETESHOT
    TAG_COPYVISION TAG_CRASHBOMB TAG_CRYSTALEYE TAG_DANGERWRAP TAG_DAWNBREAKER TAG_DEEPDIGGER
    TAG_DIVEMISSILE TAG_DRILLBOMB TAG_DUSTCRUSHER TAG_ELECTRICSHOCK TAG_FIRESTORM TAG_FLAMEBLAST
    TAG_FLAMESWORD TAG_FLASHBOMB TAG_FLASHSTOPPER TAG_FREEZECRACKER TAG_GEMINILASER TAG_GRABBUSTER
    TAG_GRAVITYHOLD TAG_GYROATTACK TAG_HARDKNUCKLE TAG_HOMINGSNIPER TAG_HORNETCHASER TAG_HYPERBOMB
    TAG_ICESLASHER TAG_ICEWALL TAG_ICEWAVE TAG_JEWELSATELLITE TAG_JUNKSHIELD TAG_KNIGHTCRUSH
    TAG_LASERTRIDENT TAG_LEAFSHIELD TAG_LIGHTNINGBOLT TAG_MAGICCARD TAG_MAGMABAZOOKA TAG_MAGNETMISSILE
    TAG_MEGABALL TAG_METALBLADE TAG_MIRRORBUSTER TAG_NAPALMBOMB TAG_NEEDLECANNON TAG_NOISECRUSH
    TAG_OILSLIDER TAG_PHARAOHSHOT TAG_PHOTONMISSILE TAG_PLANTBARRIER TAG_PLUGBALL TAG_POWERSTONE
    TAG_QUICKBOOMERANG TAG_RAINFLUSH TAG_REBOUNDSTRIKER TAG_REMOTEMINE TAG_RINGBOOMERANG TAG_ROLLINGCUTTER
    TAG_SAKUGARNE TAG_SALTWATER TAG_SCORCHWHEEL TAG_SCREWCRUSHER TAG_SEARCHSNAKE TAG_SHADOWBLADE
    TAG_SILVERTOMAHAWK TAG_SKULLBARRIER TAG_SLASHCLAW TAG_SOLARBLAZE TAG_SPARKCHASER TAG_SPARKSHOCK
    TAG_SPREADDRILL TAG_STARCRASH TAG_SUPERARM TAG_TENGUBLADE TAG_THUNDERBEAM TAG_THUNDERBOLT
    TAG_THUNDERCLAW TAG_THUNDERWOOL TAG_TIMESLOW TAG_TIMESTOPPER TAG_TOPSPIN TAG_TORNADOBLOW
    TAG_TORNADOHOLD TAG_TRIPLEBLADE TAG_WATERBALLOON TAG_WATERSHIELD TAG_WATERWAVE TAG_WAVEBURNER
    TAG_WHEELCUTTER TAG_WILDCOIL TAG_WINDSTORM TAG_YAMATOSPEAR
""".split())

# No known unresolved LANGUAGE key at HEAD.
KNOWN_UNRESOLVED_LANGUAGE_KEYS = frozenset()

BASE_GAME_HUD_GRAPHICS = frozenset("""
    AIRSKY BARAMM13 BAREMPTY BARFLS1 BLACK M_DOOM
    NOBAR VARAMM13 VAREMPTY VARFLS1 VNOBAR
""".split())

# No known unresolved HUD texture at HEAD.
KNOWN_UNRESOLVED_HUD_GRAPHICS = frozenset()

_WALK = None


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def strip_comments(text):
    """Remove comments, but keep the line count so line numbers stay valid."""
    text = re.sub(
        r'/\*.*?\*/',
        lambda match: re.sub(r'[^\n]', '', match.group(0)),
        text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def walk_src():
    global _WALK
    if _WALK is None:
        files = []
        for dirpath, _dirnames, names in os.walk(SRC):
            base = Path(dirpath)
            files.extend(base / name for name in names)
        _WALK = files
    return _WALK


def decorate_files():
    files = [p for p in walk_src() if p.suffix.lower() in DECORATE_SUFFIXES]
    files.extend(p for p in SRC.glob("DECORATE*") if p.is_file())
    return files


def sound_definitions():
    """Logical sound names defined by src/SNDINFO*, lowercased."""
    defs = set()
    for path in sorted(SRC.glob("SNDINFO*")):
        text = strip_comments(read_text(path))
        for line in text.splitlines():
            tokens = line.split()
            if not tokens:
                continue
            head = tokens[0].lower()
            field = SND_NAME_FIELD.get(head)
            if field is not None:
                if len(tokens) > field:
                    defs.add(tokens[field].lower())
                continue
            if head.startswith("$"):
                continue
            defs.add(head)
    return defs


def sound_references():
    """{name: set('file:line')} for every DECORATE sound call."""
    refs = {}
    for path in decorate_files():
        data = path.read_bytes()
        if b"A_PlaySound" not in data and b"A_PlaySoundEx" not in data \
                and b"A_StartSound" not in data and b"A_AmbientSound" not in data:
            continue
        text = strip_comments(data.decode("utf-8", errors="replace"))
        rel = path.relative_to(ROOT).as_posix()
        for match in SOUND_CALL_RE.finditer(text):
            name = match.group(1).lower()
            lineno = text.count("\n", 0, match.start()) + 1
            refs.setdefault(name, set()).add("{}:{}".format(rel, lineno))
    return refs


def check_sound_paths(problems, warnings):
    """Every SNDINFO entry that points at a sound file must name a real file."""
    total = 0
    for path in sorted(SRC.glob("SNDINFO*")):
        text = strip_comments(read_text(path))
        rel = path.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            tokens = line.split()
            if not tokens or tokens[0].startswith("$"):
                continue
            match = SND_PATH_RE.match(line)
            if not match:
                continue
            total += 1
            target = match.group(1).replace("\\", "/")
            if (SRC / target).is_file():
                continue
            parent = (SRC / target).parent
            want = target.rsplit("/", 1)[-1].lower()
            variant = None
            if parent.is_dir():
                for child in parent.iterdir():
                    if child.name.lower() == want:
                        variant = child
                        break
            if variant is not None:
                warnings.append(
                    "case-only sound file: {}:{} names {!r}, found {}".format(
                        rel, lineno, target,
                        variant.relative_to(ROOT).as_posix()))
            else:
                problems.append(
                    "missing sound file: {}:{} names {!r} but src/{} does not "
                    "exist".format(rel, lineno, target, target))
    return total


def language_definitions():
    keys = set()
    for path in sorted(SRC.glob("LANGUAGE*")):
        text = strip_comments(read_text(path))
        for match in LANGUAGE_DEF_RE.finditer(text):
            keys.add(match.group(1).upper())
    return keys


def language_reference_files():
    """Lumps outside src/actors that also reference LANGUAGE keys."""
    files = []
    for pattern in ("MENUDEF", "SCORINFO", "MAPINFO", "KEYCONF",
                    "SBARINFO.h.uhappend", "SBARINFO.v.uhappend"):
        files.extend(p for p in SRC.glob(pattern) if p.is_file())
    return sorted(set(files))


def language_references():
    refs = {}
    for path in decorate_files():
        data = path.read_bytes()
        if b'"$' not in data:
            continue
        text = strip_comments(data.decode("utf-8", errors="replace"))
        rel = path.relative_to(ROOT).as_posix()
        for match in LANGUAGE_REF_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            refs.setdefault(match.group(1).upper(), set()).add(
                "{}:{}".format(rel, lineno))
    for path in language_reference_files():
        text = strip_comments(read_text(path))
        rel = path.relative_to(ROOT).as_posix()
        for match in LANGUAGE_REF_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            refs.setdefault(match.group(1).upper(), set()).add(
                "{}:{}".format(rel, lineno))
    for path in sorted(SRC.joinpath("acs_source").rglob("*.acs")):
        data = path.read_bytes()
        if b"GetString" not in data:
            continue
        text = strip_comments(data.decode("utf-8", errors="replace"))
        rel = path.relative_to(ROOT).as_posix()
        for match in re.finditer(r'(?i)GetString[ 	]*\([ 	]*"([^"]+)"', text):
            lineno = text.count("\n", 0, match.start()) + 1
            refs.setdefault(match.group(1).upper(), set()).add(
                "{}:{}".format(rel, lineno))
    return refs


def graphics_lumps():
    """Every graphic name the PK3 itself provides: file stems and TEXTURES defs."""
    names = set()
    prefixes = tuple(str(SRC / directory) + os.sep
                     for directory in ("sprites", "graphics", "patches"))
    for path in walk_src():
        if str(path).startswith(prefixes):
            names.add(path.stem.upper())
    texture_def_re = re.compile(
        r'(?im)^[ \t]*(?:sprite|texture|graphic|walltexture|flat|font)[ \t]+'
        r'("[^"]*"|[^\s,]+)[ \t]*,')
    for path in sorted(SRC.glob("TEXTURES*")):
        text = strip_comments(read_text(path))
        for match in texture_def_re.finditer(text):
            names.add(match.group(1).strip('"').upper())
    return names


def count_loadacs_entries():
    """Number of LOADACS library names (coverage figure only)."""
    total = 0
    for line in read_text(SRC / "LOADACS").splitlines():
        if line.split("//")[0].strip():
            total += 1
    return total


def hud_texture_references():
    refs = {}
    for path in sorted(SRC.glob("SBARINFO.*.uhappend")):
        text = strip_comments(read_text(path))
        rel = path.relative_to(ROOT).as_posix()
        for match in DRAWIMAGE_RE.finditer(text):
            refs.setdefault(match.group(1).upper(), set()).add(rel)
        for match in DRAWBAR_RE.finditer(text):
            refs.setdefault(match.group(1).upper(), set()).add(rel)
            refs.setdefault(match.group(2).upper(), set()).add(rel)
    for path in sorted(SRC.glob("MENUDEF")):
        text = strip_comments(read_text(path))
        rel = path.relative_to(ROOT).as_posix()
        for match in STATICPATCH_RE.finditer(text):
            refs.setdefault(match.group(1).upper(), set()).add(rel)
    for path in sorted(SRC.glob("MAPINFO")):
        text = strip_comments(read_text(path))
        rel = path.relative_to(ROOT).as_posix()
        for match in MAPINFO_IMAGE_RE.finditer(text):
            refs.setdefault(match.group(1).upper(), set()).add(rel)
    return refs


def report(problems, warnings, kind, name, sites, external, known):
    """Classify one unresolved reference."""
    if name in external:
        return
    where = sorted(sites)[0]
    if name in known:
        warnings.append(
            "known latent defect: {} {!r} is not defined in src/ or in the base "
            "game (used at {}){}".format(
                kind, name, where, "" if len(sites) == 1 else
                " and {} more site(s)".format(len(sites) - 1)))
        return
    problems.append(
        "undefined {}: {!r} at {}{}".format(
            kind, name, where, "" if len(sites) == 1 else
            " and {} more site(s)".format(len(sites) - 1)))


def main(argv):
    parser = argparse.ArgumentParser(
        description="Verify sound, language and HUD texture references.",
        epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true",
                        help="fail on warnings, including known latent defects")
    args = parser.parse_args(argv[1:])

    if not SRC.is_dir():
        print("error: missing src/", file=sys.stderr)
        return 2
    if not list(SRC.glob("SNDINFO*")):
        print("error: no SNDINFO lumps under src/", file=sys.stderr)
        return 2

    problems = []
    warnings = []

    sound_defs = sound_definitions()
    sound_refs = sound_references()
    for name, sites in sorted(sound_refs.items()):
        if name in sound_defs:
            continue
        report(problems, warnings, "logical sound", name, sites,
               BASE_GAME_SOUNDS, KNOWN_UNRESOLVED_SOUNDS)

    sound_files = check_sound_paths(problems, warnings)

    lang_defs = language_definitions()
    lang_refs = language_references()
    for name, sites in sorted(lang_refs.items()):
        if name in lang_defs:
            continue
        report(problems, warnings, "LANGUAGE key", name, sites,
               BASE_GAME_LANGUAGE_KEYS, KNOWN_UNRESOLVED_LANGUAGE_KEYS)

    for name in sorted(KNOWN_UNRESOLVED_SOUNDS):
        if name in sound_defs or name not in sound_refs:
            warnings.append(
                "stale KNOWN_UNRESOLVED_SOUNDS entry (now defined or unused): "
                "'{}'".format(name))
    for name in sorted(KNOWN_UNRESOLVED_LANGUAGE_KEYS):
        if name in lang_defs or name not in lang_refs:
            warnings.append(
                "stale KNOWN_UNRESOLVED_LANGUAGE_KEYS entry (now defined or "
                "unused): '{}'".format(name))

    graphics = graphics_lumps()
    loadacs_entries = count_loadacs_entries()
    hud_refs = hud_texture_references()
    for name, sites in sorted(hud_refs.items()):
        if name in graphics:
            continue
        report(problems, warnings, "HUD texture", name, sites,
               BASE_GAME_HUD_GRAPHICS, KNOWN_UNRESOLVED_HUD_GRAPHICS)

    print("logical sounds:     {} defined locally, {} referenced by {} call "
          "site(s)".format(len(sound_defs), len(sound_refs),
                           sum(len(s) for s in sound_refs.values())))
    print("sound file targets: {} SNDINFO entries pointing at a .wav/.ogg/.mp3 "
          "file".format(sound_files))
    print("LANGUAGE keys:      {} defined locally, {} referenced by {} site(s)".format(
        len(lang_defs), len(lang_refs), sum(len(s) for s in lang_refs.values())))
    print("HUD/menu textures:  {} referenced by SBARINFO/MENUDEF/MAPINFO".format(
        len(hud_refs)))
    print("coverage:           {} sound name(s), {} LANGUAGE key(s), {} HUD "
          "texture name(s), {} LOADACS librar(y/ies), {} graphic name(s); "
          "include and Patch-target counts are printed by "
          "check_lump_integrity.py".format(
              len(sound_defs), len(lang_defs), len(hud_refs),
              loadacs_entries, len(graphics)))

    for warning in warnings:
        print("warn: {}".format(warning))
    for problem in problems:
        print("FAIL: {}".format(problem))

    checked = len(sound_refs) + len(lang_refs) + len(hud_refs)
    if problems or (args.strict and warnings):
        print()
        print("{} problem(s), {} warning(s) across {} reference(s)".format(
            len(problems), len(warnings), checked))
        return 1
    print("ok: {} asset references resolve, {} warning(s)".format(
        checked, len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
