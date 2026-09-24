#!/usr/bin/env python3
"""
Migrate all boss weapon tags from legacy TAG_BossXXX_W to TAG_<ActorName>.
Updates:
1. src/LANGUAGE.enu.tag (replaces legacy Boss tag sections with clean TAG_<ActorName>)
2. src/acs_source/compat/mods/uix/uh_uixfw_boss_defs.acs (updates fixed weapon wheels)
3. src/actors/classes/bosses/*_W.dec (updates DECORATE Tag properties)
"""

import os
import re
import sys
import glob

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LANG_FILE = os.path.join(REPO_ROOT, "src", "LANGUAGE.enu.tag")
UIX_FILE = os.path.join(REPO_ROOT, "src", "acs_source", "compat", "mods", "uix", "uh_uixfw_boss_defs.acs")
BOSS_DIR = os.path.join(REPO_ROOT, "src", "actors", "classes", "bosses")

# Mapping of weapon actor name -> polished display name
BOSS_WEAPON_TAGS = {
    "AbePenny_W": "Flintlock Revolver",
    "ArchArcanist_W": "Shin Arcane Magicks",
    "ArchArcanist_W1": "Shin Arcane - Wind",
    "ArchArcanist_W2": "Shin Arcane - Fire",
    "ArchArcanist_W3": "Shin Arcane - Water",
    "ArenaDemoneye_W": "Arena Demoneye Hands",
    "AstromancerComplex_W": "Astro Crash",
    "AstromancerSimple_W": "Star Crush",
    "BalladeGB_W": "Sapion Cracker",
    "Balrog_W": "Balrog Buster",
    "Berserker_W": "Berserker Rage",
    "BlackDevilEye_W": "Duplicated Flare Hands",
    "BluTankBot_W": "Blue Machine Buster",
    "BlueDestron_W": "Sorry Nothing - Blue",
    "BlueElephant_W": "Elephant Trunk",
    "BlueHero_W": "Blue Hero Buster",
    "BlueJayDuo_W": "Blue Jay Safety Eye",
    "BlueSpeciman_W": "Assumption Freeze",
    "BlueThwomp_W": "Thwomp Drop",
    "CXAirman_W": "CX Airman Fans",
    "CaptainBlitzkrieg_W": "Blitzkrieg Sawblades",
    "CaptainDevilEye_W": "Pridegasm Flare Hands",
    "ChieftainTomahawk_W": "Chieftain Tomahawk",
    "Clownpiece_W": "Clownpiece Hell Wand",
    "Clownpiece_W1": "Clownpiece Hell Wand",
    "Clownpiece_W2": "Hell Sign: Eclipse",
    "Clownpiece_W3": "Hell Sign: Star & Stripe",
    "Clownpiece_W4": "Hell Sign: Graze Inferno",
    "Clownpiece_W5": "Hell Sign: Flash and Stripe",
    "Clownpiece_W6": "Hell Sign: Lunatic Torch",
    "Clownpiece_W7": "Hell Sign: Apollo Hoax",
    "Clownpiece_W8": "Hell Sign: Fake Asylum",
    "Cobe_W": "Cobe Mushroom Chomp",
    "ColonelKachidonga_W": "Kangogias Cannon",
    "CrazedGrenademan_W": "Cranked Flash Bomb",
    "CuttyCut_W": "Minor Circuit Powers",
    "DLCCentaurman_W": "DLC Centaur Buster",
    "DicksterDick_W": "Surprise Weapon of No Regrets",
    "Dixieandoff_W": "Dixie Kung Fu Hands",
    "DonJavier_W": "Garras de Zen",
    "ElitistSue_W": "Frozen Arts of Hell",
    "ElitistWaylon_W": "Deity Dire Spear of Wind",
    "EyelentoMajor_W": "Leading Baton",
    "FBeast_W1": "F-Beast Claws",
    "FBeast_W2": "Aqua Cross",
    "FBeast_W3": "Tengu Cross",
    "FBeast_W4": "Ground Cross",
    "FBeast_W5": "Dust Cross",
    "FBeast_W6": "Beast Charge Attack",
    "FinalSampi_W": "Tools of Sampi",
    "FinalSampi_W1": "Blade of Sampi",
    "FinalSampi_W2": "Pinpoint Target",
    "FinalSampi_W3": "Power Stone",
    "FinalSampi_W4": "Rapid Stab",
    "FinalSampi_W5": "Spray and Pray",
    "FinalSampi_W6": "Fling Shot",
    "FinalSampi_W7": "Aerial Reppuken",
    "FinalSpeciman_W": "Final Assumption",
    "Floovy_W": "Golden Experience",
    "GBeast_W1": "G-Beast Claws",
    "GBeast_W2": "Heat Cross",
    "GBeast_W3": "Elec Cross",
    "GBeast_W4": "Slash Cross",
    "GBeast_W5": "Erase Cross",
    "GBeast_W6": "Beast Charge Attack",
    "GENERICBOSS_W": "Generic Boss Weapon",
    "GemBanker_W": "Fake Gem Weapon",
    "GhostSpeciman_W": "Assumption Ghost",
    "GraniteMauler_W": "Granite Maul",
    "GravitymanKamilia_W": "Gravity Reverse",
    "GutsBuddy_W": "Guts Buddy Arm",
    "HalfPressHardman_W": "TASBot Evolved Buster",
    "HarpStrumm_W": "Magical Girl Guitar",
    "HellBot_W": "Hands of Tragic Past Accidents",
    "HunterHawkeye_W": "Hellshot Railgun",
    "IronCurtain_W": "Green Tank of Greed",
    "JesterGelato_W": "Italian Revolutionary Weaponry",
    "JoeOfDuty_W": "Sniper Joe Assault",
    "Joterra_W": "Yare Yare Daze",
    "JuggerbroGold_W": "Golden Juggernaut",
    "JuggerbroSilver_W": "Silver Juggernaut",
    "KFCDragon756_W": "CFaKe Revolver",
    "KakusaretaSutoka_W": "Daku Sutaburedo",
    "KakusaretaSutoka_W2": "Daku Sutaburedo - Kunai",
    "KakusaretaSutoka_W3": "Daku Sutaburedo - Shuriken",
    "Lin_W1": "Lin Crossing",
    "Lin_W2": "Illusion Sword Dance",
    "MagicDevilEye_W": "Pressure Pulse Wand",
    "Magnetismo_W": "One Magnet Man Army",
    "MakeAGoodZero_W": "0-Saber",
    "MakeAGoodZero_W2": "Zero Default",
    "MakeAGoodZero_W3": "Zero Cutter Chip",
    "MakeAGoodZero_W4": "Zero Flame Chip",
    "MakeAGoodZero_W5": "Zero Icicle Chip",
    "MakeAGoodZero_W6": "Zero Zap Chip",
    "MakeAGoodZero_W7": "Zero Psycho Chip",
    "MakeAGoodZero_W8": "Zero Cheat Weapon",
    "MeguhMang_W": "Meguh Buster",
    "MeisterWahwee_W": "Double Gear Buster",
    "Wahwee_W1": "Wahwee Gear System",
    "Wahwee_W2": "Wahwee Speed Gear",
    "Misery_W": "Misery Bubble",
    "Morshu_W": "Lamp Oil, Rope, Bombs",
    "Neru_W": "Twin Dragon",
    "OfficerJohnson_W": "Hell-Made Modified SSG",
    "Pharaohman4MI_W": "Pharaoh Shotgun",
    "PlasmaSpark_W": "Plasma Spark",
    "PricksterPrick_W": "Spicy Sausage Feeder",
    "ProtoManBadGuy_W": "Proto Bad Guy",
    "PurpleDestron_W": "Sorry Nothing - Purple",
    "PurpleHero_W": "Purple Hero Buster",
    "RNCClashman_W": "Rumbling Bang",
    "RedBaronDuo_W": "Red Baron Danger Eye",
    "RedDestron_W": "Sorry Nothing - Red",
    "RedHero_W": "Red Hero Buster",
    "RedSpeciman_W": "Assumption Fire",
    "RedTankBot_W": "Red Machine Buster",
    "RedeadGuts_W": "Decaying Arm",
    "RepairManEdward_W": "Wrench and Toolbox",
    "RichDevilEye_W": "Total Pridegasm Money Wave",
    "Rogue_W": "Power of One-Man Army",
    "RussianGuts_W": "Soviet Bare Hands",
    "SPOOKYGHOSTHITLER_W": "Fait Negguh Ovas Mech",
    "SadFaceToadMan_W": "Toad Tears",
    "SakikoTogawa_W": "Oblivionis Chord",
    "ScrotoStuntDouble_W": "Low Payment Action Weapon",
    "Scrotoman_W": "Scroto Buster",
    "ShinHellbot_W": "Helltatoru Decoy Buster",
    "ShinNegaman_W": "Shin Nega Buster",
    "SinfulBusterExpert_W": "Sinful Great Buster",
    "SinfulBusterExpert_W1": "Sin of Lust",
    "SinfulBusterExpert_W2": "Sin of Gluttony",
    "SinfulBusterExpert_W3": "Sin of Sloth",
    "SinfulBusterExpert_W4": "Sin of Pride",
    "SinfulBusterExpert_W5": "Sin of Greed",
    "SinfulBusterExpert_W6": "Sin of Envy",
    "SinfulBusterExpert_W7": "Sin of Wrath",
    "SinfulBusterExpert_W8": "Sin of Buster",
    "SirAlphaEX_W": "Sword of Alpha EX",
    "SirAlpha_W": "Sword of Alpha",
    "Skullman4MI_W": "Hell Wheel",
    "SoccerRock_W": "Soccer Rock Buster",
    "SovietFrostBite_W": "Soviet Cold Buster",
    "SovietIgniter_W": "Soviet Ignite Buster",
    "SpecimanDX_W": "Assumption Deluxe",
    "Speciman_W": "Assumption Power",
    "SuperMegaman_W": "Super Magma Bazooka",
    "WeakHorse_W": "Horse Gun",
    "SuperSpeciman_W": "Assumption Support",
    "TheCommandoChamp_W": "Commando Landmine",
    "TheShadowManMythBoss_W": "Shadow Blade Master",
    "ThomasTheTrain_W": "Very Useful Steam Engine",
    "TidalTito_W": "Wicked Surfboard",
    "TimemanC_W": "Hands of Time",
    "TorontoCalifornia_W": "California Buster",
    "TricksterGiovanni_W": "Sinister Bombing Tech",
    "TropicalMWS_W": "Tropical Water Spout",
    "Troutius_W": "Troutius Buster",
    "TrueBusterExpert_W": "True Great Buster",
    "TrueBusterMistress_W": "True Mistress Buster",
    "VoidWalker_W": "Catalytic Rune - Wind",
    "VoidWalker_W2": "Catalytic Rune - Earth",
    "VoidWalker_W3": "Catalytic Rune - Water",
    "VoidWalker_W4": "Catalytic Rune - Fire",
    "WarRockStelar_W": "Star Force Mega Buster",
    "WarRockStelar_W2": "Star Force Tribe On",
    "YelTankBot_W": "Yellow Machine Buster",
    "YellowHero_W": "Yellow Hero Buster",
    "YellowSpeciman_W": "Assumption Thunder",
    "ZankokunaHellbot_W": "Ultimate Helltatoru Disaster",
}


def update_language_file():
    print(f"Updating {LANG_FILE}...")
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find where Boss Multi-Weapon Wheels and Boss Weapons sections are
    start_match = re.search(r"// =+\s*\n// Boss Multi-Weapon Wheels", content)
    end_match = re.search(r"// =+\s*\n// Demoneye & Lackey Weapons", content)

    if not start_match or not end_match:
        print("ERROR: Could not locate Boss sections in LANGUAGE.enu.tag!")
        sys.exit(1)

    start_idx = start_match.start()
    end_idx = end_match.start()

    # Generate new clean Boss sections
    # Separate multi-weapon wheels vs main weapons for clean organization
    multi_wep_bosses = [
        "ArchArcanist", "Clownpiece", "FBeast", "FinalSampi", "GBeast",
        "KakusaretaSutoka", "Lin", "MakeAGoodZero", "SinfulBusterExpert",
        "VoidWalker", "Wahwee", "WarRockStelar"
    ]

    wheel_entries = []
    main_entries = []

    for wep, name in sorted(BOSS_WEAPON_TAGS.items()):
        line = f"TAG_{wep} = \"{name}\";"
        is_wheel = any(wep.startswith(m) for m in multi_wep_bosses) and ("_W" in wep and any(wep.endswith(str(i)) for i in range(1, 10)))
        if is_wheel:
            wheel_entries.append(line)
        else:
            main_entries.append(line)

    new_section = (
        "// ===========================================================================\n"
        "// Boss Multi-Weapon Wheels\n"
        "// ===========================================================================\n\n"
        + "\n".join(wheel_entries)
        + "\n\n"
        "// ===========================================================================\n"
        "// Boss Weapons\n"
        "// ===========================================================================\n\n"
        + "\n".join(main_entries)
        + "\n\n"
    )

    new_content = content[:start_idx] + new_section + content[end_idx:]
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("LANGUAGE.enu.tag updated successfully.")


def update_uix_file():
    print(f"Updating {UIX_FILE}...")
    with open(UIX_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    replacements = {
        "TAG_Boss005_W": "TAG_KakusaretaSutoka_W",
        "TAG_Boss005_W2": "TAG_KakusaretaSutoka_W2",
        "TAG_Boss005_W3": "TAG_KakusaretaSutoka_W3",
        "TAG_Boss018_W": "TAG_ArchArcanist_W1",
        "TAG_Boss018_W2": "TAG_ArchArcanist_W2",
        "TAG_Boss018_W3": "TAG_ArchArcanist_W3",
        "TAG_Boss108_W": "TAG_GBeast_W1",
        "TAG_Boss108_W2": "TAG_GBeast_W2",
        "TAG_Boss108_W3": "TAG_GBeast_W3",
        "TAG_Boss108_W4": "TAG_GBeast_W4",
        "TAG_Boss108_W5": "TAG_GBeast_W5",
        "TAG_Boss108_W6": "TAG_GBeast_W6",
        "TAG_Boss109_W": "TAG_FBeast_W1",
        "TAG_Boss109_W2": "TAG_FBeast_W2",
        "TAG_Boss109_W3": "TAG_FBeast_W3",
        "TAG_Boss109_W4": "TAG_FBeast_W4",
        "TAG_Boss109_W5": "TAG_FBeast_W5",
        "TAG_Boss109_W6": "TAG_FBeast_W6",
        "TAG_Boss402_W1": "TAG_FinalSampi_W1",
        "TAG_Boss402_W2": "TAG_FinalSampi_W2",
        "TAG_Boss402_W3": "TAG_FinalSampi_W3",
        "TAG_Boss402_W4": "TAG_FinalSampi_W4",
        "TAG_Boss402_W5": "TAG_FinalSampi_W5",
        "TAG_Boss402_W6": "TAG_FinalSampi_W6",
        "TAG_Boss402_W7": "TAG_FinalSampi_W7",
        "TAG_Boss102_W1": "TAG_SinfulBusterExpert_W1",
        "TAG_Boss102_W2": "TAG_SinfulBusterExpert_W2",
        "TAG_Boss102_W3": "TAG_SinfulBusterExpert_W3",
        "TAG_Boss102_W4": "TAG_SinfulBusterExpert_W4",
        "TAG_Boss102_W5": "TAG_SinfulBusterExpert_W5",
        "TAG_Boss102_W6": "TAG_SinfulBusterExpert_W6",
        "TAG_Boss102_W7": "TAG_SinfulBusterExpert_W7",
        "TAG_Boss102_W8": "TAG_SinfulBusterExpert_W8",
        "TAG_MGZero_W2": "TAG_MakeAGoodZero_W2",
        "TAG_MGZero_W3": "TAG_MakeAGoodZero_W3",
        "TAG_MGZero_W4": "TAG_MakeAGoodZero_W4",
        "TAG_MGZero_W5": "TAG_MakeAGoodZero_W5",
        "TAG_MGZero_W6": "TAG_MakeAGoodZero_W6",
        "TAG_MGZero_W7": "TAG_MakeAGoodZero_W7",
    }

    count = 0
    for old_k, new_k in replacements.items():
        if old_k in text:
            text = text.replace(f'"{old_k}"', f'"{new_k}"')
            count += 1

    with open(UIX_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"uh_uixfw_boss_defs.acs updated ({count} replacements).")


def update_decorate_files():
    print(f"Updating DECORATE files in {BOSS_DIR}...")
    files = sorted(glob.glob(os.path.join(BOSS_DIR, "*_W.dec")))
    updated_files_count = 0

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        orig_content = content

        # Process actor by actor
        # Split while preserving delimiters
        # Find all actor blocks
        def update_actor_block(match):
            block = match.group(0)
            act_name = match.group(1)
            
            # Check if this actor is a known boss weapon
            # Case-insensitive lookup in BOSS_WEAPON_TAGS
            tag_key = None
            for w in BOSS_WEAPON_TAGS:
                if w.lower() == act_name.lower():
                    tag_key = f"TAG_{w}"
                    break

            if not tag_key:
                # If not a weapon in BOSS_WEAPON_TAGS, don't modify
                return block

            # Has Tag property?
            # Patterns:
            # Tag "$TAG_..."
            # Tag "literal..."
            # // Tag "..."
            tag_regex = re.compile(r"^\s*(?://\s*)?Tag\s+\"[^\"]*\"", re.I | re.M)
            new_tag_line = f'  Tag "${tag_key}"'

            if tag_regex.search(block):
                # Replace existing or commented Tag
                block = tag_regex.sub(new_tag_line, block, count=1)
            else:
                # Insert Tag right after opening brace or after the actor header
                # Find '{'
                brace_pos = block.find('{')
                if brace_pos != -1:
                    # insert on newline after '{'
                    block = block[:brace_pos + 1] + "\n" + new_tag_line + block[brace_pos + 1:]

            return block

        # Match actor Name [/*...*/] [: Parent] { ... }
        # Pattern captures actor header up to opening brace
        # We replace inside each actor chunk
        chunks = re.split(r"(?im)^(?=actor\s+)", content)
        new_chunks = []
        for c in chunks:
            m = re.match(r"actor\s+([A-Za-z0-9_]+)", c, re.I)
            if not m:
                new_chunks.append(c)
                continue
            act_name = m.group(1)
            
            tag_key = None
            for w in BOSS_WEAPON_TAGS:
                if w.lower() == act_name.lower():
                    tag_key = f"TAG_{w}"
                    break
            
            if not tag_key:
                new_chunks.append(c)
                continue

            # Need to update or add Tag
            tag_pattern = re.compile(r"^\s*(?://\s*)?Tag\s+\"[^\"]*\"", re.I | re.M)
            new_tag_line = f'  Tag "${tag_key}"'

            if tag_pattern.search(c):
                c = tag_pattern.sub(new_tag_line, c, count=1)
            else:
                # insert after opening {
                brace_pos = c.find('{')
                if brace_pos != -1:
                    c = c[:brace_pos + 1] + "\n" + new_tag_line + c[brace_pos + 1:]
            
            new_chunks.append(c)

        new_content = "".join(new_chunks)
        if new_content != orig_content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated_files_count += 1

    print(f"Updated {updated_files_count} DECORATE files.")


def main():
    update_language_file()
    update_uix_file()
    update_decorate_files()
    print("All migrations completed!")


if __name__ == "__main__":
    main()
