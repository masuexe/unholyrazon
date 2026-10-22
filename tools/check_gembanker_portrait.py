#!/usr/bin/env python3
"""Check viewer-local mode selection, animation timing and portrait sizes.

Executes the actual ACS selector with C stubs. Does not test engine drawing.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "src/acs_source/_imports/uhdt.acs").read_text()
    selector = re.search(r"function str UH_GemBankerPortrait\([^\n]+\n.*?^}",
                         source, re.M | re.S).group().replace("function ", "")
    stubs = r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <strings.h>
typedef const char *str;
int mode;
int StrICmp(str a, str b) { return strcasecmp(a, b); }
int GetCVar(str name) {
  assert(!strcmp(name, "uh_cl_GemBankerPortrait"));
  return mode;
}
'''
    tests = r'''
int main(void) {
  str raw[] = {"UFACE22", "GBF_SLOW", "GBF_FAST"};
  str scaled[] = {"UB022MUG", "GBM_SLOW", "GBM_FAST"};
  // Includes invalid settings and every mode-to-mode transition, including
  // cached portraits belonging to a dead player or a spectated subject.
  for (mode = -2; mode <= 4; mode++) {
    int expected = mode == 1 || mode == 2 ? mode : 0;
    for (int previous = 0; previous < 3; previous++) {
      assert(!strcmp(UH_GemBankerPortrait(raw[previous]), raw[expected]));
      assert(!strcmp(UH_GemBankerPortrait(scaled[previous]), scaled[expected]));
    }
    assert(!strcmp(UH_GemBankerPortrait("ub022mug"), scaled[expected]));
    assert(!strcmp(UH_GemBankerPortrait("UB001MUG"), "UB001MUG"));
    assert(!strcmp(UH_GemBankerPortrait(""), ""));
  }
  return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="uh-gembanker-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(stubs + selector + tests)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)

    textures = (ROOT / "src/TEXTURES.gembanker").read_text()
    names = re.findall(r"^texture (\w+),", textures, re.M)
    assert len(names) == len(set(names)) == 18, "duplicate portrait textures"
    assert all(len(name) <= 8 for name in names)
    # All animation frames preserve their target's logical dimensions.
    for name, scale in re.findall(r"^texture (\w+), 32, 32 \{(.*?)Patch", textures, re.M):
        if name.startswith("GBM"):
            assert "XScale 4.0 YScale 4.0" in scale, name
        else:
            assert "Scale" not in scale, name
    animations = (ROOT / "src/ANIMDEFS.gembanker").read_text()
    blocks = re.findall(r"^texture (\w+) allowdecals\n(.*?)(?=^texture|\Z)",
                        animations, re.M | re.S)
    assert len(blocks) == 4
    for target, body in blocks:
        assert target in names
        prefix = "GBFACE" if target.startswith("GBF_") else "GBMUG"
        frames = re.findall(r"pic (\w+) (rand \d+ \d+|tics \d+)", body)
        assert [name for name, _ in frames] == [prefix + letter for letter in "ABCDEFG"]
        expected = "rand 350 700" if target.endswith("SLOW") else "tics 4"
        assert all(duration == expected for _, duration in frames)
        assert all(name in names and name != target for name, _ in frames)
    cvars = (ROOT / "src/CVARINFO.user").read_text()
    assert re.search(r"^local int uh_cl_GemBankerPortrait = 1;", cvars, re.M)
    assert re.search(r"^user bool uh_cl_GemBankerHud = true;", cvars, re.M)
    menu = (ROOT / "src/MENUDEF").read_text()
    assert '"uh_cl_GemBankerPortrait", "UH_Menu_GemBankerPortrait"' in menu
    print("GemBanker portraits: local selector, mode changes, timing, dimensions and menu passed")


if __name__ == "__main__":
    main()
