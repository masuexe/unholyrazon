#!/usr/bin/env python3
"""Exercise result-music ACS with C stubs; ACC checks language compatibility.

Checks one-pass stops, stale timers and screen holds for short/long themes.
Delay injects replacement playback, including selecting the same lump again.
Startup stubs model v6b OPEN resets and its native two-player music trigger.
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
    lifecycle = (ROOT / "src/acs_source/unholy/uh_lifecycle.acs").read_text()
    startup = lifecycle.split('script "ub_StartUpSettings" OPEN {', 1)[1]
    startup = startup.split('script "ub_ValidateBossCombosDeferred"', 1)[0]
    # Execute the production startup tail after its last background-task launch.
    claim = startup.split('ACS_NamedExecute("uh_BackgroundTimer", 0);', 1)[1]
    claim = claim[:claim.index("\n}")]
    code = (STUBS + play.replace("function ", "") + result.replace("function ", "")
            + "void FinishStartup(void) {" + claim + "\n}\n" + TESTS)
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
#define BMSF_SETVAL 1
int uh_musicstate[2], duration, emulated, selections, stops, scheduled, waitticks;
int scheduledticks, scheduledgeneration, replacement;
int startup, native_state, native_pending, native_changes;
str playing = "";
void PlayMusic(str music);
int StrLen(str s) { return strlen(s); }
int FindSpace(str s, int n) { (void)s; (void)n; return -1; }
str StrLeft(str s, int n) { (void)n; return s; }
str StrRight(str s, int n) { (void)n; return s; }
int StringToInt(str s, int n) { (void)s; (void)n; return 0; }
/* ACS SetMusic's optional order argument is irrelevant to timer ownership. */
void SetMusic(str s, ...) { playing = s; selections++; if (!*s) stops++; }
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
void ACS_NamedTerminate(str name, int map) {
    assert(!strcmp(name, "core_musichandler") && map == 0);
    native_pending = 0;
}
void ACS_NamedExecuteWithResult(str name, int mode, int value) {
    assert(!strcmp(name, "core_bossmusicstate") && mode == BMSF_SETVAL);
    native_state = value;
}
/* v6b MUSSYS returns immediately above state 2; otherwise 2 living players
   in LMS trigger map boss music from state 0, bypassing UH's generation. */
void NativeDeathMusic(int living) {
    if (native_state > 2) return;
    if (living <= 2 && native_state == 0) {
        native_state = 1;
        native_changes++;
        SetMusic("MAPBOSS");
    }
}
void Delay(int ticks) {
    waitticks = ticks;
    /* MUSSYS/MAPCARDS reset this state during OPEN, after UH's first writes. */
    if (startup) { assert(ticks == 1); native_state = 0; }
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

    /* Reproduce the report before the startup claim: three living players,
       defeat jingle, then another death starts native boss music. */
    duration = 4 * 65536;
    native_state = 0;
    NativeDeathMusic(3);
    UH_PlayResultMusic(0);
    NativeDeathMusic(2);
    assert(!strcmp(playing, "MAPBOSS"));
    int previous_stops = stops;
    StopResultMusic(scheduledticks, scheduledgeneration);
    assert(stops == previous_stops + 1 && !*playing);

    /* Even if UH initially disabled native music, OPEN resets used to undo it.
       The deferred production claim also cancels a pending native restore. */
    startup = 1; native_state = 100; native_pending = 1;
    FinishStartup();
    startup = 0;
    assert(native_state > 2 && native_pending == 0);
    int previous_changes = native_changes;
    UH_PlayResultMusic(0);
    NativeDeathMusic(2);
    NativeDeathMusic(1);
    assert(native_changes == previous_changes && !strcmp(playing, "RESULT"));
    previous_stops = stops;
    StopResultMusic(scheduledticks, scheduledgeneration);
    assert(stops == previous_stops + 1 && !*playing);
    puts("Result music: known/unknown duration, emulation allowance, stale timers and short/long screen holds passed.");
    return 0;
}
'''


if __name__ == "__main__":
    main()
