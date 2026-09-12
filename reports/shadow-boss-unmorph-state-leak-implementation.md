# Shadow boss unmorph state leak — 实施记录

对应审计：`reports/shadow-boss-unmorph-state-leak-audit.md`
状态：已实现（静态验证通过；运行时验收见文末）

## 1. 新增架构

### morph 身份 / generation（审计 §1）
- `src/acs_source/_imports/uhdt.acs`
  - `uh_playermorphgen[]`、`uh_playeractiveboss[]`（共享 UHDT 存储，所有 import 该文件的库都可读）。
  - `BeginPlayerBossMorph` / `EndPlayerBossMorph` / `GetPlayerMorphGen` / `GetPlayerActiveBossId`。
  - 成功 morph 与每次 unmorph 都递增 generation；退化的旧 watcher 自行退出，不用
    `ACS_NamedTerminate` 去杀公共 named script。
- 记录点：`MorphActorToBoss`（`unholy/uh_funclib.acs`）与 Boss FFA 的
  `BossFFAMorphPlayer`（`unholy/uh_events.acs`）都在启动 morph setup（也就是启动 watcher）
  之前记录，因此 watcher 捕获的一定是本次 morph 的 generation。

### 两阶段 unmorph hook（审计 §2、§5）
- UHDT 注册表：`SetBossUnmorphCleanup(id, pre, post)` / `GetBossUnmorphPre/Post`。
- 公共 API：`uhadd.acs` 的 `SetBossUnmorphCleanupByActor` / `...ById`；
  CVar 桥接 handler 在 `corescripts/api_handlers/uhaddr.acs`。
- 调度：`unholy/uh_bossselect.acs` 的 `ub_UnMorphThisTID(w, bossid)`：

  ```text
  SetActivator(tid)
    -> 通用 pre：剥离 UnholyPowerLimit_F / UnholyPowerDisableRazzle_F
    -> boss pre cleanup      (boss 武器/marker 仍在，可判所有权)
    -> EndPlayerBossMorph    (generation 失效)
    -> UnMorphActor + uh_MorphDemorphReset
    -> 通用 post：按 GetBossActor(bossid) 剥离 <Actor>_W / _W1.._W9
    -> boss post cleanup
  ```
- shadow 调用点显式传入旧 boss id：`ub_ShadowBossManager` 传
  `bossdataarr[i][BOSSDATA_NUM]`（该槽随后会被改写），`ub_TestShadowBoss` 传当前
  active boss。

### stacker / Power 基线快照（审计 §3、§4 的替代实现）
`src/acs_source/systems/tools/morph_reset.acs` 在 `MorphActor` 前保存、`UnMorphActor` 后恢复：

| 快照 | 覆盖 |
|------|------|
| `Uh_Save/RestoreMorphJumpInventory` | AirJumpLimit / WallJumpLimit |
| `Uh_Save/RestorePropStackBaseline` | 27 种 stacker inventory（core_*player 与 uh_*player 家族） |
| `Uh_Save/RestoreMorphPowerBaseline` | 40 种 UH PowerAprop（speed 35…250、jump、alpha） |

- 恢复按 `while (cur > want) 调 stacker(false)` 逐层回退，因此派生属性/actor flag 会随计数
  一起归零；不是裸 `TakeInventory`。
- **没有采用** 审计建议的 `BossXOwnsFreeze_F` 逐点 marker。原因：基线快照对全部 117 个 boss
  一次生效、不需要改 60+ 处 DECORATE 获取点（改这些点还有相对 `A_Jump` 偏移风险），
  并且额外修复了"morph 自己吃掉 survivor 合法层"的问题（`BasicBossItem` 每次 morph 都会
  无条件 pop 一层）。审计在 §4 也把"保存基线、卸形后恢复"列为可接受方案。
- re-morph 保护：`MorphedFlag` 存在时不覆盖快照（boss 复活/重试不会把 boss 的临时状态
  写成 survivor 基线）。

### 评审修复（Bugbot P1）
`uh_MorphPreReset` 在重写时丢掉了原有的 `UH_ClearGenericBossAirDisable();`。该调用专为
**没有经过卸形的直接 re-morph**（Dickhead 复活、morph 重试、Boss FFA、事件 morph 路径）而存在：
GenericBoss 武器的 `Deselect_ClearAir` 在 re-morph 时不会执行，因此 `DisabledAirJumps` 与
`GenericBossAirDisable_F` 会残留到下一个 boss，永久禁用它的空中跳跃。已恢复该调用
（基线快照本身不覆盖 `DisabledAirJumps`），并加注释说明原因。

### 评审修复 2（Bugbot P1：raw flag floor 与计数恢复的错配）
`UH_UnMorphSuperFlagReset_P` 会强制清除 BUDDHA / NOTARGET / NONSHOOTABLE / CANTSEEK /
INVISIBLE / DONTIDENTIFYTARGET / NOGRAVITY / CANPUSHWALLS / NORADIUSDMG 并把 SOLID 置真，
而 base game 的 stacker 只在 ON 路径应用属性、只在自身计数归零时清除。原来的恢复循环仅在
`cur != want` 时调用 stacker，于是：

- baseline 非零且计数已经等于 baseline（这些属性 `BasicBossItem` 不会 pop，例如 Buddha、
  NoTarget、Invisible、CantPushWalls、NoRadiusDmg）时，flag 被清了却不会重新应用；
- boss 叠加到 2 层、卸形时从 2 减到 1 时，计数正确但 flag 已被清除。

修复：新增 `uh_morphpropstackfloor[]` 标记被 floor 影响的 11 个条目，恢复循环在计数对齐后对
`want > 0` 的条目做一次显式 refresh —— 调 stacker ON（应用属性并 +1），再按实际增量
`TakeInventory` 回退计数（计数未归零，因此不会触发 resolidify/Off 事件）。增量按
`Inventory.MaxAmount` 截断后的真实差值回退，避免把计数压到 baseline 以下。
不变量：卸形后每个 stacker 满足「计数 == survivor baseline 且 flag == (baseline > 0)」。

### 评审修复 3（独立审查：无快照路径、Power 只恢复计数、forced 刷新）
1. **baseline 有效性标志**：PowerMorph（Demoneye/Clone）与引擎 death-unmorph 不经过
   `uh_MorphPreReset`，但仍会走 `uh_MorphDemorphReset`（shadow 路径）。此时 map 作用域的
   `uh_morphsaved*` 全为 0，恢复逻辑会把玩家的 extra life / Buddha / NoHitStun / 跳跃上限 /
   UH Power 全部清零。现在新增 `uh_morphbaselinevalid[]`：只有真正取过快照才置位，三个恢复
   函数在未置位时直接返回（不写任何值），并在一次 demorph 后消费掉该标志。
2. **Power 恢复改为"给 Giver"**：`SetInventory("UH_*Power", n)` 只改计数，不会应用 APROP
   （唯一应用路径是 Giver pickup 触发的 `core_aproppoweractivator`），而"计数非零但 APROP
   未应用"还会吞掉之后真正的 Giver pickup。恢复方向改为
   `GiveInventory(StrParam(s:name, s:"Giver"))`；移除方向沿用 mod 既有的 marker 移除路径。
3. **forced 条目顺序与计数**：`PlayerPropertyFlightForced` / `NoGravityForced` 的 ON 会同时
   增加 base 计数，且原表按 base→forced 顺序遍历会让 base 的 OFF 抹掉 forced 层。现在
   forced 条目排在 base 之前，refresh 时同时回退 forced 与 base 两个计数（按实际增量）。

### 评审修复 4（所有权边界缓解：per-boss stacker 家族掩码）
绝对计数恢复无法区分"boss 自己加的层"和"morph 期间地图/道具/其他 mod 加的层"。本次落地
的缓解措施：为每个已注册 boss 生成 stacker **家族掩码**（扫描该 boss 自己的 DECORATE 得到），
down-clamp 只允许作用于掩码内的家族；掩码外的家族出现增量时一律保留。

- 数据流：`uh_bossunmorphfams[]`（UHDT，注册行为 `-1` = 未知/全部）←
  `SetBossUnmorphFamsByActor`（uhadd，经 `uh_SetBossUnmorphOwnedFamilies_S` 桥接）←
  `UH_RegisterBossOwnedFamilies` 的 19 行掩码；`ub_UnMorphThisTID` 读取后作为参数传给
  `uh_MorphDemorphReset(ownedfams)` → `UH_RestorePropStackBaseline(ownedfams)`。
- 效果：例如 SinfulBusterExpert 只会被回退 Frozen/NoGravity，其余 25 个家族（invuln、buddha、
  invisibility、unsolid…）在 morph 期间的外部增量不再被删除；未注册 boss 与 addon 保持旧行为。
- 掩码由脚本从 DECORATE 生成（见下表），不手工维护；SakikoTogawa 为 0（它只泄漏 Power/全局状态）。

### 评审修复 5（精确所有权：per-site marker 迁移，已完成）
在家族掩码之上，把 boss 的 stacker 获取/释放点全部改为维护"boss 自有层账本"的包装脚本，
down-clamp 现在只退还账本记录的层：

- 账本：`uh_bossstackowned[player][family]`（uh_tools，ACS map 数组，随玩家索引天然跨 morph）。
- 包装：`uh_BossStackOn(family)` / `uh_BossStackOff(family)` / `uh_BossUnsolidOn` /
  `uh_BossUnsolidOffDmg(dmg)`（后者保留 `USP_TOGGLEOFF_DAMAGE` 语义）。
  OFF 只在账本 > 0 时递减（绝不出现负漂移），但仍无条件调用原 stacker，行为与迁移前一致。
- 迁移：`tools/migrate-boss-stackers.py`（本次新增，dry-run 默认）把严格可判定的
  `("core_*player", 0, toggle)` 形式改写为包装调用：**85 个文件、692 处**
  （On 289 / Off 365 / UnsolidOn 19 / UnsolidOffDmg 19），全部为 1:1 行替换，
  因此不会移动任何相对 `A_Jump` 偏移。范围＝boss 目录 + `bosswepbase.dec`（BasicBossItem）+
  `baseweaponedit.txt`（NoAmmo_B）+ `Zangief_W.dec`（SuplexStartA/ResetFlags）+
  `GeneralThings_U.dec`（Invulnerable/Shadow PreRound 对）。
- 释放：`while (账本 > 0 && cur > baseline)`，i==15 走 `USP_TOGGLEOFF_NONE`；随后清空该玩家账本行。
  家族掩码只是附录信息（公共 API），**不**参与这条释放路径——boss 也可能通过共享授予 actor
  获得某个家族，用掩码去挡会造成假漏；账本与 baseline 下限已经足够。
  账本偏高只会少退（安全方向），baseline 下限保证永不低于 survivor 既有状态。
- 未迁移的残留（都是安全方向）：12 处作用于**其他玩家**的调用（`Args[3]-999`、
  `CallACS("core_gettarget")-999` 等，属于其他玩家的状态，本就不该计入本玩家账本）；
  `GeneralThings_U.dec:125` 的 `core_flyplayer(0,2)`（toggle=2 的"不 Thing_Stop"变体，
  包装语义不同，保持原样）。

### 评审修复 6（PowerAprop 账本 + 账本窗口门控）
- **PowerAprop 也改为 boss 自有账本**（Bugbot P1）：新增 `uh_bosspowerowned[player][index]` 与
  `uh_BossPowerGive(index[,amount])` / `uh_BossPowerTake(index[,amount])` 包装，
  由同一个迁移工具把 boss DECORATE 的 `A_GiveInventory("<Power>Giver")`（40 处）与
  `A_TakeInventory("<Power>")`（58 处）改写过来；索引表由工具直接从
  `uh_morphpowername` 解析，不会与运行时表漂移。
- **去掉 demorph 的无条件 Power 清表**（`UH_MorphPowerPropReset_P`）：它会在账本生效前
  就删掉 morph 期间外部授予的同类型 Power。现在卸形只删除账本记录的那几层，
  survivor 基线通过 Giver 重新授予（Giver 是唯一会应用 APROP 的路径）。
- **账本窗口门控**（Bugbot P2）：`UH_BossStackNote` / `UH_BossPowerNote` 只在
  `uh_morphbaselinevalid[p]` 为真（即处于有效 morph 窗口）时记账；取新 baseline 时把两个账本行
  清零，因此 survivor 武器、共享授予 actor、shadow 前回合 actor 的遗留记账不会进入下一次 morph。

### 原剩余缺口（已由上面的迁移关闭）
在 boss 确实会使用的家族内，若地图/道具/其他 mod 在 morph 期间也加了**同一家族**的层，
该层仍会被回退。要精确到"每一层归谁"，需要审计 §3 的 per-site ownership marker：

- 包装脚本 `uh_BossStackOn/Off`（family 参数，调用原 stacker 并维护
  `uh_bossstackowned[player][family]` ACS 账本；OFF 仅在账本 > 0 时递减，永不产生负漂移）。
- 转换面：boss DECORATE 中 577 处 `(0, toggle)` 调用点（81 个文件），其中 unsolid 需要单独
  一对包装以保留 `USP_TOGGLEOFF_DAMAGE` 语义；此外必须成对转换
  `Zangief_SuplexStartA_P` / `ZangiefResetFlags_P`、`ShadowPreRoundStart/End`、
  `InvulnerableOn/Off_Pickup`、`LinCheating_P`、`MagicDevilEye_ClearProps_P` 等跨文件授予/释放，
  否则账本漂移会把真实层删掉（比现状更糟）。
- 卸形释放改为：`while (owned > 0 && cur > baseline) { stacker(OFF); owned--; }`，再把该玩家的
  账本行清零 —— 这样即使账本偏高也只会吃掉"窗口内新增的多余层"，绝不回退到 baseline 以下。
- 必须配运行时验收：逐个 boss 中途 fakeout，核对账本与层数（marker 平衡静态校验只能覆盖
  配对计数，覆盖不了运行期分支）。

### watcher 身份校验（审计 §异步 watcher）
`classes/shared/special_watchers.acs`：`rz_LinRageWatcher`、`rz_PurpleDestronHealth`、
`rz_BlueDestronShotCooldown`、`rz_SinfulBusterExpertSinWatcher` 每 tick 校验
`UH_WatcherStillOwnsBoss(gen, player)`（generation 未变且 active boss 仍存在）。

`systems/tools/player_queries.acs`：`uh_PointerIsABoss` 增加 `MorphedFlag` 判定。
这是 DECORATE helper/watcher 的统一切断点，影响 358 处调用（`BasicBoss_Rooted`、
ChieftainHold_H、ShadowMan Cloak/Smoke、DLCCentaurOption/Rage watcher、
MagicDevilEye_PewWarper、MGZero watcher 等），使它们在卸形后自行 Death，而不是继续
作用在 survivor 身上。

## 2. 逐 boss cleanup（`classes/bosses/boss_unmorph_cleanups.acs`）

19 个注册项：

- **第一批**：BlueDestron / PurpleDestron（Ability、DotFire、LimHealth）、Lin
  （LinCheating_P、`UH_XRayVisionOn_F`）、SinfulBusterExpert（SBE 弹药与瞄准 helper）、
  Clownpiece（spell session）、SakikoTogawa（Mujica 成员计数）。
- **第二批**：8 个抓取型 boss 共用一个 `GrabRelease`（SuplexID / IsPerformingSuplex /
  ZangiefAngle / ZangiefHoldFlag 等），以及 Rogue、MagicDevilEye（复用其自带
  `MagicDevilEye_ClearProps_P`）、Magnetismo、MakeAGoodZero、DLCCentaurman。
- RedDestron、SPOOKYGHOSTHITLER 无需注册：前者只有飞行层，后者在 DECORATE 修掉了
  裸 `SetPlayerProperty(0,1,PROP_FLY)` 之后也只剩飞行/冻结层，均由基线快照覆盖。

配套修正：
- `unholy/clownpiece_spellcard.acs`：新增 `uh_ClownpieceUnmorphCancel`
  （结束共享 spell-card session + 清本人 phase marker）；`ub_SelectBossAndEvent` 每回合
  开始也调一次 `uh_SpellCardStop`，避免上一回合死亡的 Clownpiece 把 phase 留到下一回合。
- `unholy/sakiko_mujica.acs`：新增 `uh_MujicaRelease`，成对释放成员计数并同步
  `Sora no Musica` 取消。
- `systems/shared/projectile_and_xray.acs` + `GeneralThings_U.dec`：无限 X-Ray 管理器
  改为受 `UH_XRayVisionOn_F` 控制，Lin 卸形时可以真正关掉 nametag（此前只按生命值退出）。
- `ScrotoStuntDouble_W.dec`：`uh_ZangiefGiver` 的 TID 由 `rz_CountInv_ZangiefAngle`
  改为 `rz_CountInv_SuplexID`（与其它抓取 boss 一致），被抓玩家才会真正拿到
  `AntiInvincible_P`。
- `MakeAGoodZero_W.dec`：两个 boss 追踪 watcher 改用 `uh_PointerIsABoss`，卸形后走
  Death 分支归还额外无敌层。

## 3. `UH_UnMorphSuperFlagReset_P` 审查结论（审计 §5）

- 基线恢复安排在 flag floor **之后**执行，因此 BUDDHA / NOTARGET / NONSHOOTABLE /
  CANTSEEK / INVISIBLE / DONTIDENTIFYTARGET / NOGRAVITY / CANPUSHWALLS / NORADIUSDMG /
  SOLID 的 survivor 合法层会被重新加回。
- 保留该 actor 作为"绕过 stacker 的裸 flag 写入"（例如 GraniteMauler 的
  `A_ChangeFlag("NONSHOOTABLE",1)`）的兜底。
- 仍有残余暴露面：非 stacker 来源的 invisibility / unsolid 会被 floor 覆盖。逐项删除需要
  运行时确认，已记录为后续项，未在本次删除。

## 4. 验证

已完成（静态、可复现）：

- `tools/compile-acs.sh`（本次新增）：按 LOADACS 顺序用 Zandronum ACC 1.60 编译全部
  39 个库，输出名与源 lump 名一致（v6b LOADACS 按 lump 名寻址）。
  结果：**39/39 编译通过**。
- 基线版本比对：未改动的库重新编译后与原 `.o` 字节一致，只有本次修改涉及的库变化。
- 注册表一致性脚本检查：19 个 actor 名都能在 `boss_definition_table.acs` 找到；
  pre 脚本全部有定义；prop-stack 四条并行数组均为 27 项。
- stacker 脚本名与 v6b `acs/PROPUTIL.o` / `uh_aprop.acs` 逐一核对存在。
- `out/build.pk3` 按 `src/.pk3ignore` 规则重打包（16562 项，与原清单一致），
  `tools/validate-build-pk3.sh` → `status=ok`。

仍需运行时验收（审计 §6，未执行，需要用户明确允许启动引擎）：

1. 每个高风险 boss 动作中途强制 shadow fakeout，检查 survivor 阶段的 inventory、
   actor flags、速度/跳跃、stacker marker、watcher 与被抓目标。
2. 非 stacker invisibility/unsolid 的场景（决定 flag floor 还能删哪些行）。
3. Clownpiece spell session 与 Mujica 计数在多人下的表现。
