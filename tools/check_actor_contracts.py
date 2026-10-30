#!/usr/bin/env python3
"""Guard the DECORATE actor/weapon contracts that shipped bugs broke.

Every rule here exists because this mod shipped a fix for the failure it
describes.  DECORATE is not type-checked against the mod's own intent: an actor
name is a bare string, a state label is a bare string, and the engine happily
loads a mod whose weapon is unreachable or whose spawn action does nothing.
The four traps:

1. A spawn/inventory action names an actor that does not exist.
   A_SpawnItemEx("TidalTitoJetWave", ...) with the actor renamed or deleted
   spawns nothing at all: no error, no visual, no damage.  The same holds for
   A_GiveInventory("PowerX") / A_JumpIfInventory("Flag"): the check silently
   answers "no" forever.  The registered fix class is "actors spawned by name
   that no longer exist".  Actor names are case-insensitive in ZDoom, so a
   Cutterflag / CutterFlag pair is the same class and must resolve.

2. A weapon actor loses a state label its base dispatches to.
   BaseQwantWep ends Altfire with A_ReFire("ReadyX") and documents that every
   concrete Qwant weapon must define ReadyX; the UH weapon bases do the same
   with DeselectDeath / DeselectSwap / SelectSwap.  Delete or rename that label
   in a child weapon and the weapon locks up (or cannot be deselected) with no
   diagnostic.  The registered fix class is "weapons that lose a state label".

3. Two actors declare the same class name.  The engine keeps one definition and
   silently discards the other, so half of the intended properties never apply -
   and the duplicate usually appears after a rename or a merge.

4. An orphan _W weapon actor.  A weapon actor that nothing references is a
   weapon no class can ever be given; it is dead weight that still costs load
   time and, worse, it hides the fact that a class lost its weapon.

The allowlist BASE_GAME_ACTORS holds actor classes supplied by MM8BDM v6b or by
the engine itself (Zandronum/GZDoom built-ins such as TeleportFog).  It was
generated once by resolving every referenced name against src/actors plus the
read-only reference DECORATE trees (for_8bdm-v6b, for_8bdm-universal,
for_8bdm-v6a); every entry is a base-game or engine actor, none is a UH actor.
Do not add a name to it because a check failed: a name is missing from it only
when the actor it points at exists nowhere (the bug this file guards).
--list-unresolved prints every reference that resolves to neither src/actors nor
this allowlist, which is the list to audit before touching the constant.

Run:  python3 tools/check_actor_contracts.py [--list-unresolved] [--root PATH]
Exit: 0 clean, 1 findings, 2 usage/parse error.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUFFIXES = {".dec", ".txt"}
# Functions whose first string argument names another actor / inventory class.
CLASS_ARG_FUNCS = (
    "A_SpawnItemEx",
    "A_SpawnItem",
    "A_CustomMissile",
    "A_FireCustomMissile",
    "A_SpawnProjectile",
    "A_GiveInventory",
    "A_TakeInventory",
    "A_JumpIfInventory",
    "A_JumpIfInTargetInventory",
    "A_JumpIfTargetInventory",
    "A_GiveToTarget",
    "A_TakeFromTarget",
    "A_CheckInventory",
    "A_DropItem",
)
CLASS_ARG_RE = re.compile(
    r'\b(' + "|".join(CLASS_ARG_FUNCS) + r')\s*\(\s*"([^"]+)"', re.IGNORECASE
)
# Inventory-ish functions: their first quoted argument is an item, not a label.
ITEM_FIRST_RE = re.compile(
    r"A_JumpIf(InTarget)?Inventory|A_JumpIfTargetInventory|A_CheckInventory",
    re.IGNORECASE,
)
# Actions whose trailing string arguments are state labels.
LABEL_ARG_RE = re.compile(
    r"\b(A_Jump\w*|A_ReFire|A_GunFlash|A_WeaponReady)\s*\(([^()]*)\)", re.IGNORECASE
)
# goto Target / goto Target+N / goto Parent::Label (DECORATE ancestor label).
GOTO_RE = re.compile(
    r"\bgoto\s+([A-Za-z0-9_.]+)(?:\s*[+-]\s*\d+)?(?:\s*::\s*([A-Za-z0-9_.]+))?",
    re.IGNORECASE,
)
# DECORATE identifiers may start with a digit (4MICritPainFX, 4MIPharaoh).
ACTOR_RE = re.compile(
    r"(?im)^[ \t]*actor\s+([A-Za-z0-9_]+)"
    r"(?:\s*:\s*([A-Za-z0-9_]+))?"
)
STATES_RE = re.compile(r"(?im)^[ \t]*States\s*\{")
LABEL_RE = re.compile(r"(?m)^[ \t]*([A-Za-z0-9_.]+)\s*:")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# State labels supplied by the MM8BDM v6b weapon / ClassBase DECORATE (DeselectSwap,
# SelectSwap, NoFlash, Megaman* death and pain labels, ...).  These are the only
# labels a UH weapon may dispatch to without defining them in src/actors.
EXTERNAL_STATE_LABELS = {
    "deselectswap",
    "selectswap",
    "noflash",
    "noammo",
    "hold",
    "botammo",
    "botquakestart",
    "altfireh",
    "firehr",
    "megamandeath",
    "megamanpain",
    "megamanerase",
    "megamanfall",
    "megamangib",
    "megamanfade",
    "megamanfade3",
    "megamancorpseend",
    "megamanicegib",
    "sound.bustercharge",  # flash label defined by the MM8BDM weapon bases
    "spawn",
    "death",
    "end",
}

# Actor classes referenced by src/actors that live in MM8BDM v6b, the shared
# MM8BDM universal tree, or the engine.  Generated; see the module docstring.
BASE_GAME_ACTORS = frozenset(
    word.lower()
    for word in """
    AdapterWaitCount AirJumpLimit AirJumpsUsed AliveCheck AliveCheckFlag AtomicFireAmmo
    BallFlag BallKickCounter BaseFlagPack BasicArmor BassBusterRage BassExplode
    BeatBoosterHasLanded BeatBoostIsActive BeatCallCheck BeatCallProtection BigHealth BigWeaponEnergy
    BlackHoleAmmo BlackHoleBomb_Ready_P BlackHoleBombAmmo BlackHoleBombCooldown BlackHoleBombExists BlackHoleBombFXSpawner
    BlackHoleBombKill BlackHoleBombTrigger BlackHoleFlag BlackHoleShieldCheck BlackHoleSpawnerSync BlackHoleTrigger
    BlackHoleTrigger_W BlastRuneWave BlastRuneWaveL BlastRuneWaveR BlowDeathTimer BotFlashStopperCooldown
    BotTimeStopperCooldown BouncerReflectedCheck BreakDashAmmo BreakDashCharge BreakDashFX BreakDashHit
    BreakDashPuff BreakDashQuake BreakDashRecoil BreakDashSpark BreakDashSparkFX BreakDashSpeed
    BubbleBomb2 BubblePop BurnWaveSpawner CanBeGrabBustered CardSpawner CentaurFlashAlt
    CentaurFlashFX CentaurFlashHalfAlpha CentaurFlashHalfAlphaGiver CentaurFlashNoAlpha CentaurFlashNoAlphaGiver CentaurFlashQuarterAlpha
    CentaurFlashQuarterAlphaGiver CentaurFlashTime CentaurFlashTimeShort ChillDebris ChillFreeze ChillFreezeGravity
    ChillFreezeJump ChillFreezeTimer ChillSpikeCeilingFX1 ChillSpikeCeilingFX2 ChillSpikeFloorFX1 ChillSpikeFloorFX2
    ChillSpikeWallFX1 ChillSpikeWallFX2 Clip CommandoBombSecondary CommandoCooldown CommandoSwitch
    CommandoTrailFX
    ConcreteFX ConcreteTime ConcreteVision ConfettiSpawner CopyShot CopyVisionAmmo
    CopyVisionFlag CopyVisionRedirect CopyVisionSpawner CossackTeamFlag CountBomb CountbombExplodeFX
    CrashBombExplode CriticalDeath CriticalDeathGiver CriticalDeathSpawner CrystalEyeHit CutterFlag
    Cutterflag DawnBreakerAmmo DawnBreakerAmmoSyncer DawnBreakerDebris DawnBreakerDive DawnBreakerEmitter
    DawnBreakerFX1 DawnBreakerFX2 DawnBreakerFX3 DawnBreakerFX4 DawnBreakerFX5 DawnBreakerQuake
    DeathFX1 DeathFX2 DeepDiggerAltFrames DeepDiggerFlagL DeepDiggerFlagR DeepDiggerMainFrames
    DeepDiggerWarper_L DeepDiggerWarper_R DespawnOldCutter DiveCounter DoomSphere DoveSpawner
    DrillFlag DustBit1 DustBit1C DustBit2 DustBit2C DustBit3
    DustBit3C DustBit4 DustBit4C DynamicArmorDosage ElectricShockBurstStart ElectrifyEffect
    EndSpin ExplodeDeathFlag ExplosionEffect1 ExplosionEffect2 ExplosionEffect3 FakeDeathFX
    FallDeathExplodeFlag FallingDeathFlag FireIceWall FirePhotonMissileLauncher FireRainFlush FireShield1
    FireShield2 FireShield3 FireShieldDamage FireThunderClaw FireTornadoBlow1 FireTornadoBlow2
    FireTornadoBlow3 FireTornadoBlow4 FireVision FireWheelSaw FistFlag FlameSword
    FlameSword2 FlameSwordAmmo FlameSwordBit FlameSwordProtect FlashBombFX1 FlashBombFX2
    FlashBombTrail FlashStopper FlashStopperCooldowner FlashStopperFX FlashStopperHit FlashStopperStarter
    FlashStopperWait FreezeCrackerFX FrozenDeathFX GravityHoldPainPower Guardsphere GutrockFX
    GutRockMelee GyroAttack_Fire_P GyroAttack_Ready_P GyroAttackExists GyroAttackFunc GyroAttackPuff
    GyroAttackTrigger GyroFlag HardKnuckleFX HasFeetInWater HeadTowardsTarget_Arg0 HomingSniper
    HomingSniperAmmo HomingSniperCharge HornetChaserCooldowner HornetChaserCooldownFlag HyperStormDust IceDeathFlag
    IcePitFreeze IceVision IceWallAmmo IceWallCooldowner IceWallCooldownFlag IceWallFlag
    IceWaveDropper ImFrozen ImOnFire IsBot IsDead IsUnderWater
    Item2Flag JewelSatelliteAmmo JewelSatelliteDisable JewelSatelliteEnable JewelSatelliteWarper JewelSatelliteWarper2
    JewelSatelliteWarper3 JewelSatelliteWarper4 JewelShieldCheck JumpCancler JunkChargeWait JunkChargeWaitCooldowner
    JunkEndEffect2 JunkShieldAmmo JunkShieldCharge JunkSpawnFX KickedBall KilledMe
    KilledMeStock KingTeamFlag KnightDouble KnightFlag LargeDrillShell LeafShieldAmmo
    LeafShieldCharge LeafShieldCounter LeafShieldDisable LeafShieldGuard LeafShieldWarper LightningBoltCooldown
    LightningBoltEndpoint LightningBoltFX LightningBoltGuessShooter LightningBoltLength LightningBoltTracerShooter LightningExtend
    LightningStartFX1 LightningStartFX2 LightTeamFlag MagicCardWallDetector MagicCardWallDetectorReturn MagmaBazookaAmmo
    MediumDrillShell MegaBallAmmo MegaBallStart Metrenger MirrorBusterAmmo MirrorBusterFlag
    MirrorBusterReflectSound MirrorBusterSwitch MM8BDMPlayer MM8BDMProjSpawnFuncClient NoHookshot NoiseCrushAmmo
    NoiseCrushCaught NoiseCrushTrail2A NoiseCrushTrail2B NoiseCrushTrail2C NoiseCrushTrail2D NoiseCrushTrail2E
    NoiseCrushTrail2F NoJumpCancel NoProjectileTeamTranslation NoPushFlag NoRemoteMineLatch NoWeaponSwitchSound
    OilBoat OilCanisterExplodeFX OilPitIgnite OilShot OilSliderFlag OilSliderFlightFlag
    Once PainFX PartyBallRespawner PartyBallSpawnFunc PharaohCharge PharaohShotAmmo
    PhotonMissileAmmo PhotonMissileCharge PhotonMissileHold1 PhotonMissileHold2 PhotonMissileHold3 PhotonMissileHold4
    PhotonMissileHold5 PirateMineExplosionFX PlantBarrierHealer PlantBarrierWarper PlantWeakener PlayerPropertyBuddha
    PlayerPropertyBuddhaOn PlayerPropertyFlight PlayerPropertyGrounded PlayerPropertyInvulnerable PlayerPropertyNoGravity PlayerPropertyProsperity
    PlayerPropertyRage PlayerPropertySpread PowerBeatBoostSpeed PowerBeatBoostUpSpeed PowerDoubleFiringSpeed PowerDrainRune
    PowerHighJump PowerQuarterDamage PowerShock PowerSlowFade PowerSpreadRune PowerTime
    PropBlowerEffect ProtoShieldDeathFX ProtoShieldFX ProtoShieldHitbox1 ProtoShieldHitbox2 ProtoShieldHitbox3
    ProtoShieldHitbox4 ProtoShieldHitbox5 ProtoShot RainFlushAmmo RainFlushSoakify RainSprinkleSpawn
    RemoteMineFlag RemoteMineFlyFunc Repulsion RespawnProtectionAlpha ReturningCutterMasterFunc ReturningKnight
    ReturningKnightFunc ReturningKnightMasterFunc ReturningMagicCard ReturningRingFunc ReturningRingMasterFunc RisingDeathFlag
    RollingCutterFlag RotateFunc SakugarneActive SakugarneAmmo SakugarneCrush SakugarneDebris
    SakugarneDriller SakugarneWarper SakugarneWarperStart ScorchBit ScorchWheelPowerup ScorchWheelWarper
    ScrewCrusherSpawner SearchSnakeMasterFunc SetDynamicArmorDosage ShieldCheck ShieldHits Shocked
    ShockFX SkullBarrierAmmo SkullBarrierCooldown SkullBarrierProtection SkullBarrierWarper SkullBarrierWatcher
    SkullShieldCheck SmallHealth SniperJoeShieldX SnowFlake SoakifyEffect SolarBlazeCooldown
    SolarBlazeFlag SparkChaserTagged SparkShockCooldowner SparkShockCooldownFlag SparkShockFX SpawnMirrorBuster
    SpinTime SpreadDrill_Fire_P SpreadDrill_Ready_P SpreadDrillAltWait SpreadDrillAltWaitCooldowner SpreadDrillAmmo
    SpreadDrillFlag SpreadDrillProtect SpreadDrillTrigger SpreadDrillWait StarCrashAmmo StarCrashWarper
    StopShield StreetTree StrongSpring SunstarNovaBeamEndFX SuperArmTemp SuperArmTempTaker
    SuperArmWarper TakeTenguBladeAmmo TakeTopSpinAmmo TargetAimPointActive TargetMarker TeleportFog
    TeleportFogFancy TeleportFogNormal TenguDash ThunderBeamAmmo ThunderClawAmmo ThunderWoolArc
    ThunderWoolImpact ThunderWoolSparkFX TimeSlowAmmo TimeSlowCooldown TimeSlowCooldowner TimeSlowFX
    TimeStopActivator TimeStopGFX TimeStoppedCounter TimeStopperAmmo TimeUnstopped TopSpinAmmo
    TopSpinFlag TornadoBlowAmmo TornadoBlowThrust TornadoHoldCooldowner TornadoHoldCooldownFlag TornadoHoldEnd
    TornadoHoldProtect TornadoHoldRefresh WallJumpLimit WarpMasterHere WaterBalloon WaterShieldAmmo
    WaterShieldCheck WaterShieldExpand WaterShieldShoot WaterShieldSpawn WaterShieldSpawner WaterShieldSpread
    WaterShieldStop WaterWaveAmmo WaterWaveSpawner WaveBurnerBubbleFX WaveBurnUW WeaponCharge
    WeaponChargeLevel WeaponEnergy WheelCount WheelCutterAmmo WheelCutterCheck WheelCutterDestroy
    WheelCutterLaunchPlacer WheelCutterWallCheck WildCoilAmmo WildCoilFlag WilyIcePainPower WilyTeamFlag
    WireHookShotDelay
    // Added in MM8BDM v6c. Copy weapons and shared pain adapters reference
    // these base actors under actors/inventory and actors/boss.
    BreakDashAttack1_CI BreakDashAttack2_CI BreakDashAttack3_CI
    CentaurFlashCooldownFlag CentaurFlashCooldowner IceWallIcePitFreeze
    PharaohFX PhotonMissileCooldown_P PhotonMissileDelay_W
    SakugarneActivate_CI SakugarneDeactivate_CI CrashCooldownFlag CrashCooldowner ChargeKickThrust
    FlameSwordSlash_CI FlameSwordOilPitIgnite FlameSwordFlameFX4G FlameSwordFlameFX5 FlameSwordDunk_CI FlameSwordQuake_CI
    SearchSnakeSpawner SearchSnakeCrawler
    GravityHold_Fire_P GravityHoldCooldown GravityHoldCooldowner GravityHoldExplosionFX GravityHoldExplosionFXCeiling GravityHoldHit
    RockKickHit RollSwingHit RollSwingSweepHit SkullBarrierHit SkullBarrierHitBig
    FlameSwordHit_CI? FlameSwordStun_CI
""".split()
)


# A block comment that never closes (it happens: see TheDentistShiny_W.dec)
# must still be stripped, so the pattern accepts end-of-file as its terminator.
COMMENT_RE = re.compile(r'"(?:[^"\\]|\\.)*"|//[^\n]*|/\*.*?(?:\*/|\Z)', re.DOTALL)


def strip_comments(text: str) -> str:
    """Remove // and /* */ comments, keep line numbering, keep strings."""

    def replace(match):
        token = match.group(0)
        if token.startswith('"'):
            return token
        return "\n" * token.count("\n")

    return COMMENT_RE.sub(replace, text)


def iter_actor_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() in SUFFIXES:
            yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def split_states(text: str, start: int, end: int):
    """Return (has_states_block, block_text) for one actor body."""
    match = STATES_RE.search(text, start, end)
    if not match:
        return False, ""
    depth = 0
    index = match.end() - 1
    while index < end:
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return True, text[match.start() : index + 1]
        index += 1
    return True, text[match.start() : end]


def gather_actor_refs(text: str):
    """Every first-string-argument actor reference as (name, line, function)."""
    refs = []
    for match in CLASS_ARG_RE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        refs.append((match.group(2), line, match.group(1)))
    return refs


def label_refs(states: str) -> set:
    """State labels this state block dispatches to."""
    refs = set()
    for match in GOTO_RE.finditer(states):
        # "goto Parent::Label" dispatches to the named ancestor's label, so the
        # target is the label after "::"; plain "goto Label" is a local dispatch.
        refs.add((match.group(2) or match.group(1)).lower())
    for match in LABEL_ARG_RE.finditer(states):
        func = match.group(1)
        quoted = re.findall(r'"([A-Za-z_][A-Za-z0-9_.]*)"', match.group(2))
        if ITEM_FIRST_RE.search(func) and quoted:
            quoted = quoted[1:]
        refs.update(item.lower() for item in quoted)
    return refs


def own_labels(states: str) -> set:
    return {item.lower() for item in LABEL_RE.findall(states)}


class Decl:
    __slots__ = ("name", "parent", "path", "line", "states", "has_states", "keys", "body")

    def __init__(self, name, parent, path, line, has_states, states, body):
        self.name = name
        self.parent = parent
        self.path = path
        self.line = line
        self.has_states = has_states
        self.states = states
        self.body = body
        self.keys = own_labels(states) if has_states else set()


def parse_tree(actor_root: Path):
    """Return (decls_by_name, order, refs)."""
    decls = {}
    order = []
    refs = []
    for path in iter_actor_files(actor_root):
        text = strip_comments(read_text(path))
        matches = list(ACTOR_RE.finditer(text))
        for index, match in enumerate(matches):
            body_start = match.end()
            body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            has_states, states = split_states(text, body_start, body_end)
            decl = Decl(
                match.group(1),
                match.group(2),
                path,
                text.count("\n", 0, match.start()) + 1,
                has_states,
                states,
                text[body_start:body_end],
            )
            order.append(decl)
            decls.setdefault(decl.name.lower(), decl)
        refs.extend((path, name, line, func) for name, line, func in gather_actor_refs(text))
    return decls, order, refs


def chain(decls, name: str):
    """In-src inheritance chain, nearest first, ending with the external base."""
    out = []
    current = name.lower()
    guard = 0
    while current and current in decls and guard < 64:
        out.append(current)
        parent = decls[current].parent
        current = parent.lower() if parent else ""
        guard += 1
    if current:
        out.append(current)
    return out


def chain_labels(decls, name: str) -> set:
    labels = set()
    for ancestor in chain(decls, name):
        decl = decls.get(ancestor)
        if decl is not None:
            labels |= decl.keys
    return labels


def weapon_bases(baseweapon_path: Path) -> set:
    if not baseweapon_path.is_file():
        return set()
    text = strip_comments(read_text(baseweapon_path))
    return {match.group(1).lower() for match in ACTOR_RE.finditer(text)}


def main(argv) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument(
        "--list-unresolved",
        action="store_true",
        help="print every unresolved actor reference (allowlist audit)",
    )
    args = parser.parse_args(argv[1:])

    root = args.root.resolve()
    actor_root = root / "src" / "actors"
    baseweapon_path = actor_root / "inventory" / "baseweaponedit.txt"
    if not actor_root.is_dir():
        print(f"error: missing {actor_root}", file=sys.stderr)
        return 2
    if not baseweapon_path.is_file():
        print(f"error: missing {baseweapon_path}", file=sys.stderr)
        return 2

    decls, order, refs = parse_tree(actor_root)
    if not decls:
        print("error: no actor declarations parsed", file=sys.stderr)
        return 2

    findings = 0
    checks = {}

    # --- rule 1: referenced actor classes must exist ----------------------
    unresolved = Counter()
    unresolved_where = {}
    for path, name, line, func in refs:
        key = name.lower()
        if key in decls or key in BASE_GAME_ACTORS:
            continue
        unresolved[name] += 1
        unresolved_where.setdefault(name, (path, line, func))
    checks["refs"] = len(refs)
    if unresolved:
        findings += len(unresolved)
        print("missing actor classes referenced by spawn/inventory actions:")
        for name in sorted(unresolved):
            path, line, func = unresolved_where[name]
            print(
                f"  {name}  ({unresolved[name]}x) first at "
                f"{path.relative_to(root)}:{line} in {func}"
            )
    if args.list_unresolved:
        print("\nreferences resolving to neither src/actors nor BASE_GAME_ACTORS:")
        for name in sorted(unresolved):
            path, line, func = unresolved_where[name]
            print(f"  {name:38} {path.relative_to(root)}:{line} {func}")
        print(f"({len(unresolved)} distinct)")

    # --- rule 2: weapon state labels its base dispatches to ---------------
    bases = weapon_bases(baseweapon_path)
    if not bases:
        print(f"error: no weapon base actors in {baseweapon_path}", file=sys.stderr)
        return 2
    weapons = [
        decl for decl in order if any(base in chain(decls, decl.name) for base in bases)
    ]
    checks["weapons"] = len(weapons)
    label_findings = 0
    for decl in weapons:
        if decl.path == baseweapon_path:
            # The abstract bases in baseweaponedit.txt dispatch to labels that
            # each concrete weapon must define (ReadyX, DeselectSwap).  That is
            # the documented contract, not a defect in the base itself.
            continue
        resolved = chain_labels(decls, decl.name)
        if not resolved:
            findings += 1
            print(
                f"{decl.path.relative_to(root)}:{decl.line}: {decl.name}: "
                f"weapon has no state label in its declaration chain"
            )
            continue
        for label in sorted(label_refs(decl.states) if decl.has_states else ()):
            if label in EXTERNAL_STATE_LABELS or label in resolved:
                continue
            label_findings += 1
            findings += 1
            print(
                f"{decl.path.relative_to(root)}:{decl.line}: {decl.name}: "
                f"state label '{label}' is dispatched to but never defined"
            )
    checks["label-findings"] = label_findings

    # --- rule 3: duplicate class names ------------------------------------
    seen = {}
    for decl in order:
        seen.setdefault(decl.name.lower(), []).append(decl)
    duplicates = {key: group for key, group in seen.items() if len(group) > 1}
    checks["decls"] = len(order)
    for key in sorted(duplicates):
        group = duplicates[key]
        findings += len(group) - 1
        locations = ", ".join(
            f"{decl.path.relative_to(root)}:{decl.line}" for decl in group
        )
        print(f"duplicate actor class '{group[0].name}': {locations}")

    # --- rule 4: orphan _W weapon actors ----------------------------------
    corpus = Counter()
    for path in sorted((root / "src").rglob("*")):
        if path.is_file() and path.suffix.lower() in {".dec", ".txt", ".acs", ".md"}:
            corpus.update(IDENT_RE.findall(read_text(path).lower()))
    for name in ("KEYCONF", "LOADACS", "DECORATE", "TEAMINFO", "SNDINFO.players"):
        path = root / "src" / name
        if path.is_file():
            corpus.update(IDENT_RE.findall(read_text(path).lower()))
    w_actors = [decl for decl in order if decl.name.endswith("_W")]
    checks["_W"] = len(w_actors)
    orphans = [decl for decl in w_actors if corpus[decl.name.lower()] <= 1]
    for decl in orphans:
        findings += 1
        print(
            f"{decl.path.relative_to(root)}:{decl.line}: orphan weapon actor "
            f"'{decl.name}' is declared but never referenced"
        )
    checks["orphans"] = len(orphans)

    print(
        "actor contracts: "
        + ", ".join(f"{key} {value}" for key, value in checks.items())
    )
    if findings:
        print(f"\n{findings} actor/weapon contract finding(s)")
        return 1
    print("ok: actor and weapon contracts hold")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
