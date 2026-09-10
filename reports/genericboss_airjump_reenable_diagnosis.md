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

未覆盖：真实按键的空中跳跃高度与落地流程（无输入注入，属人工门）。死亡/unmorph 清理路径本次未改动。
