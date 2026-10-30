# A_Recoil Usage Inventory

Generated: 2026-10-30 (Asia/Taipei). Scope: project DECORATE sources under `src/`.

## Summary

- Total `A_Recoil` lines: **480**
- Active (in code): **442**
- Commented out: **38**
- Distinct files with active use: **117**

### Active occurrences by area

| Area | Active |
|---|---:|
| classes/bosses | 242 |
| classes/survivors | 124 |
| coopenemies | 43 |
| classes/eyes | 16 |
| items | 9 |
| unepic (core replace / FX) | 6 |
| player (core pain / classbase) | 2 |

## v6c migration pattern

MM8BDM v6c routes actor movement action functions through ACS wrappers so they respect the
new dash/fling aprop factors. Observed substitutions (v6b -> v6c base game):

| v6b (direct action) | v6c (ACS wrapper) |
|---|---|
| `A_Recoil(v)` | `ACS_NamedExecuteWithResult("core_dashRecoil", v)` or `"core_flingRecoil"` |
| `A_ChangeVelocity(...)` | `"core_dashChangeVelocity"` / `"core_flingChangeVelocity"` |
| `ThrustThingZ(...)` | `"core_dashThrustThingZ"` / `"core_flingThrustThingZ"` |

This migration is **selective**, not a blanket replacement. The v6c base game still contains
about 414 plain `A_Recoil` calls. Only designated weapons were converted. For example
`inventory/mmb/tengublade.txt`: v6b `A_Recoil(-50)` -> v6c `core_dashRecoil(-50)`.
Therefore do not replace every `A_Recoil` blindly. Match each actor against its v6c
counterpart, or decide by movement semantics (dash vs fling vs plain).

## Concrete migration candidates found

Project files that mirror a v6c base weapon which was itself converted:

- `src/actors/classes/survivors/megaman_copyweps/mm1/oilslider.dec`
  - `A_Recoil(-1.4375)` at line 237 and `A_Recoil(-2.875)` at line 240 -> `core_dashRecoil`
  - Also `ThrustThingZ(0, 2, 0, 0)` at line 250 -> `core_dashThrustThingZ`
- Copyweapons already migrated in this project: `hardknuckle`, `tengublade`, `breakdash`, `sakugarne`, `tornadohold` (core_dash* family).

## All active occurrences, by area

### classes/bosses (242)

- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:109` — 8I02 A 0 A_Recoil(-95)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:142` — 8I02 A 0 A_Recoil(100)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:172` — 8I02 C 1 A_Recoil(-10)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:175` — 8I02 C 1 A_Recoil(-15)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:178` — 8I02 C 1 A_Recoil(-20)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:181` — 8I02 C 1 A_Recoil(-25)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:184` — 8I02 C 1 A_Recoil(-30)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:187` — 8I02 C 1 A_Recoil(-35)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:190` — 8I02 C 1 A_Recoil(-40)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:193` — 8I02 C 1 A_Recoil(-45)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:196` — 8I02 C 1 A_Recoil(-50)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:199` — 8I02 C 1 A_Recoil(-55)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:229` — 8I02 A 0 A_Recoil(1)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:271` — 8I02 A 0 A_Recoil(35)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:295` — 8I02 A 0 A_Recoil(-65)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:333` — 8I02 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:339` — 8I02 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:345` — 8I02 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/SinfulBusterExpert_W.dec:752` — X_8A H 1 A_Recoil(-2)
- `src/actors/classes/bosses/RedTankBot_W.dec:94` — TNT1 A 0 A_Recoil(-35)
- `src/actors/classes/bosses/RedTankBot_W.dec:145` — 8H35 A 0 A_Recoil(-35)
- `src/actors/classes/bosses/Dixieandoff_W.dec:63` — 8H23 A 0 A_Recoil(-20)
- `src/actors/classes/bosses/Dixieandoff_W.dec:130` — 8H23 N 0 A_Recoil(-5)
- `src/actors/classes/bosses/Dixieandoff_W.dec:136` — 8H23 N 0 A_Recoil(-5)
- `src/actors/classes/bosses/Dixieandoff_W.dec:201` — TNT1 A 0 A_Recoil(35)
- `src/actors/classes/bosses/AstromancerSimple_W.dec:152` — X_8B G 1 A_Recoil(2.5)
- `src/actors/classes/bosses/TropicalMWS_W.dec:92` — 8I10 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/AbePenny_W.dec:167` — TNT1 A 4 A_Recoil(-35)
- `src/actors/classes/bosses/TricksterGiovanni_W.dec:395` — TNT1 A 0 A_Recoil(-35)
- `src/actors/classes/bosses/TricksterGiovanni_W.dec:666` — X_KC ABCDABCD 1 A_Recoil(3)
- `src/actors/classes/bosses/TricksterGiovanni_W.dec:697` — X_KC ABCD 2 A_Recoil(-10)
- `src/actors/classes/bosses/SirAlpha_W.dec:53` — TNT1 A 0 A_Recoil(-7)
- `src/actors/classes/bosses/SirAlpha_W.dec:67` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/SirAlpha_W.dec:83` — 8I03 J 0 A_Recoil(-35)
- `src/actors/classes/bosses/SirAlpha_W.dec:85` — 8I03 K 0 A_Recoil(-15)
- `src/actors/classes/bosses/SirAlpha_W.dec:130` — 8I03 P 0 A_Recoil(25)
- `src/actors/classes/bosses/SirAlpha_W.dec:146` — 8I03 A 0 A_Recoil(-30)
- `src/actors/classes/bosses/SirAlpha_W.dec:151` — 8I03 A 0 A_Recoil(-5)
- `src/actors/classes/bosses/SirAlpha_W.dec:175` — 8I03 E 0 A_Recoil(5)  // -5
- `src/actors/classes/bosses/SirAlpha_W.dec:223` — 8I03 M 0 A_Recoil(-30)
- `src/actors/classes/bosses/SirAlpha_W.dec:564` — SCLA J 0 A_Recoil(5)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:115` — 8H06 G 1 A_Recoil(-10)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:117` — 8H06 G 1 A_Recoil(-15)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:119` — 8H06 G 1 A_Recoil(-20)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:121` — 8H06 G 1 A_Recoil(-25)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:123` — 8H06 G 1 A_Recoil(-30)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:125` — 8H06 G 1 A_Recoil(-35)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:127` — 8H06 G 1 A_Recoil(-40)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:129` — 8H06 G 1 A_Recoil(-45)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:131` — 8H06 G 1 A_Recoil(-50)
- `src/actors/classes/bosses/OfficerJohnson_W.dec:133` — 8H06 G 1 A_Recoil(-55)
- `src/actors/classes/bosses/DonJavier_W.dec:33` — 8H02 A 0 A_Recoil(-40)
- `src/actors/classes/bosses/DonJavier_W.dec:56` — 8H02 A 0 A_Recoil(-25)
- `src/actors/classes/bosses/DonJavier_W.dec:130` — 8H02 B 0 A_Recoil(-15)
- `src/actors/classes/bosses/DonJavier_W.dec:145` — 8H02 B 0 A_Recoil(-10)
- `src/actors/classes/bosses/RussianGuts_W.dec:148` — TNT1 A 0 A_Recoil(-35)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:44` — 8L00 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:49` — 8L00 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:51` — 8L00 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:53` — 8L00 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:55` — 8L00 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:57` — 8L00 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:119` — 8L00 A 0 A_Recoil(-70)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:130` — 8L00 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:137` — 8L00 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:171` — 8L00 A 0 A_Recoil(-40)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:208` — 8L00 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:216` — 8L00 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:232` — 8L00 A 0 A_Recoil(-75)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:602` — X_4G ABABAB 1 A_Recoil(3)
- `src/actors/classes/bosses/ZankokunaHellbot_W.dec:615` — X_4G AB 1 A_Recoil(-10)
- `src/actors/classes/bosses/Joterra_W.dec:1049` — X_0E F 0 A_Recoil(5)
- `src/actors/classes/bosses/CrazedGrenademan_W.dec:189` — 8H55 D 0 A_Recoil(-5)  // -5
- `src/actors/classes/bosses/CrazedGrenademan_W.dec:195` — 8H55 E 0 A_Recoil(-5)  // -5
- `src/actors/classes/bosses/CrazedGrenademan_W.dec:202` — 8H55 D 0 A_Recoil(-5)  // -5
- `src/actors/classes/bosses/CrazedGrenademan_W.dec:208` — 8H55 E 0 A_Recoil(-5)  // -5
- `src/actors/classes/bosses/ElitistSue_W.dec:279` — TNT1 A 1 A_Recoil(-25)
- `src/actors/classes/bosses/GraniteMauler_W.dec:300` — 8I14 B 1 A_Recoil(-4)
- `src/actors/classes/bosses/GraniteMauler_W.dec:320` — 8I14 D 0 A_Recoil(10)
- `src/actors/classes/bosses/GraniteMauler_W.dec:380` — TNT1 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/GraniteMauler_W.dec:384` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/GraniteMauler_W.dec:388` — TNT1 A 0 A_Recoil(-20)
- `src/actors/classes/bosses/GraniteMauler_W.dec:392` — TNT1 A 0 A_Recoil(-25)
- `src/actors/classes/bosses/GraniteMauler_W.dec:396` — TNT1 A 0 A_Recoil(-30)
- `src/actors/classes/bosses/GraniteMauler_W.dec:445` — TNT1 A 0 A_Recoil(-1.3)
- `src/actors/classes/bosses/GraniteMauler_W.dec:450` — TNT1 A 0 A_Recoil(-2.6)
- `src/actors/classes/bosses/GraniteMauler_W.dec:453` — TNT1 A 0 A_Recoil(-3.25)
- `src/actors/classes/bosses/ElitistWaylon_W.dec:97` — 8H07 E 0 A_Recoil(-45)
- `src/actors/classes/bosses/ElitistWaylon_W.dec:118` — 8H07 E 0 A_Recoil(-45)
- `src/actors/classes/bosses/ElitistWaylon_W.dec:393` — X_8A H 1 A_Recoil(-2)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:155` — 8H61 E 0 A_Recoil(-25)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:162` — 8H61 E 0 A_Recoil(-2)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:167` — 8H61 E 0 A_Recoil(-2)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:172` — 8H61 E 0 A_Recoil(-2)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:290` — 8H61 E 0 A_Recoil(-40)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:359` — TNT1 A 1 A_Recoil(20)
- `src/actors/classes/bosses/ChieftainTomahawk_W.dec:776` — TNT1 A 0 A_Recoil(6)
- `src/actors/classes/bosses/Troutius_W.dec:73` — 8H49 I 2 A_Recoil(15)
- `src/actors/classes/bosses/Troutius_W.dec:306` — 8H49 D 0 A_Recoil(-35)
- `src/actors/classes/bosses/Troutius_W.dec:348` — 8H49 I 0 A_Recoil(-30)
- `src/actors/classes/bosses/Troutius_W.dec:353` — 8H49 I 0 A_Recoil(-5)
- `src/actors/classes/bosses/Troutius_W.dec:371` — 8H49 J 0 A_Recoil(5)  // -5
- `src/actors/classes/bosses/Troutius_W.dec:703` — TNT1 A 0 A_Recoil(7)
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:89` — 8H57 A 0 A_Recoil(-15)  // -20
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:169` — 8H57 H 0 A_Recoil(-35)  // -20
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:187` — 8H57 H 1 A_Recoil(-5)
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:208` — 8H57 G 1 A_Recoil(20)
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:238` — 8H57 H 0 A_Recoil(35)  // -20
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:255` — 8H57 H 1 A_Recoil(5)
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:282` — TNT1 A 0 A_Recoil(-50)  /// ///////////////////CHANGE LEAP TO BE A BIT MORE AIMABLE, USE RATHORS AIMING
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:639` — CMDH GGGGGGG 1 A_Recoil(3)
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:662` — CMDH G 0 A_Recoil(-3)  // -5
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:895` — TNT1 A 0 A_Recoil(20)
- `src/actors/classes/bosses/BalladeGB_W.dec:144` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/ShinNegaman_W.dec:78` — 8H21 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/ShinNegaman_W.dec:205` — 8H21 A 0 A_Recoil(-40)
- `src/actors/classes/bosses/ShinNegaman_W.dec:239` — 8H21 B 0 A_Recoil(15)
- `src/actors/classes/bosses/ShinNegaman_W.dec:427` — TNT1 A 0 A_Recoil(-1)
- `src/actors/classes/bosses/ShinNegaman_W.dec:585` — TMFX DCBA 1 A_Recoil(3)
- `src/actors/classes/bosses/Berserker_W.dec:72` — 8H73 A 0 A_Recoil(-20)
- `src/actors/classes/bosses/HalfPressHardman_W.dec:120` — 8H50 A 0 A_Recoil(-1)
- `src/actors/classes/bosses/HalfPressHardman_W.dec:367` — TNT1 A 0 A_Recoil(-3)
- `src/actors/classes/bosses/YelTankBot_W.dec:180` — 8H37 A 0 A_Recoil(-20)
- `src/actors/classes/bosses/YelTankBot_W.dec:339` — X_4G AAABBB 1 A_Recoil(2)
- `src/actors/classes/bosses/Magnetismo_W.dec:53` — 8H20 A 0 A_Recoil(35)
- `src/actors/classes/bosses/SoccerRock_W.dec:50` — H0RK K 0 A_Recoil(-20)
- `src/actors/classes/bosses/Lin_W.dec:51` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/Lin_W.dec:79` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/Lin_W.dec:179` — 8H67 F 0 A_Recoil(-15)
- `src/actors/classes/bosses/Lin_W.dec:207` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/IronCurtain_W.dec:232` — 8H11 C 0 A_Recoil(-4)
- `src/actors/classes/bosses/IronCurtain_W.dec:239` — 8H11 C 0 A_Recoil(-4)
- `src/actors/classes/bosses/IronCurtain_W.dec:295` — 8H11 A 0 A_Recoil(-30)
- `src/actors/classes/bosses/IronCurtain_W.dec:300` — 8H11 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/IronCurtain_W.dec:319` — 8H11 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/IronCurtain_W.dec:353` — 8H11 A 0 A_Recoil(10)
- `src/actors/classes/bosses/IronCurtain_W.dec:451` — TNT1 A 0 A_Recoil(35)
- `src/actors/classes/bosses/IronCurtain_W.dec:875` — CMDH GGGGGGG 1 A_Recoil(3)
- `src/actors/classes/bosses/Rogue_W.dec:352` — 8I06 R 0 A_Recoil(-10)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:57` — TNT1 A 0 A_Recoil(-14)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:76` — TNT1 A 0 A_Recoil(-25)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:122` — 9I03 J 0 A_Recoil(-35)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:124` — 9I03 K 0 A_Recoil(-15)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:143` — 9I03 C 0 A_Recoil(-35)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:192` — 9I03 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:197` — 9I03 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:211` — 9I03 D 0 A_Recoil(-10)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:225` — 9I03 E 0 A_Recoil(-10)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:239` — 9I03 E 0 A_Recoil(-14)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:253` — 9I03 E 0 A_Recoil(-14)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:267` — 9I03 E 0 A_Recoil(-20)
- `src/actors/classes/bosses/SirAlphaEX_W.dec:286` — 9I03 M 0 A_Recoil(-50)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:273` — 8L01 C 1 Offset(-114, 60) A_Recoil(-30)  // -5
- `src/actors/classes/bosses/EyelentoMajor_W.dec:396` — TNT1 A 0 A_Recoil(-60)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:423` — TNT1 A 0 A_Recoil(-25)  // -45
- `src/actors/classes/bosses/EyelentoMajor_W.dec:627` — TNT1 A 0 A_Recoil(-15)  // -5
- `src/actors/classes/bosses/EyelentoMajor_W.dec:631` — TNT1 A 0 A_Recoil(-25)  // -15
- `src/actors/classes/bosses/EyelentoMajor_W.dec:635` — TNT1 A 0 A_Recoil(-35)  // -25
- `src/actors/classes/bosses/EyelentoMajor_W.dec:957` — TNT1 A 0 A_Recoil(25)  // 20
- `src/actors/classes/bosses/CaptainDevilEye_W.dec:64` — 8H09 E 0 A_Recoil(-25)
- `src/actors/classes/bosses/RedBaronDuo_W.dec:79` — 8H33 A 0 A_Recoil(10)
- `src/actors/classes/bosses/RedBaronDuo_W.dec:139` — X_4G A 0 A_Recoil(-6)
- `src/actors/classes/bosses/SovietIgniter_W.dec:299` — X_1E EEEEEE 1 A_Recoil(-3)
- `src/actors/classes/bosses/SadFaceToadMan_W.dec:86` — 8I04 E 1 A_Recoil(-24)
- `src/actors/classes/bosses/SadFaceToadMan_W.dec:186` — 8I04 J 1 A_Recoil(-36)
- `src/actors/classes/bosses/SadFaceToadMan_W.dec:243` — 8I04 G 0 A_Recoil(-125)
- `src/actors/classes/bosses/KakusaretaSutoka_W.dec:126` — 8H05 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/ShinHellBot_W.dec:51` — 8H08 O 0 A_Recoil(-75)
- `src/actors/classes/bosses/ShinHellBot_W.dec:86` — 8H08 A 0 A_Recoil(-40)
- `src/actors/classes/bosses/ShinHellBot_W.dec:114` — 8H08 A 0 A_Recoil(-70)
- `src/actors/classes/bosses/ShinHellBot_W.dec:222` — 8H08 A 0 A_Recoil(-40)
- `src/actors/classes/bosses/ShinHellBot_W.dec:256` — 8H08 J 0 A_Recoil(-10)
- `src/actors/classes/bosses/ShinHellBot_W.dec:263` — 8H08 P 0 A_Recoil(-10)
- `src/actors/classes/bosses/ShinHellBot_W.dec:274` — 8H08 A 0 A_Recoil(-75)
- `src/actors/classes/bosses/ShinHellBot_W.dec:584` — X_4G ABABAB 1 A_Recoil(3)
- `src/actors/classes/bosses/Hellbot_W.dec:54` — 8I00 B 0 A_Recoil(-45)
- `src/actors/classes/bosses/Hellbot_W.dec:112` — 8I00 E 0 A_Recoil(-40)
- `src/actors/classes/bosses/Hellbot_W.dec:140` — 8I00 D 0 A_Recoil(-70)
- `src/actors/classes/bosses/Hellbot_W.dec:227` — 8I00 A 0 A_Recoil(-40)
- `src/actors/classes/bosses/Hellbot_W.dec:633` — X_KC ABCDAB 1 A_Recoil(2.5)
- `src/actors/classes/bosses/Hellbot_W.dec:656` — X_KC ABCD 1 A_Recoil(-10)
- `src/actors/classes/bosses/TrueBusterExpert_W.dec:138` — 8H00 "#" 0 A_Recoil(-75)
- `src/actors/classes/bosses/BlackDevilEye_W.dec:54` — 9H09 B 0 A_Recoil(-25)
- `src/actors/classes/bosses/CXAirman_W.dec:332` — TNT1 A 0 A_Recoil(-4)
- `src/actors/classes/bosses/CXAirman_W.dec:367` — 8Q01 AABBCC 1 A_Recoil(3)
- `src/actors/classes/bosses/CXAirman_W.dec:385` — 8Q01 AABBCC 1 A_Recoil(2)
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:233` — TENA E 0 A_Recoil(-50)  // 50
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:352` — SHAH B 0 A_Recoil(-35)  // -20
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:423` — TNT1 A 1 A_Recoil(20)  /// /
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:472` — TNT1 A 1 A_Recoil(5)  /// /
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:2011` — SHAG I 2 A_Recoil(-10)  //
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:2012` — SHAG I 3 A_Recoil(-20)  //
- `src/actors/classes/bosses/TheShadowManMythBoss_W.dec:2013` — SHAG I 6 A_Recoil(-40)  // 8
- `src/actors/classes/bosses/RedeadGuts_W.dec:127` — 8H48 C 0 A_Recoil(-20)
- `src/actors/classes/bosses/RedeadGuts_W.dec:131` — 8H48 C 1 Offset(80, -98) A_Recoil(-5)
- `src/actors/classes/bosses/RedeadGuts_W.dec:132` — 8H48 C 1 Offset(80, -98) A_Recoil(-10)
- `src/actors/classes/bosses/RedeadGuts_W.dec:133` — 8H48 C 1 Offset(80, -98) A_Recoil(-25)
- `src/actors/classes/bosses/RedeadGuts_W.dec:217` — TNT1 A 0 A_Recoil(-20)
- `src/actors/classes/bosses/RedeadGuts_W.dec:521` — TNT1 A 0 A_Recoil(-2)
- `src/actors/classes/bosses/RedeadGuts_W.dec:525` — TNT1 A 0 A_Recoil(-1.15f)
- `src/actors/classes/bosses/BluTankBot_W.dec:137` — TNT1 A 0 A_Recoil(-20)  // -20
- `src/actors/classes/bosses/Scrotoman_W.dec:172` — 8I13 A 0 A_Recoil(-50)
- `src/actors/classes/bosses/Scrotoman_W.dec:188` — 8I13 EEEE 2 Offset(78, 32) A_Recoil(-25)
- `src/actors/classes/bosses/Scrotoman_W.dec:242` — TNT1 A 5 A_Recoil(-75)
- `src/actors/classes/bosses/Scrotoman_W.dec:285` — TNT1 A 0 A_Recoil(-15)
- `src/actors/classes/bosses/Scrotoman_W.dec:288` — TNT1 A 0 A_Recoil(-7.5)
- `src/actors/classes/bosses/Scrotoman_W.dec:499` — TNT1 A 0 A_Recoil(20)
- `src/actors/classes/bosses/Balrog_W.dec:103` — 8H59 A 1 Offset(0, 35) A_Recoil(-7)
- `src/actors/classes/bosses/Balrog_W.dec:105` — 8H59 A 1 Offset(0, 40) A_Recoil(-5)
- `src/actors/classes/bosses/Balrog_W.dec:108` — 8H59 A 1 Offset(0, 45) A_Recoil(-3)
- `src/actors/classes/bosses/Balrog_W.dec:116` — 8H59 A 1 Offset(0, 46) A_Recoil(-2)                  // 2
- `src/actors/classes/bosses/Balrog_W.dec:127` — 8H59 A 1 Offset(0, 48) A_Recoil(-2)                  // 2
- `src/actors/classes/bosses/Balrog_W.dec:138` — 8H59 A 1 Offset(0, 50) A_Recoil(-2)                  // 2
- `src/actors/classes/bosses/Balrog_W.dec:149` — 8H59 A 1 Offset(0, 48) A_Recoil(-2)                  // 2
- `src/actors/classes/bosses/Balrog_W.dec:169` — 8H59 A 1 Offset(0, 47) A_Recoil(-2)
- `src/actors/classes/bosses/Balrog_W.dec:177` — 8H59 A 1 Offset(0, 49) A_Recoil(-2)
- `src/actors/classes/bosses/Balrog_W.dec:185` — 8H59 A 1 Offset(0, 49) A_Recoil(-2)
- `src/actors/classes/bosses/Balrog_W.dec:193` — 8H59 A 1 Offset(0, 47) A_Recoil(-2)
- `src/actors/classes/bosses/Balrog_W.dec:290` — 8H59 E 1 A_Recoil(5)
- `src/actors/classes/bosses/Balrog_W.dec:585` — 8P59 AAAAAAA 1 A_Recoil(3)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:231` — 9I13 F 0 A_Recoil(-60)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:293` — 9I13 G 0 A_Recoil(-10)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:301` — 9I13 G 0 A_Recoil(-25)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:429` — 9I13 L 1 A_Recoil(25)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:476` — TNT1 A 5 A_Recoil(25)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:651` — TNT1 A 0 A_Recoil(20)
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:974` — TNT1 A 0 A_Recoil(-6)  // 15
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:977` — TNT1 A 0 A_Recoil(-4.5)  // -7.5
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:988` — TNT1 A 0 A_Recoil(-2)  // 15
- `src/actors/classes/bosses/ScrotoStuntDouble_W.dec:991` — TNT1 A 0 A_Recoil(-1.5)  // -7.5
- `src/actors/classes/bosses/BlueThwomp_W.dec:34` — TNT1 A 0 A_Recoil(-2)
- `src/actors/classes/bosses/Skullman4MI_W.dec:212` — TNT1 A 0 A_Recoil(-6.25)  // -25
- `src/actors/classes/bosses/Skullman4MI_W.dec:215` — TNT1 A 0 A_Recoil(-12.5)  // -50
- `src/actors/classes/bosses/Skullman4MI_W.dec:219` — TNT1 A 0 A_Recoil(-3)
- `src/actors/classes/bosses/Skullman4MI_W.dec:222` — TNT1 A 0 A_Recoil(-6)
- `src/actors/classes/bosses/FinalSampi_W.dec:152` — 8L02 A 0 A_Recoil(-35)  // -105
- `src/actors/classes/bosses/FinalSampi_W.dec:156` — 8L02 B 0 A_Recoil(-3)
- `src/actors/classes/bosses/FinalSampi_W.dec:170` — HEBO C 3 A_Recoil(10)
- `src/actors/classes/bosses/FinalSampi_W.dec:308` — 8L02 B 2 A_Recoil(-45)
- `src/actors/classes/bosses/FinalSampi_W.dec:361` — X_BA H 2 A_Recoil(4)
- `src/actors/classes/bosses/FinalSampi_W.dec:598` — TNT1 A 1 A_Recoil(3)
- `src/actors/classes/bosses/FinalSampi_W.dec:599` — TMFX ABABAB 1 A_Recoil(3)

### classes/survivors (124)

- `src/actors/classes/survivors/LuckyLass_W.dec:1128` — TNT1 A 0 A_Recoil(2)
- `src/actors/classes/survivors/KickChamp_W.dec:160` — 6H58 NNNNNNN 2 A_Recoil(-2)
- `src/actors/classes/survivors/KickChamp_W.dec:162` — 6H58 NNNN 2 A_Recoil(-2)
- `src/actors/classes/survivors/KickChamp_W.dec:171` — 6H58 N 0 A_Recoil(-20)
- `src/actors/classes/survivors/KickChamp_W.dec:178` — 6H58 N 0 A_Recoil(-20)
- `src/actors/classes/survivors/KickChamp_W.dec:360` — TNT1 A 0 A_Recoil(-35)
- `src/actors/classes/survivors/qwant_copyweps/FeintAttack.dec:38` — FTAT C 0 A_Recoil(-120)
- `src/actors/classes/survivors/qwant_copyweps/FeintAttack.dec:46` — TNT1 A 0 A_Recoil(120)
- `src/actors/classes/survivors/qwant_copyweps/RapidSpin.dec:100` — TNT1 A 0 A_Recoil(-15)  // ?
- `src/actors/classes/survivors/qwant_copyweps/RapidSpin.dec:139` — TNT1 A 0 A_Recoil(-25)
- `src/actors/classes/survivors/qwant_copyweps/LeafBlade.dec:46` — 6H1E G 0 A_Recoil(-5)
- `src/actors/classes/survivors/qwant_copyweps/LeafBlade.dec:62` — TNT1 A 0 A_Recoil(-5)
- `src/actors/classes/survivors/qwant_copyweps/LeafBlade.dec:78` — TNT1 A 0 A_Recoil(-5)
- `src/actors/classes/survivors/qwant_copyweps/LeafBlade.dec:105` — TNT1 A 0 A_Recoil(-30)
- `src/actors/classes/survivors/FlightUnit_W.dec:287` — X_4G AAAAAAA 1 A_Recoil(3)
- `src/actors/classes/survivors/KickChampShiny_W.dec:157` — 7H58 NNNNNNN 2 A_Recoil(-2)
- `src/actors/classes/survivors/KickChampShiny_W.dec:159` — 7H58 NNNN 2 A_Recoil(-2)
- `src/actors/classes/survivors/KickChampShiny_W.dec:168` — 7H58 N 0 A_Recoil(-20)
- `src/actors/classes/survivors/KickChampShiny_W.dec:175` — 7H58 N 0 A_Recoil(-20)
- `src/actors/classes/survivors/qwant_shiny_moves.dec:86` — TNT1 A 0 A_Recoil(-120)
- `src/actors/classes/survivors/qwant_shiny_moves.dec:93` — TNT1 A 0 A_Recoil(120)
- `src/actors/classes/survivors/SumoWrestlerShiny_W.dec:246` — 7H36 F 0 A_Recoil(random(-4, -12))
- `src/actors/classes/survivors/PartyBomberShiny_W.dec:54` — 7H39 BCDEFG 2 A_Recoil(-3)
- `src/actors/classes/survivors/SumoWrestler_W.dec:250` — 6H36 F 0 A_Recoil(random(-4, -12))
- `src/actors/classes/survivors/DecoyBot_W.dec:719` — 1H50 F 3 A_Recoil(5)
- `src/actors/classes/survivors/DecoyBot_W.dec:1030` — TNT1 A 0 A_Recoil(-2)
- `src/actors/classes/survivors/DecoyBot_W.dec:1564` — TNT1 A 0 A_Recoil(-28 - (CallACS("core_CheckFooting")) * 22)
- `src/actors/classes/survivors/DecoyBot_W.dec:1734` — TNT1 A 0 A_Recoil(-20)
- `src/actors/classes/survivors/eden/alt_items/C036_ThePoop.dec:7` — TNT1 A 0 A_Recoil(-10)
- `src/actors/classes/survivors/GhostBuster.dec:56` — 1H57 H 1 A_Recoil(15)
- `src/actors/classes/survivors/BusterExpert_W.dec:67` — 6H03 B 0 A_Recoil(8)
- `src/actors/classes/survivors/BusterExpert_W.dec:71` — 6H03 B 0 A_Recoil(8)
- `src/actors/classes/survivors/BusterExpert_W.dec:75` — 6H03 B 0 A_Recoil(8)
- `src/actors/classes/survivors/WispShiny_W.dec:126` — 7H55 A 0 A_Recoil(random(-10, -20))
- `src/actors/classes/survivors/JuggernautShiny_W.dec:68` — TNT1 A 1 A_Recoil(-5)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:69` — TNT1 A 1 A_Recoil(-7)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:70` — TNT1 A 1 A_Recoil(-10)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:71` — TNT1 A 1 A_Recoil(-12)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:72` — TNT1 A 1 A_Recoil(-17)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:73` — TNT1 A 1 A_Recoil(-24)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:74` — TNT1 A 1 A_Recoil(-33)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:75` — TNT1 A 1 A_Recoil(-44)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:76` — TNT1 A 1 A_Recoil(-57)
- `src/actors/classes/survivors/JuggernautShiny_W.dec:77` — TNT1 A 1 A_Recoil(-73)
- `src/actors/classes/survivors/TristanaShiny_W.dec:158` — 7H38 B 0 A_Recoil(-0.5f)
- `src/actors/classes/survivors/Zangief_W.dec:398` — TNT1 A 0 A_Recoil(-2.4)  // -2
- `src/actors/classes/survivors/Zangief_W.dec:404` — TNT1 A 0 A_Recoil(-3.0)
- `src/actors/classes/survivors/Zangief_W.dec:661` — TNT1 A 0 A_Recoil(-4)
- `src/actors/classes/survivors/Zangief_W.dec:723` — TNT1 A 0 A_Recoil(10)
- `src/actors/classes/survivors/GreenElf_W.dec:71` — 6H47 E 0 A_Recoil(random(-9, 9))
- `src/actors/classes/survivors/BlueValkyrieShiny_W.dec:141` — 7H45 O 0 A_Recoil(random(-3, 3) * 11)
- `src/actors/classes/survivors/MiuShiny_W.dec:179` — 7H56 C 0 A_Recoil(-15)
- `src/actors/classes/survivors/MiuShiny_W.dec:202` — 7H56 C 0 A_Recoil(-2.5)
- `src/actors/classes/survivors/MiuShiny_W.dec:210` — 7H56 G 0 A_Recoil(-2.5)
- `src/actors/classes/survivors/HomingSeeker_W.dec:322` — TNT1 A 0 A_Recoil(-25)
- `src/actors/classes/survivors/HomingSeeker_W.dec:325` — TNT1 A 0 A_Recoil(25)
- `src/actors/classes/survivors/HandyMan_W.dec:222` — TNT1 A 0 A_Recoil(-4)
- `src/actors/classes/survivors/HandyMan_W.dec:243` — TNT1 A 0 A_Recoil(-2)
- `src/actors/classes/survivors/CloseCombatUnit_W.dec:119` — TNT1 A 0 A_Recoil(-2.75 - (CallACS("core_CheckFooting")) * 3.75)  // -6.5
- `src/actors/classes/survivors/megaman_copyweps/mmb/icewall.dec:82` — ICWL F 0 A_Recoil(-3)
- `src/actors/classes/survivors/megaman_copyweps/mmb/icewall.dec:85` — ICWL F 0 A_Recoil(-3)
- `src/actors/classes/survivors/megaman_copyweps/mmb/icewall.dec:88` — ICWL F 0 A_Recoil(-3)
- `src/actors/classes/survivors/megaman_copyweps/mmb/icewall.dec:91` — ICWL F 0 A_Recoil(-2)
- `src/actors/classes/survivors/megaman_copyweps/mmb/icewall.dec:94` — ICWL F 0 A_Recoil(-2)
- `src/actors/classes/survivors/HomingSeekerShiny_W.dec:240` — TNT1 A 0 A_Recoil(-37.5)
- `src/actors/classes/survivors/HomingSeekerShiny_W.dec:243` — TNT1 A 0 A_Recoil(37.5)
- `src/actors/classes/survivors/Raider_W.dec:283` — TNT1 AA 0 A_Recoil(-25)
- `src/actors/classes/survivors/Raider_W.dec:286` — TNT1 AA 0 A_Recoil(25)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:107` — 7H49 A 4 A_Recoil(-40)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:278` — 7H49 I 4 A_Recoil(-40)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:496` — TNT1 A 0 A_Recoil(-30)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:498` — TNT1 A 0 A_Recoil(-45)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:514` — TNT1 A 0 A_Recoil(-40)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:534` — TNT1 A 0 A_Recoil(40)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:543` — TNT1 A 0 A_Recoil(-70)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:760` — 7P49 M 0 A_Recoil(-1)  // 2
- `src/actors/classes/survivors/ArchivistShiny_W.dec:763` — 7P49 N 0 A_Recoil(-1)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:766` — 7P49 O 0 A_Recoil(-1)
- `src/actors/classes/survivors/ArchivistShiny_W.dec:769` — 7P49 P 0 A_Recoil(-1)
- `src/actors/classes/survivors/TacticalBomber_W.dec:592` — X_8G Y 0 A_Recoil(frandom(0, -5))
- `src/actors/classes/survivors/Tristana_W.dec:159` — 6H38 B 0 A_Recoil(-0.5f)
- `src/actors/classes/survivors/HeavyGunner_W.dec:74` — 6H16 A 0 A_Recoil(-20)
- `src/actors/classes/survivors/HeavyGunner_W.dec:220` — TNT1 A 0 A_Recoil(-20)
- `src/actors/classes/survivors/KateShiny_W.dec:136` — 7H53 M 1 A_Recoil(-2)
- `src/actors/classes/survivors/SamuraiSam_W.dec:116` — 6H33 A 0 A_Recoil(-50)
- `src/actors/classes/survivors/Kate_W.dec:137` — 6H53 M 1 A_Recoil(-2)
- `src/actors/classes/survivors/Miu_W.dec:155` — 6H56 C 0 A_Recoil(-15)
- `src/actors/classes/survivors/Miu_W.dec:178` — 6H56 C 0 A_Recoil(-2.5)
- `src/actors/classes/survivors/Miu_W.dec:186` — 6H56 G 0 A_Recoil(-2.5)
- `src/actors/classes/survivors/Miu_W.dec:449` — TNT1 A 0 A_Recoil(-18)  // -10
- `src/actors/classes/survivors/Miu_W.dec:451` — TNT1 A 0 A_Recoil(-28)
- `src/actors/classes/survivors/PartyBomber_W.dec:54` — 6H39 BCDEFG 2 A_Recoil(-3)
- `src/actors/classes/survivors/Wisp_W.dec:123` — 6H55 A 0 A_Recoil(random(-10, -20))
- `src/actors/classes/survivors/DecoyBotShiny_W.dec:1810` — 1H50 F 3 A_Recoil(5)
- `src/actors/classes/survivors/DecoyBotShiny_W.dec:2547` — TNT1 A 0 A_Recoil(-28 - (z - floorz == 0) * 22)
- `src/actors/classes/survivors/DecoyBotShiny_W.dec:2717` — TNT1 A 0 A_Recoil(-20)
- `src/actors/classes/survivors/Juggernaut_W.dec:69` — TNT1 A 1 A_Recoil(-5)
- `src/actors/classes/survivors/Juggernaut_W.dec:70` — TNT1 A 1 A_Recoil(-7)
- `src/actors/classes/survivors/Juggernaut_W.dec:71` — TNT1 A 1 A_Recoil(-10)
- `src/actors/classes/survivors/Juggernaut_W.dec:72` — TNT1 A 1 A_Recoil(-12)
- `src/actors/classes/survivors/Juggernaut_W.dec:73` — TNT1 A 1 A_Recoil(-17)
- `src/actors/classes/survivors/Juggernaut_W.dec:74` — TNT1 A 1 A_Recoil(-24)  // 28
- `src/actors/classes/survivors/Juggernaut_W.dec:75` — TNT1 A 1 A_Recoil(-33)  // 40
- `src/actors/classes/survivors/Juggernaut_W.dec:76` — TNT1 A 1 A_Recoil(-44)  // 62
- `src/actors/classes/survivors/Juggernaut_W.dec:77` — TNT1 A 1 A_Recoil(-57)  // 85
- `src/actors/classes/survivors/Juggernaut_W.dec:78` — TNT1 A 1 A_Recoil(-73)  // 100
- `src/actors/classes/survivors/HeavyBomber_W.dec:312` — X_4G AAAAAAA 1 A_Recoil(3)
- `src/actors/classes/survivors/HeavyBomber_W.dec:340` — X_4G A 0 A_Recoil(-5)
- `src/actors/classes/survivors/Saboteur_W.dec:179` — FLSM F 3 A_Recoil(5)
- `src/actors/classes/survivors/BusterExpertShiny_W.dec:67` — 7H03 B 0 A_Recoil(8)
- `src/actors/classes/survivors/BusterExpertShiny_W.dec:71` — 7H03 B 0 A_Recoil(8)
- `src/actors/classes/survivors/BusterExpertShiny_W.dec:75` — 7H03 B 0 A_Recoil(8)
- `src/actors/classes/survivors/megaman_copyweps/mm1/oilslider.dec:237` — TNT1 A 0 A_Recoil(-1.4375)
- `src/actors/classes/survivors/megaman_copyweps/mm1/oilslider.dec:240` — TNT1 A 0 A_Recoil(-2.875)
- `src/actors/classes/survivors/SamuraiSamShiny_W.dec:103` — 7H33 A 0 A_Recoil(-50)
- `src/actors/classes/survivors/BlueValkyrie_W.dec:107` — 6H45 O 0 A_Recoil(random(-3, 3) * 11)
- `src/actors/classes/survivors/BlueValkyrie_W.dec:270` — 6H45 A 0 A_Recoil(random(-3, 3) * 11)
- `src/actors/classes/survivors/HeavyGunnerShiny_W.dec:74` — 7H16 A 0 A_Recoil(-20)
- `src/actors/classes/survivors/GreenElfShiny_W.dec:111` — 7H47 E 0 A_Recoil(random(-9, 9))
- `src/actors/classes/survivors/HeavyBomberShiny_W.dec:204` — X_4G AAAAAAA 1 A_Recoil(3)
- `src/actors/classes/survivors/NegaMan_W.dec:200` — TNT1 A 0 A_Recoil(-50)
- `src/actors/classes/survivors/NegaMan_W.dec:203` — TNT1 A 0 A_Recoil(-28)
- `src/actors/classes/survivors/NegaMan_W.dec:332` — TNT1 A 0 A_Recoil(-70)
- `src/actors/classes/survivors/NegaMan_W.dec:335` — TNT1 A 0 A_Recoil(-42)

### coopenemies (43)

- `src/actors/coopenemies/enemies/Hothead.dec:66` — HOTH C 0 A_Recoil(-15)
- `src/actors/coopenemies/enemies/Flea.dec:21` — FLEA B 0 A_Recoil(-23)
- `src/actors/coopenemies/enemies/Flea.dec:55` — FLEA B 0 A_Recoil(-23)
- `src/actors/coopenemies/enemies/Flea.dec:59` — FLEA B 0 A_Recoil(-30)
- `src/actors/coopenemies/enemies/Flea.dec:63` — FLEA B 0 A_Recoil(-7)
- `src/actors/coopenemies/enemies/BigEye.dec:34` — BIGE A 0 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:37` — BIGE A 1 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:46` — BIGE A 0 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:49` — BIGE A 1 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:110` — BIGE A 0 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:113` — BIGE A 1 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:123` — BIGE A 0 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:126` — BIGE A 1 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:165` — BIGE A 0 A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:168` — BIGE A 1 A_Recoil(-3)
- `src/actors/coopenemies/enemies/PropTop.dec:27` — PRPT D 4 A_Recoil(random(-24, -16))
- `src/actors/coopenemies/enemies/PropTop.dec:88` — PRPT A 0 A_Recoil(random(-14, -8))
- `src/actors/coopenemies/enemies/SniperJoe.dec:211` — SNAR C 0 A_Recoil(-15)
- `src/actors/coopenemies/enemies/SniperJoe.dec:533` — SNAR C 0 A_Recoil(-15)
- `src/actors/coopenemies/bosses/CutMan.dec:57` — CUTM R 0 A_Recoil(-10)
- `src/actors/coopenemies/bosses/CutMan.dec:62` — CUTM R 0 A_Recoil(-10)
- `src/actors/coopenemies/bosses/CutMan.dec:80` — CUTM H 5 A_Recoil(5)
- `src/actors/coopenemies/bosses/CutMan.dec:208` — CUTM R 0 A_Recoil(-6)
- `src/actors/coopenemies/bosses/CutMan.dec:213` — CUTM R 0 A_Recoil(-6)
- `src/actors/coopenemies/bosses/HeatMan.dec:70` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:76` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:79` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:82` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:85` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:88` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:91` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:94` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:97` — TNT1 A 1 A_Recoil(-45)
- `src/actors/coopenemies/bosses/HeatMan.dec:111` — TNT1 A 1 A_Recoil(-35)
- `src/actors/coopenemies/bosses/HeatMan.dec:362` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:368` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:371` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:374` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:377` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:380` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:383` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:386` — TNT1 A 1 A_Recoil(-50)
- `src/actors/coopenemies/bosses/HeatMan.dec:389` — TNT1 A 1 A_Recoil(-50)

### classes/eyes (16)

- `src/actors/classes/eyes/Sumo_W.dec:23` — _E04 E 0 A_Recoil(-30)
- `src/actors/classes/eyes/Joust_W.dec:22` — _E03 B 1 A_Recoil(-5)
- `src/actors/classes/eyes/Joust_W.dec:24` — _E03 B 1 A_Recoil(-7)
- `src/actors/classes/eyes/Joust_W.dec:26` — _E03 B 1 A_Recoil(-10)
- `src/actors/classes/eyes/Joust_W.dec:28` — _E03 B 1 A_Recoil(-14)  // -12
- `src/actors/classes/eyes/Joust_W.dec:30` — _E03 B 1 A_Recoil(-19)  // -17
- `src/actors/classes/eyes/Joust_W.dec:32` — _E03 B 1 A_Recoil(-25)  // -28
- `src/actors/classes/eyes/Joust_W.dec:34` — _E03 B 1 A_Recoil(-32)  // -40
- `src/actors/classes/eyes/Joust_W.dec:36` — _E03 B 1 A_Recoil(-40)  // -62
- `src/actors/classes/eyes/Joust_W.dec:38` — _E03 B 1 A_Recoil(-49)  // -85
- `src/actors/classes/eyes/Joust_W.dec:40` — _E03 B 1 A_Recoil(-59)  // -100
- `src/actors/classes/eyes/Joust_W.dec:46` — _E03 B 1 A_Recoil(-10)
- `src/actors/classes/eyes/Joust_W.dec:48` — _E03 B 1 A_Recoil(-15)
- `src/actors/classes/eyes/Joust_W.dec:50` — _E03 B 1 A_Recoil(-25)
- `src/actors/classes/eyes/Joust_W.dec:52` — _E03 B 1 A_Recoil(-40)
- `src/actors/classes/eyes/Joust_W.dec:54` — _E03 B 1 A_Recoil(-60)

### items (9)

- `src/actors/items/other/TrueBusterMistressItems.dec:449` — X_0E I 0 A_Recoil(5)
- `src/actors/items/pandora/ColdSummon.dec:995` — X_BD X 0 A_Recoil(-5)
- `src/actors/items/pandora/ColdSummon.dec:997` — X_BD X 0 A_Recoil(-4)
- `src/actors/items/pandora/ColdSummon.dec:999` — X_BD X 0 A_Recoil(-3.5)
- `src/actors/items/pandora/ColdSummon.dec:1001` — X_BD X 0 A_Recoil(-3)
- `src/actors/items/pandora/ColdSummon.dec:1003` — X_BD X 0 A_Recoil(-2.5)
- `src/actors/items/tow/UnholyInsurance.dec:163` — TNT1 A 0 A_Recoil(-2.25)
- `src/actors/items/tow/UnholyInsurance.dec:190` — I_TH A 0 A_Recoil(-2)
- `src/actors/items/tow/GauntletExit.dec:94` — I_TP K 1 A_Recoil(-0.0001)

### unepic (core replace / FX) (6)

- `src/actors/unepic/CorePropReplace.dec:497` — GUTG A 0 A_Recoil(-5)
- `src/actors/unepic/CorePropReplace.dec:500` — GUTG A 0 A_Recoil(-5)
- `src/actors/unepic/CorePropReplace.dec:503` — GUTG A 0 A_Recoil(-5)
- `src/actors/unepic/CorePropReplace.dec:506` — GUTG A 0 A_Recoil(-5)
- `src/actors/unepic/CorePropReplace.dec:509` — GUTG A 0 A_Recoil(-5)
- `src/actors/unepic/CorePropReplace.dec:512` — GUTG A 0 A_Recoil(-5)

### player (core pain / classbase) (2)

- `src/actors/player/uh-BasePain.dec:146` — TNT1 A 0 A_Recoil(1)
- `src/actors/player/classbase/root/ClassBase_UH40_DeathEffects.dec:149` — "----" H 0 A_Recoil(45)

## Commented-out occurrences

- `src/actors/unepic/GeneralThings_U.dec:199` — // TNT1 A 0 A_Recoil(-1)
- `src/actors/classes/survivors/LuckyLass_W.dec:1036` — 6P06 BCD 2 A_ScaleVelocity(2.0)  // 1.05 loop//A_Recoil(-4)
- `src/actors/classes/survivors/KickChamp_W.dec:430` — // TNT1 A 0 A_Recoil(70)
- `src/actors/classes/survivors/KickChamp_W.dec:436` — // TNT1 A 0 A_Recoil(25)
- `src/actors/classes/survivors/HandyMan_W.dec:523` — X_0E "#" 0  // A_Recoil(2.5)
- `src/actors/classes/survivors/Amber_W.dec:325` — // TNT1 A 0 A_Recoil(-22)
- `src/actors/classes/survivors/Amber_W.dec:330` — // TNT1 A 0 A_Recoil(-28)
- `src/actors/classes/survivors/HeavyGunner_W.dec:188` — // TNT1 A 0 A_Recoil(2*cos(pitch))
- `src/actors/classes/survivors/HeavyGunner_W.dec:204` — // TNT1 A 0 A_Recoil(2*cos(pitch))
- `src/actors/classes/bosses/GutsBuddy_W.dec:120` — // TNT1 A 0 A_Recoil(-35)//Unsure.
- `src/actors/classes/bosses/ColonelKachidonga_W.dec:38` — 8H04 C 0 A_ChangeVelocity(-cos(pitch) * 22, 0, sin(pitch) * 13, CVF_RELATIVE)  // A_Recoil(20)
- `src/actors/classes/bosses/ColonelKachidonga_W.dec:52` — 8H04 C 0 A_ChangeVelocity(-cos(pitch) * 30, 0, sin(pitch) * 17, CVF_RELATIVE)  // A_Recoil(35)
- `src/actors/classes/bosses/ColonelKachidonga_W.dec:63` — 8H04 C 0 A_ChangeVelocity(-cos(pitch) * 54, 0, sin(pitch) * 40, CVF_RELATIVE)  // A_Recoil(50)
- `src/actors/classes/bosses/ColonelKachidonga_W.dec:76` — 8H04 C 0 A_ChangeVelocity(-cos(pitch) * 65, 0, sin(pitch) * 50, CVF_RELATIVE)  // A_Recoil(75)
- `src/actors/classes/bosses/ColonelKachidonga_W.dec:89` — 8H04 C 0 A_ChangeVelocity(-cos(pitch) * 30, 0, sin(pitch) * 17, CVF_RELATIVE)  // A_Recoil(35)
- `src/actors/classes/bosses/ColonelKachidonga_W.dec:104` — 8H04 C 0 A_ChangeVelocity(-cos(pitch) * 54, 0, sin(pitch) * 42, CVF_RELATIVE)  // A_Recoil(50)
- `src/actors/classes/bosses/AstromancerSimple_W.dec:76` — // 8H30 A 0 A_Recoil(-60)
- `src/actors/classes/bosses/SirAlpha_W.dec:159` — 8I03 D 0  // A_Recoil(-5)
- `src/actors/classes/bosses/SirAlpha_W.dec:167` — 8I03 E 0  // A_Recoil(-1)
- `src/actors/classes/bosses/SirAlpha_W.dec:186` — 8I03 E 0  // A_Recoil(-5)
- `src/actors/classes/bosses/SirAlpha_W.dec:197` — 8I03 E 0  // A_Recoil(-5)
- `src/actors/classes/bosses/ElitistSue_W.dec:97` — // 8H03 C 0 A_Recoil(50)
- `src/actors/classes/bosses/Troutius_W.dec:359` — 8H49 J 0  // A_Recoil(-5)
- `src/actors/classes/bosses/Troutius_W.dec:365` — 8H49 J 0  // A_Recoil(-1)
- `src/actors/classes/bosses/Troutius_W.dec:377` — 8H49 J 0  // A_Recoil(-5)
- `src/actors/classes/bosses/Troutius_W.dec:384` — 8H49 J 0  // A_Recoil(-5)
- `src/actors/classes/bosses/Troutius_W.dec:395` — 8H49 J 0  // A_Recoil(-5)
- `src/actors/classes/bosses/TheCommandoChamp_W.dec:667` — CMDH G 0  // A_Recoil(-1)
- `src/actors/coopenemies/enemies/BigEye.dec:152` — BIGE A 0 A_Stop  // A_Recoil(-3)
- `src/actors/coopenemies/enemies/BigEye.dec:155` — BIGE A 1  // A_Recoil(-3)
- `src/actors/classes/bosses/BlueElephant_W.dec:50` — TNT1 A 0  // A_Recoil(-2)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:100` — //8L01 A 0 A_Recoil(-10)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:272` — TNT1 A 0 A_ScaleVelocity(0.40)  // A_Recoil(-15)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:630` — TNT1 A 0 A_ScaleVelocity(0.60)  // A_Recoil(-10)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:634` — TNT1 A 0 A_ScaleVelocity(0.60)  // A_Recoil(-15)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:717` — TNT1 A 0  // A_Recoil(7)
- `src/actors/classes/bosses/EyelentoMajor_W.dec:895` — // TNT1 A 0 A_Recoil(-45)
- `src/actors/classes/bosses/FinalSampi_W.dec:912` — TNT1 A 0 ThrustThing(angle * 256 / 360 + 128, 40, 1, 0)  // TNT1 A 0 A_Recoil(25)
