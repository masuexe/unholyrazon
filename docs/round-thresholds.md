# Round thresholds

Configure these in **Unholy Server Options → Game Rules → Round Thresholds**.
Press Enter to type a value. All seven settings are server-owned, saved in the
host's configuration, and clamped to 1–100 when read by gameplay code.

| Setting / CVAR | Default | Effect |
|----------------|---------|--------|
| Win Streak Limit / `uh_sv_winstreaklimit` | 6 | Every N consecutive survivor wins queues a random Strongman. |
| Lose Streak Limit / `uh_sv_losestreaklimit` | 6 | Every N consecutive survivor losses grants Mercy Runes. |
| Hell Mark Limit / `uh_sv_hellmarklimit` | 10 | Marks earned by winning with a last survivor queue FinalSampi. |
| Speciman Frag Limit / `uh_sv_specimanfraglimit` | 15 | Speciman deaths queue FinalSpeciman. |
| Gauntlet Treasure Limit / `uh_sv_treasurecountlimit` | 10 | Collecting N treasures spawns a True Power item and consumes N treasures. |
| LMS Count Limit / `uh_sv_lmscountlimit` | 5 | Every N times a player becomes the last survivor triggers Bad LMS. |
| Bonus Event Round Limit / `uh_sv_bonuseventlimit` | 8 | Normal rounds before the next bonus event. |

Changes apply at the next corresponding threshold check; existing counters
are retained. Lowering the treasure limit preserves any surplus after a
redemption. Treasure redemption is checked when another treasure is picked up.

These use the current UH names rather than Razon 3's `RZ_WinStreakLimit`,
`RZ_LoseStreakLimit`, `RZ_HellMarkLimit`, `RZ_FaggassoFragLimit`,
`RZ_TreasureCountLimit`, `RZ_LMSCountLimit`, and `RZ_BonusGameLimit`.
The old names are not aliases. Current v4 defaults remain unchanged.
