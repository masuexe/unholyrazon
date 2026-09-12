# Shadow boss 连续变形状态泄漏审计

日期：2026-09-12

## 结论

这里的 shadow boss 指特殊事件中的连续流程：同一个玩家从 boss A 卸形，短暂恢复 survivor，随后再变成 boss B。当前实现不应只为某个具体 boss 增加特判；应建立一个与 `BossMorphSetup` 对称的 **boss unmorph cleanup hook**，并在 `UnMorphActor` 前、后各提供一个明确阶段。

当前代码已经能强制修正若干表面 actor flag，但仍有三类实际风险：

1. `core_*player` / `uh_*player` property stacker 的计数留在 inventory 中；把原始 flag 改回 false 并不等于归还了 boss 自己取得的 stack。
2. 以 `ACS_NamedExecuteAlways` 启动的 watcher 只检查玩家存活，不检查当前 morph 身份，因此卸形后仍会继续作用于 survivor 或下一位 boss。
3. 若干非通用速度、跳跃 PowerAprop 不在 `UH_MorphPowerPropReset_P` 的清单中，会随 morph inventory 转移而留下。

其中最优先处理的是 Blue/Purple/Red Destron、Lin、SinfulBusterExpert、Clownpiece、SPOOKYGHOSTHITLER、SakikoTogawa，以及所有能在动作中持有 stacker 状态的 boss。

## 审计范围与判定方法

- 从 `boss_definition_table.acs` 提取到 117 个注册 boss。
- 对当前项目中能解析到的 boss actor 文件及其同名 `_W.dec` 文件进行静态扫描。
- 检查范围包括：property stacker、直接 player property/flag 修改、PowerAprop、永久 inventory、异步 ACS watcher、抓取/unsolid helper，以及仅存在于正常武器状态末端的清理。
- `JuggerbroGold`、`JuggerbroSilver`、`TidalTito` 的 actor 定义不在当前项目 boss 目录中；`FoxDemoneye300` 定义在 eye 目录中。这些依赖项不能仅凭当前 boss 文件集合做同等深度的结论。
- `A_SetScale`、`A_SetTranslucent` 等如果属于同文件内 projectile/helper actor，不算 player 泄漏；报告只列出能追踪到 player/weapon activator 或全局 ACS 状态的项目。

本次是静态审计，没有启动引擎。项目 `AGENTS.md` 所写的三棵解包参考源码路径在当前机器相应位置不存在；因此 Zandronum 的底层 inventory 转移时序采用项目现有注释和两个 modding skill 中的引擎规则作为依据。报告中的“确定/高风险”表示退出路径从源码上不完备，不代表已逐个完成运行时复现。

## 当前卸形路径的问题

`ub_UnMorphThisTID` 当前只做：

1. 对 invulnerability stack 调用一次 `false`；
2. `UnMorphActor(w, 1)`；
3. 调用通用 `uh_MorphDemorphReset`。

参考：`src/acs_source/unholy/uh_bossselect.acs:164-169`。

这有两个结构性问题。

第一，MM8BDM 的 `core_freezeplayer`、`core_stopplayer`、`core_invulnerableplayer`、`core_nogravityplayer`、`core_flyplayer`、`core_nopushplayer`、`core_nonshootableplayer` 等是引用计数式 stacker。一次 `false` 只归还一层。`UH_UnMorphSuperFlagReset_P` 直接改 actor flag 虽能暂时恢复外观和碰撞不出的状态，却不会保证 stack inventory 回到进入 boss 前的基线。

第二，`UnMorphActor` 不会经过当前 boss 武器的正常 `Deselect`/动作收尾。项目自己已经在 GenericBoss air jump 的注释中确认这一点：`src/acs_source/systems/tools/morph_reset.acs:64-67`。所以所有依赖攻击动画末端、Deselect 或 watcher 自然死亡来清理的 boss，都必须考虑被 shadow fakeout 任意时刻打断。

## 确定或接近确定的泄漏候选

### BlueDestron

- `Ready` 调用 `core_flyplayer(..., true)`，没有同文件关闭路径：`BlueDestron_W.dec:21`。
- `rz_BlueDestronShotCooldown` 以 `while (PlayerHealth() > 0)` 持续运行：`special_watchers.acs:120-128`。
- 卸形后 survivor 仍然存活，watcher 会继续给 `BlueDestronAbility_P`，并周期性执行 `DestronDotFire_P`。
- `uh_MorphDemorphReset` 没有调用 `core_flyplayer(false)`。

风险：**严重**。同时具有 player stack 和无限 watcher 泄漏。

### PurpleDestron

- `Ready` 调用 `core_flyplayer(..., true)`：`PurpleDestron_W.dec:20`。
- `rz_PurpleDestronHealth` 只以本地 `health > 0` 为退出条件：`special_watchers.acs:105-117`。
- 卸形后它会继续比较/写入 `LimHealth` 并可能施加 `DestronDotFire_P`。

风险：**严重**。

### RedDestron

- `Ready` 调用 `core_flyplayer(..., true)`，未找到对应关闭：`RedDestron_W.dec:13`。

风险：**高**。没有发现同类无限 watcher，但 flight stack 会跨过 demorph。

### Lin

- boss morph setup 启动 `rz_LinRageWatcher`：`boss_morph_setups.acs:98`。
- watcher 只等待 HP 低于原 boss max HP 的一半；没有检查 Lin 武器、actor class、`MorphedFlag` 或 morph generation：`special_watchers.acs:88-101`。
- survivor 通常会立即满足 `100 <= bossMaxHP/2`，随后收到 `LinCheating_P`。
- `LinCheating_P` 永久取得 `core_nopushplayer` 和 `uh_nohitstunplayer` stack：`Lin_W.dec:419-421`，未发现与 Lin 身份绑定的归还路径。

风险：**严重**。这是最容易在卸形后被 watcher 主动重新污染的案例之一。

### SinfulBusterExpert

- morph setup 启动 `rz_SinfulBusterExpertSinWatcher`：`boss_morph_setups.acs:105`。
- watcher 只检查 `IsDead` 和 `IsAFakeBoss`：`special_watchers.acs:553-571`。
- 通用 demorph 不会添加 `IsAFakeBoss`；因此 watcher 可在 survivor 或下一 boss 身上继续按旧 boss max HP 阈值发放 `SinfulBusterExpert_W2...W8`。

风险：**严重**。主要是异步脚本和武器 inventory 泄漏。

### Clownpiece

- spell-card 状态保存在 `unholy` library 的共享变量中，并启动独立的 `uh_SpellCardTimer`。
- `SpellBreak` 取得 freeze/invulnerability stack：`Clownpiece_W.dec:73-98`。
- W8 的 `FireMoon` 取得 `core_flyplayer(true)`，未见对应关闭：`Clownpiece_W.dec:1143-1148`。
- 正常 spell phase 有清理路径，但 shadow fakeout 可以在任意状态中断，且当前 demorph 不调用 spell-card cancel/reset。

风险：**严重**。需要同时清理 player-owned stack 和 library-global spell-card session；不能只 TakeInventory。

### SPOOKYGHOSTHITLER

- `Ready` 取得 flight stack，未见关闭：`SPOOKYGHOSTHITLER_W.dec:21-27`。
- Altfire 除直接 `SetPlayerProperty(0, 1, 3)`，只关闭 `core_freezeplayer`，未直接把该 property 设回 0：`SPOOKYGHOSTHITLER_W.dec:45-55`。
- 即使数字属性 3 与 freeze 目标重叠，混用 stacker 与直接 `SetPlayerProperty` 也使所有权不可追踪。

风险：**严重**。

### SakikoTogawa

- `Ready` 异步执行 `rz_SakiInit`，写入 `IsAMujicaMember` 并递增 map-global `mujicamembers`：`SakikoTogawa_W.dec:22`、`sakiko_mujica.acs:46-50`。
- 当前 `ClearMujicaState` 是整轮级清理，不是单个 boss 卸形清理。
- shadow fakeout 后如果只清 inventory，不同步递减 `mujicamembers`，成员计数和实际成员会分离；如果 marker 暂时留在 survivor，则下一 boss 仍被视为 Mujica 成员。
- 该 boss 还使用 `UH_50_SpeedPowerGiver`，而通用 Power reset 没有列出 50% speed power。

风险：**严重**。涉及全局计数，必须通过专用函数成对释放，不能只 TakeInventory。

### BalladeGB

- 终局自爆路径先取得 freeze stack，随后才造成自杀：`BalladeGB_W.dec:52-60`。
- 在 freeze 后、自杀前发生卸形时，没有正常关闭 freeze 的路径。

风险：**高**。通用卸形只会强制 actor 表面解冻，不保证 stack 计数清零。

## 高风险的可中断动作与永久能力

以下 boss 大多有正常收尾，但 shadow fakeout 可在收尾前发生；应使用 boss-owned marker 或专用 cleanup 归还其实际持有的 stack。

### Balrog

- `Balrog_Armor_P` 取得 nopush 和 no-hitstun stack：`Balrog_W.dec:462-468`。
- 没有看到与 armor 生命周期严格绑定的对应归还。
- 使用 `UH_40_SpeedPowerGiver`、`UH_82_SpeedPowerGiver`；两者不在通用 morph Power 清单内。

风险：**高**。

### GENERICBOSS

- defensive pickup 取得 nopush/no-hitstun，依赖 `GenericBossDefensive_H` helper 在效果结束时归还：`GENERICBOSS_W.dec:186-211`。
- helper 以 target pointer 和 `PowerQuarterDamage` 判断生命周期。卸形时 pointer、inventory 转移和紧接着的 `ClearActorInventory` 会产生竞态窗口。
- GenericBoss 的 air-jump stack 已经使用 owned marker 修复；这是其他状态应仿照的正确方向。

风险：**高，但已有可复用模式**。

### Rogue

- 每次进入 Ready 都执行 `uh_NoHitStunplayer(true)`：`Rogue_W.dec:23-30`。
- 没有 guard marker，也没有对称关闭；如果 Ready 可重新进入，还可能多次叠加。

风险：**严重**。除了跨 morph，还可能在单次 boss 生命周期内累积多层。

### DLCCentaurman

- rage 开始取得 `uh_cantuseitemsplayer(true)`：`DLCCentaurman_W.dec:198-205`。
- watcher 在正常结束或“不再是 boss”时关闭：`DLCCentaurman_W.dec:297-307`。
- 设计比多数 boss 完整，但仍依赖 helper 获得有效 target TID 并及时运行；shadow 流程在一 tic 后会 `ClearActorInventory`，不应把关键 stack 释放只托付给 watcher。

风险：**中高**。建议专用 cleanup 作为幂等兜底。

### GraniteMauler

- 地遁/抓取路径取得 invulnerable、nonshootable、unsolid，并改变 pickup/floorhugger/alpha：`GraniteMauler_W.dec:146-192`、`:249-281`。
- 正常动作末端有部分关闭，但抓取分支在扫描片段中没有看到完整的 nonshootable 对称关闭。
- 使用 `UH_160_SpeedPowerGiver`，通用 Power reset 未覆盖。

风险：**高**。

### MagicDevilEye

- 已经为 invulnerability、nogravity、stop 分别设置 owned marker，并提供集中 reset pickup：`MagicDevilEye_W.dec:359-373`、`:449-469`。
- 当前通用 demorph 没有调用该 reset pickup。

风险：**中高，但最适合直接接入 hook**。现有 ownership 设计应保留。

### Magnetismo

- 普通 junk 状态取得一次 freeze，并在结束归还。
- rage start 另取得一次 freeze：`Magnetismo_W.dec:236-248`；静态扫描未发现与该 rage stack 明确配对的关闭。

风险：**高**。

### MakeAGoodZero

- phase transition 与 giga crush 都取得 invulnerability stack。
- phase transition 已意识到中断问题并调用 `uh_StripInvulnStacks`：`MakeAGoodZero_W.dec:170-187`，但该清理只在正常 transition 后段运行。
- shadow fakeout 可在长达 200 tic 的 transition 中卸形。

风险：**高**。专用 unmorph cleanup 应复用已有 strip 函数，但应确认它只清该 boss 所有的层，避免清除外部来源。

### 抓取型 boss

以下 boss 使用 `SuplexID`、unsolid、cant-push-walls、stop/freeze/invulnerability，且正常释放散落在长武器状态中：

- TheShadowManMythBoss
- TheCommandoChamp
- ScrotoStuntDouble
- ChieftainTomahawk
- Berserker
- GraniteMauler
- Balrog
- EyelentoMajor

当前通用 reset 会清部分 inventory 和表面属性，但还应在 pre-unmorph 阶段显式释放被抓目标、结束 `uh_Zangief*` 关系，并归还 boss 玩家自己持有的 stack。否则不仅当前玩家可能泄漏，被抓的另一名玩家也可能保持 unsolid、禁用物品或错误指针状态。

风险：**类别级高风险**。

## PowerAprop 清单缺口

`UH_MorphPowerPropReset_P` 当前覆盖的 speed power 是 120、125、130、140、165、175、185、200、250 等固定集合；覆盖的 jump power 也只是部分常用值。这不是按“boss 所有权”清理，而是一个人工维护的类型列表。

静态扫描发现下列注册 boss 使用的 PowerGiver 不在该清单中：

- PlasmaSpark：`UH_35_SpeedPowerGiver`。
- Balrog：`UH_40_SpeedPowerGiver`、`UH_82_SpeedPowerGiver`。
- SakikoTogawa：`UH_50_SpeedPowerGiver`。
- Neru：`UH_135_SpeedPowerGiver`、`UH_145_SpeedPowerGiver`、`UH_150_SpeedPowerGiver`、`UH_Ratio7_6JumpPowerGiver`。
- KFCDragon756：`UH_150_SpeedPowerGiver`。
- Skullman4MI：`UH_150_SpeedPowerGiver`。
- GraniteMauler：`UH_160_SpeedPowerGiver`。
- MeisterWahwee：`UH_150_SpeedPowerGiver`、`UH_200_JumpPowerGiver`、`UH_140_JumpPowerGiver`。
- RepairManEdward：`UH_140_JumpPowerGiver`。
- TheShadowManMythBoss：`UH_225_SpeedPowerGiver`。

这里不能简单把所有遗漏类型加入通用 demorph 清单，因为 survivor 可能合法拥有同类型 Power。更稳妥的方案是 boss 在取得 Power 时同时取得一个 ownership marker，卸形时只移除由该 boss 持有的 Power/marker；或者在进入 boss 前保存相关 Power 的基线计数，卸形后恢复基线。

## 异步 watcher 审计

### 明确需要加身份/generation 条件

- `rz_BlueDestronShotCooldown`
- `rz_PurpleDestronHealth`
- `rz_LinRageWatcher`
- `rz_SinfulBusterExpertSinWatcher`
- Clownpiece 的 spell-card timer/session

这些脚本不能只用 `PlayerHealth() > 0`、`!IsDead` 等条件。建议统一检查：

- 当前玩家仍有本次 morph generation；
- 当前保存的 boss id 与 watcher 启动时相同；
- 必要时再检查专属 weapon/marker。

不要用 `ACS_NamedTerminate` 粗暴结束一个公共 named script，因为它可能终止其他玩家的合法实例。generation token 是多人/竞态更安全的做法。

### 已经较安全的 watcher

- `uh_GravitymanKamiliaELPoll` 同时检查 `GravitymanKamilia_W`，卸形/清 inventory 后会退出。
- Gravityman 的 dye watcher 检查专属 pissed weapon。
- DLCCentaurman rage watcher 检查 boss pointer，并在 Death 路径尝试归还 item-disable stack。

这些仍可由 cleanup hook 做幂等兜底，但优先级低于只检查 HP 的 watcher。

## 推荐架构

### 1. 保存每个玩家的 morph 身份和 generation

在 `MorphActorToBoss` 成功后保存：

```c
int uh_activebossid[MAX_PLAYERS];
int uh_bossmorphgen[MAX_PLAYERS];
```

- 每次成功 morph 增加 generation。
- watcher 启动时捕获 `mygen` 和 `bossid`。
- watcher 每个循环验证两者；变化时只做自己拥有资源的收尾并退出。

不能在 `UnMorphActor` 后再通过 actor class 推断旧 boss；那时 activator 已恢复为 survivor。直接使用 `bossdataarr[i][BOSSDATA_NUM]` 或已保存的 `uh_activebossid` 更可靠，也支持 alias/EX/custom boss。

### 2. 增加与 morph setup 对称的两阶段 hook

建议 API 概念：

```c
SetBossUnmorphCleanupByActor(actor, preScript, postScript);
```

调用顺序：

```text
SetActivator(tid)
  -> boss pre-unmorph cleanup
  -> invalidate morph generation
  -> UnMorphActor(tid, 1)
  -> SetActivator(tid)
  -> generic demorph reset
  -> boss post-unmorph cleanup
```

pre 阶段负责：

- 归还 boss-owned property stacks；
- 释放抓取目标与 helper pointer；
- 终止/失效 watcher；
- 取消 Clownpiece spell session、Mujica membership等 boss/global 状态；
- 移除明确由 boss 取得的 PowerAprop。

post 阶段只负责那些经 `P_UndoPlayerMorph` inventory 转移后才能安全处理的残留，并验证 survivor 的默认属性。不要把全部 boss 的特殊清理都塞进通用 `UH_UnMorphSuperFlagReset_P`。

### 3. 对 stacker 使用所有权 marker，而不是无条件 `false`

推荐模式：

```c
if (!CheckInventory("BossXOwnsFreeze_F")) {
  ACS_NamedExecuteWithResult("core_freezeplayer", 0, true);
  GiveInventory("BossXOwnsFreeze_F", 1);
}
```

cleanup：

```c
if (CheckInventory("BossXOwnsFreeze_F")) {
  ACS_NamedExecuteWithResult("core_freezeplayer", 0, false);
  TakeInventory("BossXOwnsFreeze_F", 1);
}
```

如果一个 boss 合法取得多层，应使用计数 marker 并逐层归还。这样不会误删地图、道具、其他 mod 或 survivor 本身取得的 stack。

GenericBoss 的 `GenericBossAirDisable_F` 和 MagicDevilEye 的 `MagicDevilEyeInvul_F` / `NoGrav_F` / `Stop_F` 已经提供了项目内先例。

### 4. 通用 reset 只保留真正通用的恢复

`uh_MorphDemorphReset` 应保留：

- 原 survivor 的 air/wall jump snapshot 恢复；
- `MorphedFlag`、`BAWS` 等 morph 协议 marker；
- DefaultProperties 重建；
- water gravity 恢复；
- 能证明所有 boss 都必须恢复、且不会覆盖 survivor 合法状态的内容。

`UH_UnMorphSuperFlagReset_P` 中直接设置 `BUDDHA`、`NOTARGET`、`NONSHOOTABLE`、`CANTSEEK`、`INVISIBLE`、`DONTIDENTIFYTARGET`、`SOLID`、`NOGRAVITY` 等操作，需要逐项确认。它们可能掩盖 stack 计数错误，也可能覆盖 survivor/地图效果的合法状态。最终应尽量由 owned stack cleanup 取代。

### 5. shadow manager 传入旧 boss id

当前 manager 调用 `ub_UnMorphThisTID` 时掌握 `bossdataarr[i][BOSSDATA_NUM]`。应把它作为第二参数传入，避免在异步脚本中重新查询一个随后会被改写的数组槽：

```c
ACS_NamedExecuteAlways(
  "ub_UnMorphThisTID", 0,
  bossdataarr[i][BOSSDATA_TID],
  bossdataarr[i][BOSSDATA_NUM]
);
```

`ub_TestShadowBoss` 也应显式提供旧 boss id，或从保存的 active boss state 读取。

## 建议实施顺序

1. 先实现 active boss id、generation 和 pre/post unmorph dispatcher，不改各 boss 行为。
2. 第一批接入 Blue/Purple/Red Destron、Lin、SinfulBusterExpert、Clownpiece、SPOOKYGHOSTHITLER、SakikoTogawa。
3. 第二批接入抓取型 boss，以及 Balrog、Rogue、GraniteMauler、MagicDevilEye、Magnetismo、MakeAGoodZero、DLCCentaurman。
4. 为缺失的 PowerAprop 增加 ownership marker；不要继续扩张全局类型黑名单作为最终方案。
5. 最后审查并缩小 `UH_UnMorphSuperFlagReset_P`，防止它掩盖计数问题。
6. 运行确定性 shadow fakeout 测试：在每个高风险 boss 的关键动作中途强制卸形，检查 survivor 阶段及 boss B 阶段的 inventory、actor flags、速度/跳跃、stacker marker、运行中的 watcher 和被抓目标。

## 验收条件

- boss A 在任意武器 state 被卸形后，survivor 不保留 A 的飞行、冻结、停止、无敌、不可射击、无实体、禁用物品、抗推/抗硬直、速度/跳跃 Power。
- 被 boss A 抓取的其他玩家立即恢复，且不存在悬挂 helper/pointer。
- boss A 的 watcher 在一个 tic 内因 generation 失效退出，不再给 survivor 或 boss B inventory。
- boss B 的 stacker 开关从正确基线开始；一次 `true` 与一次 `false` 后能完全恢复，而不是被 A 留下的隐藏计数污染。
- Mujica 和 Clownpiece 等 map-global 状态与实际当前 boss 身份一致。
- survivor 合法的地图/道具/StartItem 状态没有被通用 cleanup 误删。

