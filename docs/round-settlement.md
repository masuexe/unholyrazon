# Cancellable round settlement

The server option `uh_sv_resumeonrevive` defaults to `true` and is available in
Unholy Server Options → Game Rules → Resume Battle If Enemies Return:

```text
uh_sv_resumeonrevive false  // Existing immediate settlement behavior
uh_sv_resumeonrevive true   // Allow ordinary-round settlement cancellation
```

The option applies to ordinary Survivor vs Boss/Demoneye rounds. Bonus events,
Boss vs Boss, early boss departure and forced endings keep their existing
behavior. Native LMS result sequences remain final, including the engine's
automatic win when only one living/respawnable player remains.

Each victory candidate reads the option once. Changing it during a pending
settlement affects the next candidate; it does not change the current window.
The original exit windows are retained: 315 tics after survivor defeat, and
360 tics after survivor victory. No extra exit delay is added at confirmation.

During a cancellable window the result text/music play and the updated streak
is shown immediately. Result and streak text use the normal wording, without
a pending label. `gameover` stays
false. Victory watchers, status broadcasts and revival hooks remain alive.
The round timer pauses, AFK penalties reset and the two-player X-Ray marker is
cleared. Gameplay protections remain as they were during combat; their existing
settlement changes happen only at final confirmation.

If at least one living, nonspectating Survivor and one living, nonspectating
Boss or Demoneye return before confirmation, the result is cancelled. The HUD
clears, the streak rolls back to its previous value, and an explicit
"Opponents returned! / Round result cancelled - battle continues!" notice
appears on two lines. Battle music returns
and the timer resumes its remaining duration.
Existing LMS awards and the original battle start time are preserved. Returning
players on only one side do not cancel settlement. A revival on the deadline
tic takes precedence over expiry, but never over a native LMS result sequence.

The streak updates provisionally at the start of each window and is retained
on confirmation, without a second increment. Cancellation or a superseding
forced ending restores the previous streak. Mercy, streak rewards,
fast-kill/PERFECT bonuses, marks, combo cleanup and event end processing still
run only once the result is final. Fast-kill time and PERFECT use
the final candidate's original battle-time/player-count snapshot. Generation
checks prevent stale settlement owners or exit tasks from ending a later window.

Run `python3 tools/check_round_settlement.py` for the actual ACS decision,
ownership and restoration logic under C stubs, and compile `unholy` plus
`rz_debug` with ACC. The logic test does not simulate ACS scheduling or network
delivery. Manual multiplayer checks should cover both victory directions,
Boss/Demoneye revival, same-side revival, repeated cancellation, deadline revival,
native LMS victory and a forced ending during the window.
