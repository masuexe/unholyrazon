#!/usr/bin/env python3
"""Deterministic validation fixtures for _gen_barpos.py."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile


TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import _gen_barpos as generator


def bar(bar_id, constant_name, **overrides):
    values = {
        "id": bar_id,
        "constant_name": constant_name,
        "position": "1",
        "priority": 0,
        "vertical_full": "002B_BAR",
        "vertical_empty": "NOBAR",
        "horizontal_full": "002B_VAR",
        "horizontal_empty": "VNOBAR",
        "capacity": 100,
    }
    values.update(overrides)
    return values


def toml_config(groups):
    lines = ["schema_version = 1", ""]
    for namespace, bars in groups:
        lines += ["[[groups]]", f'namespace = "{namespace}"', ""]
        for item in bars:
            lines += ["[[groups.bars]]"]
            for key, value in item.items():
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                else:
                    rendered = str(value).lower() if isinstance(value, bool) else value
                    lines.append(f"{key} = {rendered}")
            lines.append("")
    return "\n".join(lines)


def load_fixture(groups):
    with tempfile.TemporaryDirectory(prefix="uh-bar-fixture-") as temp_dir:
        path = Path(temp_dir) / "bars.toml"
        path.write_text(toml_config(groups), encoding="utf-8")
        old_config = generator.CONFIG
        generator.CONFIG = path
        try:
            return generator.load_bar_config()
        finally:
            generator.CONFIG = old_config


def expect_failure(groups, label):
    try:
        load_fixture(groups)
    except SystemExit:
        return
    raise AssertionError(f"fixture unexpectedly passed: {label}")


def check_cli_outputs():
    """Exercise the actual CLI, destination routing, and input isolation."""
    def run(*args, cwd=None, code=0):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "_gen_barpos.py"), *map(str, args)],
            cwd=cwd, capture_output=True, text=True,
        )
        assert result.returncode == code, (args, result.stdout, result.stderr)
        return result

    expected = generator.get_target_outputs(generator.load_bar_config())
    with tempfile.TemporaryDirectory(prefix="uh-emit-test-") as temporary:
        scratch = Path(temporary)
        output = scratch / "empty-output"
        run("-o", output, "-q")
        for original, content in expected.items():
            assert (output / original.relative_to(generator.ROOT)).read_text() == content
        run("-o", output, "--check", "-q")

        # Explicit paths are cwd-relative, not relative to --output-dir.
        selected = scratch / "selected"
        run("--emit", "sbar-h=custom/hud.txt", "--emit", "acs", "-o", selected, cwd=scratch)
        horizontal = scratch / "custom/hud.txt"
        assert horizontal.read_text() == expected[generator.SBAR_HZ]
        assert (selected / generator.OUTPUT_PATHS["acs"]).read_text() == expected[generator.GENERATED_ACS]
        assert not (selected / generator.OUTPUT_PATHS["sbar-h"]).exists()
        assert not (selected / generator.OUTPUT_PATHS["decorate"]).exists()
        run("--emit", "sbar-h=custom/hud.txt", "--check", cwd=scratch)
        horizontal.write_text("drift\n")
        drift = run("--emit", "sbar-h=custom/hud.txt", "--check", cwd=scratch, code=1)
        assert "DRIFT" in drift.stderr and horizontal.read_text() == "drift\n"
        horizontal.unlink()
        run("--emit", "sbar-h=custom/hud.txt", "--check", cwd=scratch, code=1)
        assert not horizontal.exists()

        # A non-DECORATE emission never opens the template; stdout stays clean.
        streamed = run("--emit", "sbar-v=-", "--barfx-template", scratch / "missing.dec", "-v")
        assert streamed.stdout == expected[generator.SBAR_VZ]
        assert "Loaded" in streamed.stderr
        streamed = run("--emit", "acs=-,sbar-h=combined.txt", "-q", cwd=scratch)
        assert streamed.stdout == expected[generator.GENERATED_ACS]
        assert (scratch / "combined.txt").read_text() == expected[generator.SBAR_HZ]

        # Independent graphics input and DECORATE template, with custom config.
        resources = scratch / "resources"
        resources.mkdir()
        (resources / "TEXTURES.fixture").write_text(
            "graphic FIXTURE_FILL, 1, 1 { patch FIXTURE_PATCH, 0, 0 }\n"
        )
        config = scratch / "bars.toml"
        config.write_text(toml_config([("UHBar_Fixture", [bar(
            "body", "UHBAR_FIXTURE",
            vertical_full="FIXTURE_FILL", horizontal_full="FIXTURE_FILL",
        )])]))
        template = scratch / "template.dec"
        prefix = "// preserved template preamble\n"
        template.write_text(prefix + "// $UH — TOML namespaced bar selectors / ammo\nold generated text\n")
        arguments = ["-c", config, "--source-dir", resources, "--barfx-template", template]
        custom_output = scratch / "custom-output"
        run(*arguments, "-o", custom_output)
        decorate = custom_output / generator.OUTPUT_PATHS["decorate"]
        assert decorate.read_text().startswith(prefix)
        assert "old generated text" not in decorate.read_text()
        assert "actor UHBar_Fixture_P1L0Selector" in decorate.read_text()
        run(*arguments, "-o", custom_output, "--check")
        # Omitting the resource input must fail, even if output contains graphics.
        failed = run("-c", config, "-o", resources, "--emit", "acs", code=1)
        assert "FIXTURE_FILL" in failed.stderr
        default_template = resources / generator.OUTPUT_PATHS["decorate"]
        default_template.parent.mkdir(parents=True)
        default_template.write_text(template.read_text())
        run("-c", config, "--source-dir", resources, "--emit", "decorate=-")

        # Export/partial generation must not remove historical files.
        stale = output / "actors/inventory/sbar/BarFX.txt"
        stale.write_text("keep this file\n")
        run("-o", output)
        run("-o", output, "--emit", "sbar-h", "--check")
        assert stale.read_text() == "keep this file\n"

        for invalid in (
            ["--emit", "unknown"], ["--emit", ""],
            ["--emit", "sbar-h="], ["--emit", "sbar-h,"],
            ["--emit", "sbar-h", "--emit", "sbar-h=other.txt"],
            ["--emit", "sbar-h=same.txt,sbar-v=./same.txt"],
            ["--emit", "sbar-h=-,sbar-v=-"],
            ["--emit", "sbar-h=-", "--check"],
        ):
            rejected = run(*invalid, cwd=scratch, code=2)
            assert not rejected.stdout and "error:" in rejected.stderr
        assert not (scratch / "same.txt").exists()


def main():
    shared_bank = load_fixture([
        ("UHBar_FixtureOne", [
            bar("body", "UHBAR_FIXTUREONE"),
            bar("extra", "UHBAR_FIXTUREONE_EXTRA"),
        ]),
        ("UHBar_FixtureTwo", [
            bar("body", "UHBAR_FIXTURETWO"),
        ]),
    ])
    first, second = shared_bank["bars"][:2]
    assert generator.layer_selector_id(shared_bank, first) == 1
    assert generator.layer_selector_id(shared_bank, second) == 2
    assert generator.layer_selector_capacity(shared_bank, first) == 2
    generator.validate_generated_actor_names(shared_bank)
    generated = generator.gen_namespaced_barfx_actors(shared_bank)
    assert "actor UHBar_FixtureOne_P1L0Selector" in generated
    assert "actor UHBar_FixtureTwo_P1L0Selector" in generated

    source_bar = bar("body", "UHBAR_SOURCE", source="Ammo1")
    del source_bar["capacity"]
    source_config = load_fixture([("UHBar_Source", [source_bar])])
    append_lines = generator.gen_namespaced_append_lines(source_config, True)
    assert any('DrawBar "002B_VAR", "VNOBAR", Ammo1,' in line
               for line in append_lines)
    formatted_h, formatted_v = generator.gen_append_files(source_config)
    assert formatted_h.startswith("AppendStatusBar normal, forcescaled {\n")
    assert formatted_v.startswith("AppendStatusBar fullscreen, forcescaled {\n")
    assert '\n  InInventory "DrawStatusBarFlag", 1 {\n' in formatted_h
    assert '\n  InInventory "DrawStatusBarFlag", 1 {\n' in formatted_v
    assert '\n        InInventory "UHBar_Source_P1L0Selector", 1 ' in formatted_h
    assert '\n        InInventory "UHBar_Source_P1L0Selector", 1 ' in formatted_v
    assert 'DrawBar "002B_VAR", "VNOBAR", Ammo1, horizontal, 58, 184;' in formatted_h
    assert formatted_h.endswith("}\n") and formatted_v.endswith("}\n")
    source_actors = generator.gen_namespaced_barfx_actors(source_config)
    assert "actor UHBar_Source_P1L0Selector" in source_actors
    assert "UHBar_Source_P1L0_BodyAmmo" not in source_actors
    source_acs = generator.gen_generated_acs(source_config)
    assert "function void Source_DrawBar(int id)" in source_acs
    assert "SetAmmoAmountAndCapacity" not in source_acs
    assert 'SetActorInventory(cam, "UHBar_Source_P1L0Selector", 0);' in source_acs
    assert "UHBar_Source_P1L0_BodyAmmo" not in source_acs

    # NegaMan's move bar is a direct real-ammo source inside a mixed namespace.
    # Its caller must not feed the dynamic copied-weapon ammo into this bar.
    real_config = generator.load_bar_config()
    nega_move = next(
        item for item in real_config["bars"]
        if item["_namespace"] == "UHBar_NegaMan" and item["id"] == "move"
    )
    assert nega_move["source"] == "NegaDuckAmmo"
    assert "capacity" not in nega_move
    real_acs = generator.gen_generated_acs(real_config)
    move_case = real_acs.split("case UHBAR_NEGAMAN_MOVE:", 1)[1].split(
        "case UHBAR_NEGAMAN_BODY:", 1
    )[0]
    assert 'SetInventory("UHBar_NegaMan_P2L0Selector", 2);' in move_case
    assert "SetAmmoAmountAndCapacity" not in move_case
    hud_source = (generator.ROOT / "acs_source" / "hud" / "copy_weapon_bars.acs").read_text(
        encoding="utf-8"
    )
    assert (
        'NegaMan_DrawBar(UHBAR_NEGAMAN_MOVE,\n'
        '                  CheckInventory("NegaDuckAmmo"), 400);'
    ) in hud_source
    assert "NegaMan_DrawBar(UHBAR_NEGAMAN_MOVE,\n                  CheckInventory(uh_nega_fill_ammo)" not in hud_source
    timestopper = hud_source.split('script "DrawBar_NegaTimeStopperWep"', 1)[1]
    assert 'NegaMan_DrawBar(UHBAR_NEGAMAN_MOVE, CheckInventory("NegaDuckAmmo"), 400);' in timestopper

    # Qwant's type enum, TOML visual definitions, and ACS switch must stay in
    # lockstep. The move's real fill ammo/capacity are runtime-resolved, so
    # every type is a proxy row rather than a direct source row.
    type_source = (generator.ROOT / "acs_source" / "hud" / "bar_types.acs").read_text(
        encoding="utf-8"
    )
    qwant_type_count = int(re.search(
        r"#define\s+QWANT_TYPE_COUNT\s+(\d+)", type_source
    ).group(1))
    qwant_types = [
        (name.lower(), int(value))
        for name, value in re.findall(
            r"#define\s+QWANT_TYPE_(?!COUNT\b)([A-Z]+)\s+(\d+)", type_source
        )
    ]
    assert [value for _name, value in qwant_types] == list(range(qwant_type_count))
    qwant_bars = [
        item for item in real_config["bars"] if item["_namespace"] == "UHBar_Qwant"
    ]
    qwant_moves = [item for item in qwant_bars if item["id"].startswith("move_")]
    assert len(qwant_moves) == qwant_type_count
    assert {item["id"] for item in qwant_moves} == {
        f"move_{name}" for name, _value in qwant_types
    }
    for name, value in qwant_types:
        item = next(bar for bar in qwant_moves if bar["id"] == f"move_{name}")
        letter = chr(ord("A") + value)
        assert item["vertical_full"] == f"02__{letter}_00"
        assert item["horizontal_full"] == f"02__{letter}_50"
        assert "source" not in item and item["capacity"] == 56
        assert (
            f"case QWANT_TYPE_{name.upper()}:\n"
            f"      Qwant_DrawBar(UHBAR_QWANT_MOVE_{name.upper()}, "
            "CheckInventory(ammo), max_var);"
        ) in hud_source
    assert "qwanttypebar[type]" not in hud_source
    assert "qwanttypevar[type]" not in hud_source

    # Player-health visuals intentionally use runtime proxy capacities. Do not
    # replace these with SBARINFO Health: BARLIB reads APROP_SpawnHealth while
    # the engine's Health bar includes stamina in its maximum.
    health_bars = [
        item for item in real_config["bars"]
        if item["_namespace"] == "UHBar_PlayerHealthState"
    ]
    assert {
        item["id"] for item in health_bars
    } == {"invulnerable", "guard_strengthened", "guard_weakened", "burning"}
    assert all("source" not in item and item["capacity"] == 100 for item in health_bars)
    health_source = (generator.ROOT / "acs_source" / "hud" / "common_bars.acs").read_text(
        encoding="utf-8"
    )
    assert re.findall(
        r"PlayerHealthState_DrawBar\((UHBAR_PLAYERHEALTH_[A-Z]+), hp, maxhp\)",
        health_source,
    ) == [
        "UHBAR_PLAYERHEALTH_INVULNERABLE",
        "UHBAR_PLAYERHEALTH_STRENGTHENED",
        "UHBAR_PLAYERHEALTH_WEAKENED",
        "UHBAR_PLAYERHEALTH_WEAKENED",
        "UHBAR_PLAYERHEALTH_STRENGTHENED",
        "UHBAR_PLAYERHEALTH_BURNING",
    ]

    # Atomic Fire retains its cvar/threshold/timer control flow. Ammo variants
    # use position-1/layer-0, and charge_meter uses position-1/layer-1 overlay.
    atomic_bars = [
        item for item in real_config["bars"]
        if item["_namespace"] == "UHBar_AtomicFireWepU"
    ]
    assert {
        (item["id"], item["source"], item["position"], item["priority"])
        for item in atomic_bars
    } == {
        ("charge_meter", "AtomicFireCharge_F", "1", 1),
        ("ammo_maximum", "AtomicFireAmmo", "1", 0),
        ("ammo_high", "AtomicFireAmmo", "1", 0),
        ("ammo_medium", "AtomicFireAmmo", "1", 0),
    }
    assert len({generator.namespaced_selector(item) for item in atomic_bars}) == 2
    atomic_source = (generator.ROOT / "acs_source" / "hud" / "uh_cwepbar.acs").read_text(
        encoding="utf-8"
    )
    for threshold, constant in ((50, "MAXIMUM"), (40, "HIGH"), (30, "MEDIUM")):
        assert (
            f'CheckInventory("WeaponCharge") >= {threshold}' in atomic_source
            and f"AtomicFireWepU_DrawBar(UHBAR_ATOMICFIRE_{constant});" in atomic_source
        )
    assert atomic_source.count("AtomicFireWepU_DrawBar(UHBAR_ATOMICFIRE_MAXIMUM);") == 1
    assert "AtomicFireWepU_DrawBar(UHBAR_ATOMICFIRE_CHARGE);" in atomic_source
    charge_call = atomic_source.index("AtomicFireWepU_DrawBar(UHBAR_ATOMICFIRE_CHARGE);")
    for constant in ("MAXIMUM", "HIGH", "MEDIUM"):
        assert atomic_source.index(
            f"AtomicFireWepU_DrawBar(UHBAR_ATOMICFIRE_{constant});"
        ) < charge_call
    assert 'GetUserCVar(ConsolePlayerNumber(), "mm8bdm_usechargebars")' in atomic_source
    assert "Timer() % 2 == 1" in atomic_source

    base_graphics = load_fixture([("UHBar_BaseGraphics", [bar(
        "body", "UHBAR_BASEGRAPHICS",
        vertical_full="BARAMM13", horizontal_full="VARAMM13",
    )])])
    assert base_graphics["bars"][0]["vertical_full"] == "BARAMM13"

    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE")]),
        ("uhbar_fixture", [bar("body", "UHBAR_FIXTURE_TWO")]),
    ], "duplicate namespace")
    expect_failure([
        ("UHBar_Fixture", [
            bar("body", "UHBAR_FIXTURE"),
            bar("BODY", "UHBAR_FIXTURE_TWO"),
        ]),
    ], "duplicate id")
    expect_failure([
        ("UHBar_FixtureOne", [bar("body", "UHBAR_DUPLICATE")]),
        ("UHBar_FixtureTwo", [bar("body", "uhbar_duplicate")]),
    ], "duplicate constant")
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_" + "A" * 26)]),
    ], "long constant")
    expect_failure([
        ("UHBar_" + "A" * 26, [bar("body", "UHBAR_FIXTURE")]),
    ], "long helper")
    expect_failure([
        ("UHBar_Empty", []),
    ], "empty group")
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE", position="9")]),
    ], "invalid position")
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE", priority=-1)]),
    ], "invalid priority")
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE", capacity=0)]),
    ], "invalid capacity")
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE", source="Ammo-1")]),
    ], "invalid source")
    source_with_capacity = bar("body", "UHBAR_FIXTURE", source="Ammo1")
    expect_failure([
        ("UHBar_Fixture", [source_with_capacity]),
    ], "source with capacity")
    no_capacity = bar("body", "UHBAR_FIXTURE")
    del no_capacity["capacity"]
    expect_failure([
        ("UHBar_Fixture", [no_capacity]),
    ], "missing capacity")
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE", vertical_full="MISSING")]),
    ], "missing graphics")

    # --- DrawBar fill sanity -------------------------------------------------
    # The renderer takes the fill texture's own left/top offset as the default
    # draw offset (v_draw.cpp: parms->left/top = img->GetScaledLeftOffset/
    # TopOffset), so a fill whose frames carry an offset is drawn displaced from
    # its slot. bars.toml shipped that once via aliases over the 34_C_V1x
    # group, whose frames carried offset -16,-8 and -58,-184. Those offsets
    # were removed on 2026-09-15, so the shipped config must stay offset-free;
    # the detection itself is exercised on synthetic data.
    _, texture_defs, animations = generator.load_bar_graphics()
    assert generator.range_frames("34_B_V11", "34_B_V14") == [
        "34_b_v11", "34_b_v12", "34_b_v13", "34_b_v14",
    ]
    # An ANIMDEFS animation replaces the wrapper entirely, so an offset-free
    # wrapper around offset frames would still render displaced.
    assert generator.fill_animation_frames("083_B_VR", animations) == [
        "083_b1vr", "083_b2vr", "083_b3vr", "083_b4vr",
    ]
    for item in real_config["bars"]:
        for key in ("vertical_full", "horizontal_full"):
            assert generator.fill_offsets(item[key], texture_defs, animations) == [], (
                item["_namespace"], item["id"], key,
            )
    transparent_defs = {
        "transparent_fill": {"patches": ["tnt1a0"], "offset": (0, 0)},
        "animated_fill": {"patches": ["tnt1a0"], "offset": (0, 0)},
    }
    assert generator.is_transparent_fill("transparent_fill", transparent_defs, {})
    # Animation-aware transparency: a transparent wrapper is visible when its
    # animation supplies opaque frames.
    assert not generator.is_transparent_fill(
        "animated_fill", transparent_defs, {"animated_fill": ["b_bar01a"]}
    )
    assert not generator.is_transparent_fill("NOBAR", texture_defs, animations)
    # DecoyBot's formerly commented wrapper is now an animated charge bar.
    assert texture_defs["50_f_bar"]["patches"] == ["tnt1a0"]
    assert generator.fill_animation_frames("50_F_BAR", animations) == [
        "50_e_bar", "50_d_bar", "50_c_bar", "50_b_bar",
    ]
    assert not generator.is_transparent_fill("50_F_BAR", texture_defs, animations)
    assert texture_defs["50_k_bar"]["patches"] == ["tnt1a0"]
    assert generator.fill_animation_frames("50_K_BAR", animations) == [
        "50_j_bar", "50_i_bar", "50_h_bar", "50_g_bar",
    ]
    assert not generator.is_transparent_fill("50_K_BAR", texture_defs, animations)
    # A definition that only exists in a comment is not a graphic at all.
    assert "50_only_comment" not in generator.parse_texture_defs(
        generator.strip_line_comments("// graphic 50_ONLY_COMMENT, 8, 56 {Patch TNT1A0, 0, 0}")
    )

    fake_defs = {
        "fake_off": {"patches": ["b_bar01a"], "offset": (-16, -8)},
        "fake_off_h": {"patches": ["fake_off"], "offset": (-58, -184)},
        "fake_plain": {"patches": ["b_bar01a"], "offset": (0, 0)},
        "fake_clear": {"patches": ["tnt1a0"], "offset": (0, 0)},
    }
    fake_anims = {"fake_wrap": ["fake_off"]}
    assert generator.fill_offsets("fake_wrap", fake_defs, fake_anims) == [
        ("fake_off", -16, -8),
    ]
    assert generator.fill_offsets("fake_off", fake_defs, fake_anims) == [
        ("fake_off", -16, -8),
    ]
    assert generator.fill_offsets("fake_plain", fake_defs, fake_anims) == []

    off_bar = bar("body", "UHBAR_OFF",
                  vertical_full="fake_off", horizontal_full="fake_off_h")
    try:
        generator.validate_fill_graphics([off_bar], fake_defs, fake_anims)
    except SystemExit:
        pass
    else:
        raise AssertionError("offset fill unexpectedly accepted")
    generator.validate_fill_graphics(
        [dict(off_bar, offset_fill_ack=True)], fake_defs, fake_anims
    )
    expect_failure([
        ("UHBar_Fixture", [bar("body", "UHBAR_FIXTURE", offset_fill_ack="yes")]),
    ], "non-boolean offset_fill_ack")

    clear_bar = bar(
        "body", "UHBAR_FIXTURE",
        vertical_full="fake_clear", horizontal_full="fake_clear",
    )
    try:
        generator.validate_fill_graphics([clear_bar], fake_defs, fake_anims)
    except SystemExit:
        pass
    else:
        raise AssertionError("transparent fill over opaque empty unexpectedly passed")
    generator.validate_fill_graphics(
        [dict(clear_bar, reverse_mask=True)], fake_defs, fake_anims
    )
    # --- CLI & Argument parser tests -----------------------------------------
    # Test load_bar_config with explicit config_path (no mutation of generator.CONFIG)
    with tempfile.TemporaryDirectory(prefix="uh-cli-test-") as temp_dir:
        temp_cfg = Path(temp_dir) / "custom_bars.toml"
        temp_cfg.write_text(toml_config([("UHBar_Direct", [bar("body", "UHBAR_DIRECT")])]), encoding="utf-8")
        direct_config = generator.load_bar_config(config_path=temp_cfg)
        assert len(direct_config["bars"]) == 1
        assert direct_config["bars"][0]["_namespace"] == "UHBar_Direct"

    # Test main() CLI check execution
    assert generator.main(["--check", "-q"]) == 0
    assert generator.main(["-v", "--check"]) == 0

    # Test mutual exclusivity of -v and -q
    try:
        generator.main(["-v", "-q", "--check"])
    except SystemExit:
        pass
    else:
        raise AssertionError("expected -v and -q combination to fail")

    check_cli_outputs()
    print("bar generator fixture checks: OK")


if __name__ == "__main__":
    main()
