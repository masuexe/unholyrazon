#!/usr/bin/env python3
"""Exercise result-music ACS with C stubs; ACC checks language compatibility.

Checks one-pass stops, stale timers and screen holds for short/long themes.
Delay injects replacement playback, including selecting the same lump again.
This does not emulate network or audio-device timing.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "src/acs_source/unholy/uh_music.acs").read_text()
    play = source[source.index("function void PlayMusic(str music)"):
                  source.index("function int UH_MusicLumpPublishable")]
    result = source[source.index("function int UH_PlayResultMusic"):
                    source.index("function int PlayMusic_Winner")]
    result = result.replace('script "uh_StopResultMusic"', 'void StopResultMusic')
    code = STUBS + play.replace("function ", "") + result.replace("function ", "") + TESTS
    with tempfile.TemporaryDirectory(prefix="uh-result-music-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(code)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(path / "test.c"), "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)


STUBS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef const char *str;
#define UH_MUSIC_GENERATION 1
int uh_musicstate[2], duration, emulated, selections, stops, scheduled, waitticks;
int scheduledticks, scheduledgeneration, replacement;
void PlayMusic(str music);
int StrLen(str s) { return strlen(s); }
int FindSpace(str s, int n) { (void)s; (void)n; return -1; }
str StrLeft(str s, int n) { (void)n; return s; }
str StrRight(str s, int n) { (void)n; return s; }
int StringToInt(str s, int n) { (void)s; (void)n; return 0; }
/* ACS SetMusic's optional order argument is irrelevant to timer ownership. */
void SetMusic(str s, ...) { selections++; if (!*s) stops++; }
int UH_MusicLumpPublishable(str s) { return *s && strcmp(s, "*"); }
void UH_ClearPublishedMusic(int context) { (void)context; }
void UH_PlayBossRow(int row, int context, int announce) {
    assert(row == 0 && context == 0 && announce == 0); PlayMusic("RESULT");
}
int GetBossMusicDurationByRow(int row) { assert(row == 0); return duration; }
int GetBossMusicEmuFlagByRow(int row) { assert(row == 0); return emulated; }
int Max(int a, int b) { return a > b ? a : b; }
int RoundFixedToInt(int x) { return (x + 32768) >> 16; }
void ACS_NamedExecuteAlways(str name, int map, int ticks, int generation) {
    assert(!strcmp(name, "uh_StopResultMusic") && map == 0);
    scheduled++; scheduledticks = ticks; scheduledgeneration = generation;
}
void Delay(int ticks) {
    waitticks = ticks;
    if (replacement == 1) PlayMusic("BATTLE");
    if (replacement == 2) PlayMusic("RESULT");
    if (replacement == 3) PlayMusic("*");
}
'''

TESTS = r'''
int main(void) {
    assert(UH_PlayResultMusic(-1) == 0 && selections == 0 && scheduled == 0);
    duration = -65536;
    assert(UH_PlayResultMusic(0) == 0 && scheduled == 0 && selections == 1);
    duration = 0;
    assert(UH_PlayResultMusic(0) == 0 && scheduled == 0);
    duration = 2 * 65536;
    assert(UH_PlayResultMusic(0) == 70 && scheduled == 1);
    StopResultMusic(scheduledticks, scheduledgeneration);
    assert(waitticks == 70 && stops == 1);
    /* Re-running an expired instance cannot stop subsequent playback. */
    PlayMusic("BATTLE");
    StopResultMusic(scheduledticks, scheduledgeneration);
    assert(stops == 1);
    for (replacement = 1; replacement <= 3; replacement++) {
        assert(UH_PlayResultMusic(0) == 70);
        StopResultMusic(scheduledticks, scheduledgeneration);
        assert(stops == 1);
    }
    replacement = 0;
    emulated = 1;
    assert(UH_PlayResultMusic(0) == 82);
    StopResultMusic(scheduledticks, scheduledgeneration);
    assert(waitticks == 82 && stops == 2);
    /* Screen hold is independent of the one-pass stop, with a map-change tail. */
    assert(UH_CoverResultMusic(315, 70) == 315);
    assert(UH_CoverResultMusic(315, 420) == 432);
    assert(UH_CoverResultMusic(315, 0) == 315);
    assert(UH_CoverResultMusic(70, 82) == 94);
    duration = 1; emulated = 0;
    assert(UH_PlayResultMusic(0) == 1);
    puts("Result music: known/unknown duration, emulation allowance, stale timers and short/long screen holds passed.");
    return 0;
}
'''


if __name__ == "__main__":
    main()
