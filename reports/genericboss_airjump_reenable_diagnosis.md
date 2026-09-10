# GenericBoss 满弹药后无法恢复 AirJump：诊断与处理方案

## 结论

用户对现象的判断基本正确：`GENERICBOSS_W` 的 `Flash` 监视器没有持续运行，因此 Ammo1 回满后不会移除该武器自己添加的 `DisabledAirJumps`。

但更准确的根因不是普通的“未进入 `A_GunFlash`”，而是 **Morph 武器初始化期间确实可能执行了 `A_GunFlash`，随后引擎又立即清空了 flash psprite**。

不建议把 `Ready` 中重新加入 1 tic 作为最终设计。推荐通过现有的 `uh_BossMorphSetup_GENERICBOSS`，在 `MorphActor()` 完成、引擎清空 flash psprite之后，显式启动 GenericBoss 的 flash 监视器。

## 证据链

### 1. GenericBoss 的恢复逻辑只存在于 Flash

当前 `GENERICBOSS_W`：

- `Ready` 调用 `A_GunFlash`。
- `Flash_Low` 在 Ammo1 小于 100 时添加：
  - `DisabledAirJumps`
  - `GenericBossAirDisable_F`
- `Flash_Full` 在 Ammo1 回到 100 且存在 `GenericBossAirDisable_F` 时，移除上述两个库存。

因此，只要 `Flash` 监视器消失，Ammo1 虽然会在 `ReadyX` 中继续恢复，`DisabledAirJumps` 却不会被解除。

### 2. Zandronum 会在 Morph 初始化末尾清空 flash psprite

Zandronum 的 Morph 顺序为：

1. `P_MorphPlayer()` 创建并配置新 Pawn。
2. 调用 `APlayerPawn::ActivateMorphWeapon()`。
3. `ActivateMorphWeapon()` 设置 `ReadyWeapon`。
4. `P_SetPsprite(ps_weapon, Ready)` 立即遍历武器 `Ready` 开头的零 tic 状态，所以其中的 `A_GunFlash` 可以运行。
5. `ActivateMorphWeapon()` 随后执行 `P_SetPsprite(player, ps_flash, NULL)`，无条件清空刚启动的 Flash。
6. `MorphActor()` 返回 ACS。
7. `MorphActorToBoss()` 才调用 `uh_MorphPostReset` 和已注册的 boss morph setup。

相关引擎位置：

- `../references/zandronum/zandronum-stable-branch-default/src/g_shared/a_morph.cpp`：`P_MorphPlayer()` 调用 `ActivateMorphWeapon()`。
- `../references/zandronum/zandronum-stable-branch-default/src/p_user.cpp`：`ActivateMorphWeapon()` 先设置 weapon psprite，最后清空 `ps_flash`。
- `../references/zandronum/zandronum-stable-branch-default/src/p_pspr.cpp`：零 tic 状态会由 `P_SetPsprite()` 在同一次调用中连续执行；`A_GunFlash()` 设置 `ps_flash`。

这也解释了为什么在 `A_GunFlash` 前放置 1 tic 能临时修复：`P_SetPsprite()` 在该非零 tic 帧停止，等下一 tic 才执行 `A_GunFlash`；此时 `ActivateMorphWeapon()` 的末尾清理已经结束。

## 推荐实现

### 方案 A：从 Morph setup 在正确时点启动现有 Flash（推荐）

保留 `Flash` 中现有的 Ammo/AirJump 状态机，但不要依靠 morph weapon 的首个 `Ready` 零 tic链启动它。

1. 新增一个一次性 `CustomInventory` helper，其 `Pickup` 状态只执行：

   ```c
   TNT1 A 0 A_GunFlash("Flash", GFF_NOEXTCHANGE)
   ```

   `GFF_NOEXTCHANGE` 可避免仅为启动后台监视器而切换 Pawn 的攻击动画。

2. 在 `uh_BossMorphSetup_GENERICBOSS` 中，在 `SetActivator(tid)` 后发放该 helper。

3. 从 `GENERICBOSS_W.Ready` 删除启动用的 `A_GunFlash`，避免非 Morph 获取、武器重新选择或 Ready 重入时重复重置同一个 flash psprite。若项目仍支持不经过 boss Morph setup 取得该武器，则需要单独定义那个入口的启动责任，不能盲目删除。

该方案通常不需要 `Delay(1)`。boss setup 是在 `MorphActor()` 返回后调用的，此时 `ActivateMorphWeapon()` 已经完成最后的 `ps_flash = NULL`。因此它解决的是调用顺序，而不是用任意延迟掩盖顺序。

为什么 helper 可行：Zandronum 的 `ACustomInventory::TryPickup()` 通过 `CallStateChain(toucher, PickupState)` 执行 Pickup 动作，动作的 `self` 是获得物品的 Pawn；`A_GunFlash` 因而能够取得该 Pawn 的 `player` 与当前 `ReadyWeapon`。

### 方案 B：改为 ACS watcher（不作为首选）

也可以从 `uh_BossMorphSetup_GENERICBOSS` 启动一个每 tic 检查 Ammo、`AirJumpsUsed` 和 class/TID 的 ACS watcher，并把整个 `Flash` 状态机迁移到 ACS。

缺点：

- 需要处理 watcher 去重、死亡、unmorph、换 Pawn、断线和 TID 复用。
- 需要确保服务器权威执行并验证库存同步。
- 会把一个适合 psprite 的短状态机扩展成生命周期更复杂的常驻脚本。
- 容易重复扣除 Ammo，必须保持现有语义：一次空中跳跃将 Ammo 降到不足 100，落地及回满后才恢复权限。

只有计划彻底移除 GenericBoss 的 Flash 后台逻辑时，才值得选用此方案。

### 方案 C：在 Ready 中加入 1 tic（可接受的临时修复）

在 `A_GunFlash` 前增加 1 tic 的确符合引擎时序，成本最低。但它把 Morph 初始化约束隐藏在普通武器状态中，也会延迟 Ready 后续动作，因此应视为保底修复，而不是首选架构。

## 与 FixMorph 删除的关系

该问题不是删除 `FixMorph_PropPower` 后产生的新属性恢复问题。

此前的 3 tic 帧同时承担了两个偶然效果：

- 等待 `FixMorphAirJumpZ_Pow` 到期，避免覆盖 GenericBoss 的特殊 AirJumpZ；
- 阻止 Morph 初始化在同一次 `P_SetPsprite()` 中继续执行到 `A_GunFlash`，从而让 Flash 躲过引擎末尾的清空。

删除 FixMorph 后，第一个等待理由消失，但第二个隐含时序作用也随之消失，暴露了原有的 psprite 生命周期问题。不要为此恢复 FixMorph 或恢复 3 tic；应单独修正 Flash 的启动时点。

## 建议实施顺序

1. 实现方案 A 的一次性 CustomInventory starter。
2. 由 `uh_BossMorphSetup_GENERICBOSS` 发放 starter。
3. 确认是否存在绕过 `MorphActorToBoss` / `BossFFAMorphPlayer` 而直接获得 `GENERICBOSS_W` 的受支持入口，再决定是否删除 `Ready` 内旧调用。
4. 保留显式 `CAPROP_AirJumpZ = 30.0`；它与是否允许 AirJump 是两件事。
5. 不恢复 `FixMorph_PropPower`。

## 低成本验收

至少覆盖单机和一组服务器/客户端：

1. Morph 为 GenericBoss。
2. 确认初始 Ammo1 满时可以 AirJump。
3. 使用 AirJump 后确认 Ammo1 被消耗，并在不足 100 时被禁用。
4. 落地等待 Ammo1 回满，确认 `DisabledAirJumps` 与 `GenericBossAirDisable_F` 被成对移除。
5. 再次 AirJump，确认高度仍为 `30.0`，而不是 Pawn 的普通 `JumpZ = 12.0`。
6. 死亡、unmorph 或离开 GenericBoss 时，确认只清理由 GenericBoss 自己添加的 disable stack，不移除外部系统添加的 `DisabledAirJumps`。
7. 如果保留任何非 Morph 获取入口，单独验证该入口也能启动监视器。

## 风险提示

- 不要在通用 `uh_MorphPostReset` 中无条件启动 GenericBoss Flash；该层不知道具体武器状态，责任应留在已注册的 per-boss setup。
- 不要直接在 ACS 中无条件 `TakeInventory("DisabledAirJumps")`；必须继续以 `GenericBossAirDisable_F` 标识所有权，避免移除地图、状态效果或其他系统施加的禁跳。
- 如果 starter 指定字符串状态 `"Flash"`，应在执行前确保当前 `ReadyWeapon` 确为 `GENERICBOSS_W`。现有 Morph setup 调用时序满足这一条件，但其他入口需要单独核实。

## 执行结果（2026-09-10）

方案 A 已实现并通过 MCP 运行时验收：

- `GENERICBOSS_W.dec`：新增一次性 `GenericBossFlashStarter_P`（Pickup 状态执行 `A_GunFlash`），删除 `Ready` 内旧 `A_GunFlash`。已确认 `GENERICBOSS_W` 只能经 `player.morphweapon` 获得，无非 Morph 入口。
- `boss_morph_setups.acs`：`uh_BossMorphSetup_GENERICBOSS` 在 `SetActivator(tid)` 后发放 starter。

实现中发现并修正了报告未覆盖的一点：`uh_MorphPostReset → DefineDefaultProperties` 会在 morph 后无条件把 `CAPROP_AirJumpZ` 重置为 Pawn 默认 12.0（旧 FixMorph 时代由 `FixMorphAirJumpZ_Pow` 顶住）。因此 starter 的 Pickup 状态同时重新执行 `core_SetCustomActorProperty(0, CAPROP_AirJumpZ, 1966080)`，再启动 Flash。`Ready` 中的原属性行保留不动。

MCP 验收（`pukename rz_debug_GBAirTest`，脚本已留在 `debug/rz_debug.acs`）：

1. Morph 后满弹药 100：无 `DisabledAirJumps`、无 `GenericBossAirDisable_F`。
2. `airjumpz=1966080`（30.0）确认生效。
3. 弹药降至 5：`DisabledAirJumps=1`、`OurFlag=1` 成对出现。
4. 回满 100：两者成对移除（0/0）。

后续人工验收已完成：真实按键的空中跳跃高度、落地回满后的再次跳跃，以及死亡/unmorph 时 **GenericBoss 自有 `DisabledAirJumps` + ownership flag** 的清理均已通过。本报告所述 GenericBoss Flash/AirJump gate 修复可以视为验收完成；这不代表所有 morph 专属 inventory 都已在 unmorph 后恢复，下面记录的 `AirJumpLimit` 残留是独立问题。

## 验收旁观：unmorph 后 `AirJumpLimit` 残留（本次未改）

验收时另外观察到：从 GenericBoss unmorph 回幸存者后，`AirJumpLimit=1` 会残留。这个现象不属于本次已经修复的 Flash gate：

- `GenericBossAirDisable_F` 与它拥有的 `DisabledAirJumps` stack 已按设计清理；残留的是决定可用空中跳跃次数的 `AirJumpLimit`。
- `uh_BossMorphSetup_GENERICBOSS` 会给 morph pawn 一个 `AirJumpLimit`。
- Zandronum 的 `P_UndoPlayerMorph()` 会执行 `mo->ObtainInventory(pmo)`，把 morph pawn 的普通 inventory 转移回原 pawn；引擎随后只对 morph weapon 做专门移除，不会按本 mod 的语义识别并删除 `AirJumpLimit`。
- 当前 `uh_MorphDemorphReset` 会清理 GenericBoss 自有禁跳标记、morph flags 与属性 power，但没有清理或还原 `AirJumpLimit`、`AirJumpsUsed`、`InfiniteAirJumps`、`WallJumpLimit` 等 jump inventory。
- `BossWepBase` 的清理状态虽有 `A_TakeInventory("AirJumpLimit")`，但不能假定 weapon deselect/death state 会覆盖所有 `UnMorphActor` 路径；这和此前 Flash deselect 不会在 unmorph 时可靠执行是同一类生命周期边界。

因此应把它登记为更广泛的 **morph inventory ownership/restore** 问题，而不是在 GenericBoss starter 中再补一个局部 `TakeInventory("AirJumpLimit")`。其他 boss/class morph setup 也可能赋予不同数量的 jump inventory，局部硬删可能反过来破坏原幸存者自身的 air-jump 能力。

### 与 ShadowBoss 的关系

ShadowBoss 是可信的重点调查路径，但目前只能标记为“可能相关”，不能直接定为根因：

1. `ub_ShadowBossManager` 对 shadow slot 调用 `ub_UnMorphThisTID`。
2. `ub_UnMorphThisTID` 执行 `UnMorphActor(w, 1)`，然后调用 `uh_MorphDemorphReset`。
3. Shadow 流程之后会再次 `MorphActorToBoss`，所以一次 shadow fakeout 包含明确的 unmorph → reset → re-morph 边界。
4. 由于 demorph reset 没有恢复 jump inventory，这条路径可能把前一个 boss 的 `AirJumpLimit` 带入幸存者中间态，再带进下一个 boss；重复 shadow morph 也可能暴露跨形态污染。

### 后续调查建议

后续任务应单独建立 morph 前后 inventory 快照，至少覆盖：

1. 无空中跳跃的幸存者 → GenericBoss → unmorph。
2. 自带 `AirJumpLimit` 的幸存者 → GenericBoss → unmorph，验证应恢复原值而非一律清零。
3. GenericBoss → ShadowBoss fakeout → 新 boss，逐阶段记录 `AirJumpLimit`、`AirJumpsUsed`、`InfiniteAirJumps`、`DisabledAirJumps`、`WallJumpLimit` 与相应 ownership flags。
4. 普通 boss morph、ShadowBoss、死亡、断线/重生等各个 unmorph 入口，确认是否都经过 `uh_MorphDemorphReset`。

修复方向应优先考虑“morph 前保存、demorph 后恢复原值”或为 morph 添加明确的 ownership marker；不要在通用 demorph 中无条件清零，因为幸存者类本身可能合法拥有 `AirJumpLimit`。本次不修改上述逻辑，也不影响 GenericBoss Flash 修复的验收结论。

## 后续验收（2026-09-10，本次）

### 报告引用解耦与代码留档

- `debug/rz_debug.acs` 的注释不再引用本报告路径，改为直接说明 probe 对象
  （`GenericBossFlashStarter_P -> GENERICBOSS_W.Flash`）。
- `GENERICBOSS_W.dec` 的 `GenericBossFlashStarter_P` 注释完整保留时序原因：
  `ActivateMorphWeapon()` 执行首个 `Ready` 零 tic 链后会无条件清空 `ps_flash`，
  所以 Flash 必须由 morph setup 的 starter 在清空之后启动；
  `uh_MorphPostReset` 会重置 `CAPROP_AirJumpZ`，starter 同时重设 30.0。
  `boss_morph_setups.acs` 有指向该注释的交叉引用。

### 真实按键空中跳跃（本次完成）

MCP bridge 无 gameplay 键位注入，但 Zandronum 控制台 `+jump`/`-jump` 可设置
`BT_JUMP`，因此完成了真实按键验收（mm8bdm-v6b-smoke，GENERICBOSS）：

1. 地面跳：`velz≈11.2`（Pawn 默认 `JumpZ`）。
2. 空中再按：`velz≈29.2`（`CAPROP_AirJumpZ = 30.0`），`AirJumpsUsed=1`，
   `UnholyBossAmmo100 100 → 0`，`DisabledAirJumps=1` + `GenericBossAirDisable_F=1`。
3. 落地后 `ReadyX` 回蓝，`ammo` 到 100 时两者成对移除。

### 死亡 / unmorph 清理（本次完成，并修复一处缺口）

- **死亡**：`DisabledAirJumps=1` + `GenericBossAirDisable_F=1` 在死亡后由
  `Deselect_ClearAir` 成对清除；外部来源的 `DisabledAirJumps`（无 flag）不受影响。
- **unmorph 缺口**：`UnMorphActor` 不会触达武器 `Deselect`，导致两库存被带到
  还原后的 Pawn（实测 `NegaMan` 仍带 `DisabledAirJumps=1`），会额外禁用幸存者空跳。
- **修复**：`systems/tools/morph_reset.acs` 新增 `UH_ClearGenericBossAirDisable()`，
  仅在 `GenericBossAirDisable_F` 存在时移除 1 层 `DisabledAirJumps` 与该 flag，
  并在 `uh_MorphPreReset` 与 `uh_MorphDemorphReset` 中调用。
- 修复后复测：unmorph 后两库存均清除；外部无 flag 的 `DisabledAirJumps` 仍保留 1。
  （已 morph 时引擎拒绝再次 morph：`Morph failed!`，所以实际路径总是先 unmorph；
  `uh_MorphPreReset` 的清理作为安全网。）

### 结论

三项原修复前置条件（解耦引用、代码留档、真机验收 + GenericBoss 自有禁跳
ownership 清理）均已完成，GenericBoss Flash/AirJump gate 问题可以关闭；关键时序
原因已固化在 `GENERICBOSS_W.dec` 代码注释中。

但本报告现在还承载上面的 `AirJumpLimit` unmorph 残留记录。在该问题转入独立 issue/
report，或完成 morph inventory save/restore 调查前，不再建议删除本报告。

## 后续修复：morph jump-inventory save/restore（2026-09-10）

按上面的修复方向实现并验证：

- `systems/tools/morph_reset.acs` 新增顶层
  `int uh_morphsavedairjump[MAX_PLAYERS]` / `int uh_morphsavedwalljump[MAX_PLAYERS]`
  （ACC 顶层 `int` 是 per-module map 变量，仅存活于当前关卡、不同步客户端；
  这里只需要服务端单次 unmorph 生命周期，无需 `world`/`global`）
  与 `UH_SaveMorphJumpInventory()` / `UH_RestoreMorphJumpInventory()`。
  - `uh_MorphPreReset` 在 `BasicBossItem` 清空之前保存每个玩家的
    `AirJumpLimit`/`WallJumpLimit`，并清 `AirJumpsUsed`/`WallJumpsUsed`。
  - `uh_MorphDemorphReset` 用 `SetInventory` 恢复原值（不是清零），并清 Used 计数。
- 通用 demorph 不做无条件清零，因此外部/职业自带的 jump inventory 会保留。

MCP 验收（mm8bdm-v6b-smoke）：

| 场景 | morph 前 | boss 形态 | unmorph 后 |
|---|---|---|---|
| 无空跳幸存者 → GENERICBOSS | Air 0 / Wall 0 | Air 1 | Air 0 / Wall 0 |
| 带空跳幸存者 → GENERICBOSS | Air 5 / Wall 7 | Air 1 | Air 5 / Wall 7 |
| Air5 → GENERICBOSS → unmorph → Misery | Air 5 | Air 1 → 9 | Air 5 / Wall 7 |
| 恢复后真机空跳 | — | — | `AirJumpsUsed=1`，正常起跳 |

结论：报告列出的 `AirJumpLimit`（及对称的 `WallJumpLimit`）unmorph 残留已修复；
"morph inventory ownership/restore" 不再是删除本报告的阻塞项。
