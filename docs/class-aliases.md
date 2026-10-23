# 机体别名表 / Class aliases

这份表只保留 Razon4 中存在的机体称呼，连接日常内部叫法、游戏名称和代码实体，是 Agent 解析需求的权威映射字典。新增、调整或纠正映射时直接在此表更新。

项目需求、Bug 与企划案追踪均位于腾讯文档智能表格：[Unholy Razon 企划与任务看板](https://docs.qq.com/smartsheet/DY0VLQkZxeG5RSm9C) (`cEKBFqxnQJoB`)。

## 使用规则 / Usage rules

1. **查表映射 / Lookup & Mapping**：收到机体相关任务时，优先在此表按字符串精确匹配内部绰号，映射为目标 Actor。支持中文日常绰号及常用英文缩写（如 `be` / `BE` ➔ `BusterExpert`）。
2. **Shiny 命名规则 / Shiny Naming Convention**：普通生还者的绰号**默认不映射**其 Shiny 版本。若明确指代生还者的 Shiny 版本，社区习惯使用“**<机体名>的shitpower版**”或“**<机体名>的truepower版**”（例如“飞弹荡妇的shitpower版” ➔ `BusterMistressShiny`）。
3. **范围与消歧 / Scopes & Disambiguation**：区分 `survivor`（普通生还者）、`shiny`（变体）、`boss`（Boss）、`demoneye`（恶魔眼）和 `item`（道具）。遇到重名或集合称呼时，查阅下方的【必须消歧的重名】与【类别通用绰号】，结合任务上下文消歧；仍有疑义时询问用户。
4. **有误直接更新 / Direct Updates**：本表为工程速查字典。若发现称呼有误、叫法改变或有新增别名，直接修改本表。
5. **代码检索 / Code Lookup Key**：Actor 标识符是唯一的代码检索键；数字 ID 仅供当前参考，实施前在源码中核对。

### English Guidelines

- **Canonical Task Tracker**: Project backlog, bug reports, and community proposals are tracked in the Tencent Docs SmartSheet at https://docs.qq.com/smartsheet/DY0VLQkZxeG5RSm9C (`file_id`: `cEKBFqxnQJoB`).
- **Primary dictionary**: Use this table as the authoritative mapping dictionary to resolve internal nicknames and community slang to canonical Razon4 Actors.
- **Verbatim matching**: The `Alias` column contains nicknames verbatim (primarily Chinese, plus common English acronyms like `be`/`BE`). Match incoming task terms directly against this column without inventing translated names.
- **Shiny convention**: Survivor nicknames do not map to Shiny variants by default. In community usage, Shiny variants are explicitly called `<nickname>的shitpower版` or `<nickname>的truepower版` (e.g. `飞弹荡妇的shitpower版` ➔ `BusterMistressShiny`).
- **Scope resolution**: Explicitly resolve whether the task targets a `survivor`, `shiny`, `boss`, `demoneye`, or `item`. Check the collision and collective alias sections below before implementing changes. Ask the user if ambiguity persists.
- **Maintenance**: Update this file directly whenever aliases are corrected, newly confirmed, or changed.

## 机体绰号映射 / Class alias mappings

当前显示名取自 Razon4 定义表的名称字段（去除颜色控制码），供阅读和检索；Actor 是源码实体标识，用于定位代码。

注册来源 / Registration sources：[survivor](../src/acs_source/classes/survivors/definitions/uh_survdefs.acs)、[boss](../src/acs_source/classes/bosses/boss_definition_table.acs)、[demoneye](../src/acs_source/classes/demoneyes/definitions/uh_eyedefs.acs)。ID 仅供当前检索参考；实施前仍须核对包含链和实际加载。

| 绰号 / Alias | 当前显示名 / Current display name | Actor | 范围 / Scope | 代码 / Source | 备注 / Notes |
|---|---|---|---|---|---|
| 岩男 | Mega Man | `MegaManU` | survivor | [Actor](../src/actors/classes/survivors/MegaMan.dec); ID 0 |  |
| 宝可梦大师 | Qwant | `Qwant` | survivor | [Actor](../src/actors/classes/survivors/Qwant.dec); ID 1 |  |
| Nega、内个、滑铲男 | Nega Man | `NegaMan` | survivor | [Actor](../src/actors/classes/survivors/NegaMan.dec); ID 2 |  |
| 飞弹专家、BE、be | Buster Expert | `BusterExpert` | survivor | [Actor](../src/actors/classes/survivors/BusterExpert.dec); ID 3 |  |
| 飞弹荡妇、飞弹情妇 | Buster Mistress | `BusterMistress` | survivor | [Actor](../src/actors/classes/survivors/BusterMistress.dec); ID 4 |  |
| 大盾哥、盾狗、山上彻也 | Great Shielder | `GreatShielder` | survivor | [Actor](../src/actors/classes/survivors/GreatShielder.dec); ID 5 |  |
| 抽奖福瑞、罗露 | Lucky Lass | `LuckyLass` | survivor | [Actor](../src/actors/classes/survivors/LuckyLass.dec); ID 6 |  |
| 快送人 | Quickster | `Quickster` | survivor | [Actor](../src/actors/classes/survivors/Quickster.dec); ID 7 |  |
| 榴弹 | Tactical Bomber | `TacticalBomber` | survivor | [Actor](../src/actors/classes/survivors/TacticalBomber.dec); ID 8 |  |
| 弗利萨 | Frost Bite | `FrostBite` | survivor | [Actor](../src/actors/classes/survivors/FrostBite.dec); ID 9 |  |
| 阿三 | Igniter | `Igniter` | survivor | [Actor](../src/actors/classes/survivors/Igniter.dec); ID 10 |  |
| 黑骑士、盾刀 | Close Combat Unit | `CloseCombatUnit` | survivor | [Actor](../src/actors/classes/survivors/CloseCombatUnit.dec); ID 11 |  |
| 溜冰男 | Arcanist | `Arcanist` | survivor | [Actor](../src/actors/classes/survivors/Arcanist.dec); ID 12 |  |
| 磁铁 | Homing Seeker | `HomingSeeker` | survivor | [Actor](../src/actors/classes/survivors/HomingSeeker.dec); ID 13 |  |
| 隐身B、滚木人 | Trickster | `Trickster` | survivor | [Actor](../src/actors/classes/survivors/Trickster.dec); ID 14 |  |
| 红温人 | Rage Unit | `RageUnit` | survivor | [Actor](../src/actors/classes/survivors/RageUnit.dec); ID 15 |  |
| 小坦克 | Heavy Gunner | `HeavyGunner` | survivor | [Actor](../src/actors/classes/survivors/HeavyGunner.dec); ID 16 |  |
| 棍哥、毒棍 | Raider | `Raider` | survivor | [Actor](../src/actors/classes/survivors/Raider.dec); ID 17 |  |
| 牢大、小牢大 | Flight Unit | `FlightUnit` | survivor | [Actor](../src/actors/classes/survivors/FlightUnit.dec); ID 18 |  |
| 牢大、大牢大 | Heavy Bomber | `HeavyBomber` | survivor | [Actor](../src/actors/classes/survivors/HeavyBomber.dec); ID 19 |  |
| 小帅哥 | Electrician | `Electrician` | survivor | [Actor](../src/actors/classes/survivors/Electrician.dec); ID 20 |  |
| 合金弹头 | Slugger | `Slugger` | survivor | [Actor](../src/actors/classes/survivors/Slugger.dec); ID 21 |  |
| 臭狙 | Stealth Sniper | `StealthSniper` | survivor | [Actor](../src/actors/classes/survivors/StealthSniper.dec); ID 23 |  |
| 哈基米、柔情猫娘 | Tango Girl | `TangoGirl` | survivor | [Actor](../src/actors/classes/survivors/TangoGirl.dec); ID 24 |  |
| 树哥 | Tree Hugger | `TreeHugger` | survivor | [Actor](../src/actors/classes/survivors/TreeHugger.dec); ID 26 |  |
| 丁真 | Smoke Bandit | `SmokeBandit` | survivor | [Actor](../src/actors/classes/survivors/SmokeBandit.dec); ID 28 |  |
| 茎输人 | The Dentist | `TheDentist` | survivor | [Actor](../src/actors/classes/survivors/TheDentist.dec); ID 29 |  |
| 蝙蝠 | Aero Unit | `AeroUnit` | survivor | [Actor](../src/actors/classes/survivors/AeroUnit.dec); ID 31 |  |
| 法老 | Rameses | `Rameses` | survivor | [Actor](../src/actors/classes/survivors/Rameses.dec); ID 32 |  |
| 水果忍者 | Samurai Sam | `SamuraiSam` | survivor | [Actor](../src/actors/classes/survivors/SamuraiSam.dec); ID 33 |  |
| 勇者、俄罗斯方块 | Site Worker | `SiteWorker` | survivor | [Actor](../src/actors/classes/survivors/SiteWorker.dec); ID 35 | Gutsman 皮肤，属于“勇者”类通用称呼 / Gutsman sprite, part of "勇者" category |
| 蛙哥 | Sumo Wrestler | `SumoWrestler` | survivor | [Actor](../src/actors/classes/survivors/SumoWrestler.dec); ID 36 | Toadman 皮肤，属于“蛙哥”类通用称呼 / Toadman sprite, part of "蛙哥" category |
| 海王 | Tidal Maniac | `TidalManiac` | survivor | [Actor](../src/actors/classes/survivors/TidalManiac.dec); ID 37 |  |
| 找B | Marksman | `Marksman` | survivor | [Actor](../src/actors/classes/survivors/Marksman.dec); ID 40 |  |
| Suckman | Lim | `Lim` | survivor | [Actor](../src/actors/classes/survivors/Lim.dec); ID 43 |  |
| 发育B、小红、呃唔 | Red Warrior | `RedWarrior` | survivor | [Actor](../src/actors/classes/survivors/RedWarrior.dec); ID 44 |  |
| 小蓝、蓝刀 | Blue Valkyrie | `BlueValkyrie` | survivor | [Actor](../src/actors/classes/survivors/BlueValkyrie.dec); ID 45 |  |
| 小黄、嗷呜 | Yellow Wizard | `YellowWizard` | survivor | [Actor](../src/actors/classes/survivors/YellowWizard.dec); ID 46 |  |
| 马、小绿、咿嗷 | Green Elf | `GreenElf` | survivor | [Actor](../src/actors/classes/survivors/GreenElf.dec); ID 47 |  |
| 大运、老爷爷 | Juggernaut | `Juggernaut` | survivor | [Actor](../src/actors/classes/survivors/Juggernaut.dec); ID 48 |  |
| 数值怪、龙哥专用机 | Decoy Bot | `DecoyBot` | survivor | [Actor](../src/actors/classes/survivors/DecoyBot.dec); ID 50 |  |
| 红福瑞、扫把福瑞 | Amber | `Amber` | survivor | [Actor](../src/actors/classes/survivors/Amber.dec); ID 52 |  |
| 蓝福瑞、浅蓝福瑞、背刺福瑞 | Kate | `Kate` | survivor | [Actor](../src/actors/classes/survivors/Kate.dec); ID 53 |  |
| 绿福瑞、数值怪 | Claire | `Claire` | survivor | [Actor](../src/actors/classes/survivors/Claire.dec); ID 54 |  |
| 深蓝福瑞、紫福瑞 | Wisp | `Wisp` | survivor | [Actor](../src/actors/classes/survivors/Wisp.dec); ID 55 |  |
| 黄福瑞、海盗福瑞 | Miu | `Miu` | survivor | [Actor](../src/actors/classes/survivors/Miu.dec); ID 56 |  |
| wow、踹哈 | Kick Champ | `KickChamp` | survivor | [Actor](../src/actors/classes/survivors/KickChamp.dec); ID 58 |  |
| 小孩、以撒 | Eden | `Eden` | survivor | [Actor](../src/actors/classes/survivors/Eden.dec); ID 59 |  |
| 真正的飞弹专家 | True BusterExpert | `TrueBusterExpert` | boss | [Actor](../src/actors/classes/bosses/TrueBusterExpert.dec); ID 0 |  |
| 狙、鹰眼 | Hunter Hawkeye | `HunterHawkeye` | boss | [Actor](../src/actors/classes/bosses/HunterHawkeye.dec); ID 1 |  |
| 蛇人 | Don Javier | `DonJavier` | boss | [Actor](../src/actors/classes/bosses/DonJavier.dec); ID 2 |  |
| 雪女、冰女 | Elitist Sue | `ElitistSue` | boss | [Actor](../src/actors/classes/bosses/ElitistSue.dec); ID 3 |  |
| 孙红雷 | Colonel Kachidonga | `ColonelKachidonga` | boss | [Actor](../src/actors/classes/bosses/ColonelKachidonga.dec); ID 4 |  |
| 小棍哥、侯国玉 | Kakusareta Sutoka | `KakusaretaSutoka` | boss | [Actor](../src/actors/classes/bosses/KakusaretaSutoka.dec); ID 5 |  |
| 美国队长 | Officer Johnson | `OfficerJohnson` | boss | [Actor](../src/actors/classes/bosses/OfficerJohnson.dec); ID 6 |  |
| 安柯 | Hurricane Waylon | `ElitistWaylon` | boss | [Actor](../src/actors/classes/bosses/ElitistWaylon.dec); ID 7 |  |
| 黑BOT、自动落坑机 | Shin Hellbot | `ShinHellbot` | boss | [Actor](../src/actors/classes/bosses/ShinHellBot.dec); ID 8 |  |
| 白小丑 | Trickster Giovanni | `TricksterGiovanni` | boss | [Actor](../src/actors/classes/bosses/TricksterGiovanni.dec); ID 10 |  |
| 绿坦克 | Iron Curtain | `IronCurtain` | boss | [Actor](../src/actors/classes/bosses/IronCurtain.dec); ID 11 |  |
| 茎输人 | Captain Blitzkrieg | `CaptainBlitzkrieg` | boss | [Actor](../src/actors/classes/bosses/CaptainBlitzkrieg.dec); ID 12 |  |
| 弔术士 | Dickster Dick | `DicksterDick` | boss | [Actor](../src/actors/classes/bosses/DicksterDick.dec); ID 13 |  |
| 弗利萨、苏联弗利萨 | Soviet Frostbite | `SovietFrostBite` | boss | [Actor](../src/actors/classes/bosses/SovietFrostBite.dec); ID 14 |  |
| 阿三、苏联阿三 | Soviet Igniter | `SovietIgniter` | boss | [Actor](../src/actors/classes/bosses/SovietIgniter.dec); ID 15 |  |
| 帅哥 | Repairman Edward | `RepairManEdward` | boss | [Actor](../src/actors/classes/bosses/RepairManEdward.dec); ID 16 |  |
| 黑大妈 | Arch Arcanist | `ArchArcanist` | boss | [Actor](../src/actors/classes/bosses/ArchArcanist.dec); ID 18 |  |
| bba | Meguh Mang | `MeguhMang` | boss | [Actor](../src/actors/classes/bosses/MeguhMang.dec); ID 19 |  |
| 万磁王 | Magnetismo | `Magnetismo` | boss | [Actor](../src/actors/classes/bosses/Magnetismo.dec); ID 20 |  |
| 彩虹糖 | Gem Banker | `GemBanker` | boss | [Actor](../src/actors/classes/bosses/GemBanker.dec); ID 22 |  |
| 圣骑士 | Dixieandoff | `Dixieandoff` | boss | [Actor](../src/actors/classes/bosses/Dixieandoff.dec); ID 23 |  |
| 绿勇者、农夫三拳 | THE GENERIC BOSS | `GENERICBOSS` | boss | [Actor](../src/actors/classes/bosses/GENERICBOSS.dec); ID 24 |  |
| 飞弹荡妇、飞弹情妇、真正的飞弹情妇 | True Buster Mistress | `TrueBusterMistress` | boss | [Actor](../src/actors/classes/bosses/TrueBusterMistress.dec); ID 25 |  |
| 宝可梦大师 | Cutty Cut | `CuttyCut` | boss | [Actor](../src/actors/classes/bosses/CuttyCut.dec); ID 26 |  |
| 金角大王 | Juggerbro Gold | `JuggerbroGold` | boss | [Actor](../src/actors/classes/bosses/JuggerbroGold.dec); ID 31 |  |
| 银角大王 | Juggerbro Silver | `JuggerbroSilver` | boss | [Actor](../src/actors/classes/bosses/JuggerbroSilver.dec); ID 32 |  |
| 红坦克、京东外卖 | Red TankBoi | `RedTankBot` | boss | [Actor](../src/actors/classes/bosses/RedTankBot.dec); ID 35 |  |
| 蓝坦克、龙车、饿了么 | Blue TankBoi | `BluTankBot` | boss | [Actor](../src/actors/classes/bosses/BluTankBot.dec); ID 36 |  |
| 黄坦克、美团外卖 | Yellow TankBoi | `YelTankBot` | boss | [Actor](../src/actors/classes/bosses/YelTankBot.dec); ID 37 |  |
| 红勇者 | Guts Buddy | `GutsBuddy` | boss | [Actor](../src/actors/classes/bosses/GutsBuddy.dec); ID 46 |  |
| 俄罗斯勇者 | Russian Gutsman | `RussianGuts` | boss | [Actor](../src/actors/classes/bosses/RussianGuts.dec); ID 47 |  |
| 僵尸勇者 | Redead Gutsman | `RedeadGuts` | boss | [Actor](../src/actors/classes/bosses/RedeadGuts.dec); ID 48 |  |
| 佛鲁迪、摩卡、What | Troutius | `Troutius` | boss | [Actor](../src/actors/classes/bosses/Troutius.dec); ID 49 |  |
| 硬金人、巡航导弹 | HalfPress Hardman | `HalfPressHardman` | boss | [Actor](../src/actors/classes/bosses/HalfPressHardman.dec); ID 50 |  |
| 流星洛克人、流星、流洛 | War Rock Stelar | `WarRockStelar` | boss | [Actor](../src/actors/classes/bosses/WarrockStelar.dec); ID 51 |  |
| 响美空、弹琴女、木柜子 | Harp Strumm | `HarpStrumm` | boss | [Actor](../src/actors/classes/bosses/HarpStrumm.dec); ID 52 |  |
| 海王 | Tidal Tito | `TidalTito` | boss | [Actor](../src/actors/classes/bosses/TidalTito.dec); ID 53 |  |
| 宇宙机器人 | Void Walker | `VoidWalker` | boss | [Actor](../src/actors/classes/bosses/VoidWalker.dec); ID 54 |  |
| 绿Joe | Joe | `JoeOfDuty` | boss | [Actor](../src/actors/classes/bosses/JoeOfDuty.dec); ID 58 |  |
| 电视机 | Balrog | `Balrog` | boss | [Actor](../src/actors/classes/bosses/Balrog.dec); ID 59 |  |
| 巫女 | Misery | `Misery` | boss | [Actor](../src/actors/classes/bosses/Misery.dec); ID 60 |  |
| spy、隐身女特务 | Agent TorCal | `TorontoCalifornia` | boss | [Actor](../src/actors/classes/bosses/TorontoCalifornia.dec); ID 62 |  |
| 绿南瓜 | Plasma Spark | `PlasmaSpark` | boss | [Actor](../src/actors/classes/bosses/PlasmaSpark.dec); ID 63 |  |
| 老头 | Meister Wahwee | `MeisterWahwee` | boss | [Actor](../src/actors/classes/bosses/MeisterWahwee.dec); ID 64 |  |
| 普通眼 | Demoneye | `ArenaDemoneye` | boss | [Actor](../src/actors/classes/bosses/ArenaDemoneye.dec); ID 65 |  |
| 洛克魔罗、SMM、超洛、炒螺 | Super Megaman | `SuperMegaman` | boss | [Actor](../src/actors/classes/bosses/SuperMegaman.dec); ID 66 |  |
| 几把lin | Lin | `Lin` | boss | [Actor](../src/actors/classes/bosses/Lin.dec); ID 67 |  |
| 啃几把、警巴肯 | KFCDragon756 | `KFCDragon756` | boss | [Actor](../src/actors/classes/bosses/KFCDragon756.dec); ID 69 |  |
| 红狗 | Berserker | `Berserker` | boss | [Actor](../src/actors/classes/bosses/Berserker.dec); ID 73 |  |
| 国足 | Soccer Rock | `SoccerRock` | boss | [Actor](../src/actors/classes/bosses/SoccerRock.dec); ID 74 |  |
| 几把人吸、色鸠人吸 | Timeman C | `TimemanC` | boss | [Actor](../src/actors/classes/bosses/TimemanC.dec); ID 91 |  |
| 红Bot | HellBot | `HellBot` | boss | [Actor](../src/actors/classes/bosses/Hellbot.dec); ID 100 |  |
| 空气男 | Air Man | `CXAirMan` | boss | [Actor](../src/actors/classes/bosses/CXAirman.dec); ID 101 |  |
| 无尽战神 | Sinful BusterExpert | `SinfulBusterExpert` | boss | [Actor](../src/actors/classes/bosses/SinfulBusterExpert.dec); ID 102 |  |
| 蛙哥 | Toadman | `SadFaceToadMan` | boss | [Actor](../src/actors/classes/bosses/SadFaceToadMan.dec); ID 104 | Toadman 皮肤，属于“蛙哥”类通用称呼 / Toadman sprite, part of "蛙哥" category |
| 金ASP | Super Speciman | `SuperSpeciman` | boss | [Actor](../src/actors/classes/bosses/SuperSpeciman.dec); ID 105 |  |
| 紫ASP | Ghost of Speciman | `GhostSpeciman` | boss | [Actor](../src/actors/classes/bosses/GhostSpeciman.dec); ID 106 |  |
| 肉鸽 | Rogue | `Rogue` | boss | [Actor](../src/actors/classes/bosses/Rogue.dec); ID 107 |  |
| 瓜摊老板 | Tropical MWS | `TropicalMWS` | boss | [Actor](../src/actors/classes/bosses/TropicalMWS.dec); ID 110 |  |
| 马 | DLC Centaurman | `DLCCentaurman` | boss | [Actor](../src/actors/classes/bosses/DLCCentaurman.dec); ID 111 |  |
| 美国妖精、美国小女孩 | Clownpiece | `Clownpiece` | boss | [Actor](../src/actors/classes/bosses/Clownpiece.dec); ID 112 |  |
| 红色几把石 | Granite Mauler | `GraniteMauler` | boss | [Actor](../src/actors/classes/bosses/GraniteMauler.dec); ID 114 |  |
| 法师眼 | Magic Specialist | `MagicDevilEye` | boss | [Actor](../src/actors/classes/bosses/MagicDevilEye.dec); ID 115 |  |
| 镇村神石、蓝色几把石 | Blue Thwomp | `BlueThwomp` | boss | [Actor](../src/actors/classes/bosses/BlueThwomp.dec); ID 116 |  |
| 西兰花boss、承太郎 | Joterra | `Joterra` | boss | [Actor](../src/actors/classes/bosses/Joterra.dec); ID 117 |  |
| 安倍晋三 | Abe Penny | `AbePenny` | boss | [Actor](../src/actors/classes/bosses/AbePenny.dec); ID 301 |  |
| 大资本家 | Devileye Richman | `RichDevilEye` | boss | [Actor](../src/actors/classes/bosses/RichDevilEye.dec); ID 302 |  |
| 纸片狗 | Cobe | `Cobe` | boss | [Actor](../src/actors/classes/bosses/Cobe.dec); ID 303 |  |
| 大棍哥 | Shadowman | `TheShadowManMythBoss` | boss | [Actor](../src/actors/classes/bosses/TheShadowManMythBoss.dec); ID 305 |  |
| 抹布人 | Zero | `MakeAGoodZero` | boss | [Actor](../src/actors/classes/bosses/MakeAGoodZero.dec); ID 306 |  |
| 蓝Bot | Zankokuna Hellbot | `ZankokunaHellbot` | boss | [Actor](../src/actors/classes/bosses/ZankokunaHellbot.dec); ID 400 |  |
| 棍眼 | Eyelento Major | `EyelentoMajor` | boss | [Actor](../src/actors/classes/bosses/EyelentoMajor.dec); ID 401 |  |
| 三批 | Sampi | `FinalSampi` | boss | [Actor](../src/actors/classes/bosses/FinalSampi.dec); ID 402 |  |
| 元首 | Higlur | `SPOOKYGHOSTHITLER` | boss | [Actor](../src/actors/classes/bosses/SPOOKYGHOSTHITLER.dec); ID 403 |  |
| 深红ASP | Final Speciman | `FinalSpeciman` | boss | [Actor](../src/actors/classes/bosses/FinalSpeciman.dec); ID 404 |  |
| 黑眼 | Incognito | `BlackDevilEye` | boss | [Actor](../src/actors/classes/bosses/BlackDevilEye.dec); ID 509 |  |
| 黑小丑 | Jester Gelato | `JesterGelato` | boss | [Actor](../src/actors/classes/bosses/JesterGelato.dec); ID 510 |  |
| 红色快送人 | Prickster Prick | `PricksterPrick` | boss | [Actor](../src/actors/classes/bosses/PricksterPrick.dec); ID 513 |  |
| 托马斯 | Thomas the Tank Engine | `ThomasTheTrain` | boss | [Actor](../src/actors/classes/bosses/ThomasTheTrain.dec); ID 519 |  |
| 白ASP | Speciman DX | `SpecimanDX` | boss | [Actor](../src/actors/classes/bosses/SpecimanDX.dec); ID 542 |  |
| 手冲人 | Scroto's Stunt Double | `ScrotoStuntDouble` | boss | [Actor](../src/actors/classes/bosses/ScrotoStuntDouble.dec); ID 613 |  |
| 踩踩背 | Blue Elephant | `BlueElephant` | boss | [Actor](../src/actors/classes/bosses/BlueElephant.dec); ID 616 |  |
| 普通眼 | Plain Demoneye | `PlainDemoneye` | demoneye | [Actor](../src/actors/classes/eyes/Plain.dec); ID 0 |  |
| 发育眼 | Business Eye | `BusinessDemoneye` | demoneye | [Actor](../src/actors/classes/eyes/Business.dec); ID 8 | 用户确认；不是 Rich Demoneye。 |
| 几把头 | Dickhead | `Dickhead` / `DickheadItem` | item | [Actor](../src/actors/items/tow/Dickhead.dec) | “吃了”指地上的 `Dickhead`，吃下获得额外生命；`DickheadItem` 是背包里可投掷的道具。 |

## 消歧与通用规则 / Disambiguation & Guidelines

### 必须消歧的重名 / Alias collisions

| 绰号 / Alias | 当前候选 / Current candidates |
|---|---|
| 飞弹荡妇、飞弹情妇 | `BusterMistress` (survivor) / `TrueBusterMistress` (boss) |
| 弗利萨 | `FrostBite` (survivor) / `SovietFrostBite` (boss) |
| 阿三 | `Igniter` (survivor) / `SovietIgniter` (boss) |
| 蛙哥 | `SumoWrestler` (survivor) / `SadFaceToadMan` (boss) |
| 普通眼 | `ArenaDemoneye` (boss) / `PlainDemoneye` (demoneye) |
| 宝可梦大师 | `Qwant` (survivor) / `CuttyCut` (boss) |
| 牢大 | `FlightUnit` (survivor) / `HeavyBomber` (survivor) |
| 茎输人 | `TheDentist` (survivor) / `CaptainBlitzkrieg` (boss) |
| 海王 | `TidalManiac` (survivor) / `TidalTito` (boss) |
| 马 | `GreenElf` (survivor) / `DLCCentaurman` (boss) |
| 数值怪 | `DecoyBot` (survivor) / `Claire` (survivor) |

遇到以上重名时，必须结合任务上下文消歧；切勿直接取首个匹配项。 / All current candidates must be considered; do not select the first match.

### 类别通用绰号 / Collective aliases

| 绰号 / Alias | 适用范围 / Scope & meaning | 解释规则 / Resolution rule |
|---|---|---|
| 勇者 | Gutsman 类机体或使用其皮肤机体的通用称呼。 / Collective nickname for Gutsman-type classes or classes using Gutsman sprites. | 表示外观/机体类别泛称。涵盖生还者如 `SiteWorker`（俄罗斯方块），以及 Boss 如 `GENERICBOSS`（绿勇者）、`GutsBuddy`（红勇者）、`RussianGuts`（俄罗斯勇者）、`RedeadGuts`（僵尸勇者）等。根据任务上下文区分是普通生还者还是特定 Boss；若带有修饰前缀（如“红勇者”）则直接对应具体 Boss；未指明且无法消歧时询问用户。 / Appearance-based collective nickname. Covers survivor `SiteWorker` and bosses `GENERICBOSS` (Green Guts), `GutsBuddy` (Red Guts), `RussianGuts`, `RedeadGuts`, etc. Distinguish survivor vs boss from task context. Prefixed variants map directly to specific bosses. Ask user if ambiguity remains. |
| 蛙哥 | Toadman 及使用其皮肤机体的通用称呼。 / Collective nickname for Toadman and classes using Toadman sprites. | 表示外观/机体类别泛称。涵盖生还者如 `SumoWrestler`，以及 Boss 如 `SadFaceToadMan`（Toadman）等。根据任务上下文区分是普通生还者还是 Boss；未指明且无法消歧时询问用户。 / Appearance-based collective nickname. Covers survivor `SumoWrestler` and boss `SadFaceToadMan`. Distinguish survivor vs boss from task context. Ask user if ambiguity remains. |
| 几把石 | Stone 皮肤类及可延伸归入的石块外观机体的通用绰号；不限于 Stoneman 皮肤，也可用于 `BlueThwomp`。 / Appearance-based collective nickname for stone-block classes; not limited to Stoneman skins, also includes `BlueThwomp`. | 表示外观类别，不是单一 Actor、代码继承关系或完整成员清单。按需求确定是某个机体还是一组机体；范围不明时询问用户。 / Represents an extensible visual category, not a single Actor, inheritance relation, or closed roster. Determine from task context whether a single class or a group is targeted; ask user if scope remains ambiguous. |

“几把石”按团队用语和任务上下文识别，不能仅因 Actor 名含 Stone、皮肤相似或存在继承关系就自动纳入。用户写的 `bluethromp` 在当前代码中对应 `BlueThwomp`；此前记录的“蓝色几把石”也对应此 Actor。 / Interpret "几把石" through team usage and task context, not automatic Actor-name, visual-similarity, or inheritance rules. The user spelling `bluethromp` refers to the current `BlueThwomp` Actor.

### 收录边界 / Scope

- 本表只保留 Razon4 中确实存在的机体映射，不是全量机体花名册。 / Only mappings for entities present in Razon4 are retained; this is not an exhaustive class roster.
- 红鹰 / 蓝鹰、多色 Joe、灰红蓝黄 ASP 等跨多个机体的集合称呼暂未单独列入；不能将整组称呼直接分配给单一 Actor。 / Collective nicknames spanning multiple classes (e.g. Red/Blue Falcon, multi-colored Joes/ASPs) are not assigned to a single Actor.
