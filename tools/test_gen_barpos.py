#!/usr/bin/env python3
"""Deterministic validation fixtures for _gen_barpos.py."""

from pathlib import Path
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
        "legacy_catalog": True,
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
    assert any("DrawBar \"002B_VAR\", \"VNOBAR\", Ammo1," in line
               for line in append_lines)
    source_actors = generator.gen_namespaced_barfx_actors(source_config)
    assert "actor UHBar_Source_P1L0Selector" in source_actors
    assert "UHBar_Source_P1L0_BodyAmmo" not in source_actors
    source_acs = generator.gen_generated_acs(source_config)
    assert "function void Source_DrawBar(int id)" in source_acs
    assert "SetAmmoAmountAndCapacity" not in source_acs
    assert 'SetActorInventory(cam, "UHBar_Source_P1L0Selector", 0);' in source_acs
    assert "UHBar_Source_P1L0_BodyAmmo" not in source_acs

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
    print("bar generator fixture checks: OK")


if __name__ == "__main__":
    main()
