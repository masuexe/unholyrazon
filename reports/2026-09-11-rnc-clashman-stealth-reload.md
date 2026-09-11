# RNCClashman 隐身机制改造实施计划 — Reload 键主动隐身

- 日期：2026-09-11（v2，见下）
- 状态：**v1 已实施**（commit `a1a9b387`，用户自测基础逻辑通过）；本文档 §9 为 v2 增量变更，§1-§8 已按 v1 实测经验修订
- v1 涉及文件：`src/actors/classes/bosses/RNCClashman.dec`、`src/actors/classes/bosses/RNCClashman_W.dec`、`src/acs_source/classes/uh_classes.acs`、`src/acs_source/v6b_overrides/corescripts/utilities/footchec.acs`（加可选 tol 参数）、新增 `src/acs_source/classes/bosses/rnc_clashman.acs`
- v2 增量涉及文件：`RNCClashman_W.dec`（隐身改 AlphaPower、冷却改 Inventory）、`rnc_clashman.acs`（圆环生成/清理、冷却计时）、`hud/boss_bars.acs` 的 `DrawBar_RNCClashman_W`（冷却条）
- 不改动：`LOADACS`、`KEYCONF`、`TEAMINFO`

**v1 实施时对原计划的两处修正（已并入正文）**：
1. `Powerup.Duration` 负值在 Zandronum 语义是**秒**不是永续（`thingdef_properties.cpp`），永续应写 `Duration 0`（`APowerup::Tick` 只在 EffectTics>0 时倒数）。原计划的 `-1` 是 bug。
2. 原计划的 `FixedMul(r, r)` 定点平方在 r=256 时溢出 32 位（256²=65536=0x10000，<<16 超出符号位），圆判定改用整数单位比较：`dx = (x-cx)>>16` 后 `dx*dx + dy*dy > 256²`（≤65536，int 安全）。

## 1. 现状（v1 实施前）

`RNCClashman.dec` 目前是"走路自动隐身"：`See:` 状态逐帧 `A_SetShadow`（走路时进入 SHADOW 半透明 0.5），`Spawn:`/`Missile:`/`ClassPain:` 用 `A_ClearShadow` 显形。该行为继承自 Unholy v7b pb1（参考包 `unholy_bosses_unbound_v7b_pb1/actors/MainBoss/RNCClashman.txt:502`），无任何主动按键参与，隐身/显形完全由移动与开火状态被动驱动。

`A_SetShadow`/`A_ClearShadow` 是 Strife 遗留指针（引擎 `g_strife/a_strifestuff.cpp:437-450`）：设置/清除 `+SHADOW`、RenderStyle Translucent、alpha 0.5。

## 2. 需求

用户原案 + 2026-09-11 拍板结果：

| 项目 | 决定 |
|------|------|
| 触发方式 | 删除 See/Spawn/Missile/ClassPain 的自动 SetShadow/ClearShadow，改由武器 `Reload:` 状态触发 |
| 判定圈 | 激活瞬间以当时玩家 XY 为圆心（快照，不跟随），`floorz` 为 z，半径 **r = 256** 地图单位；v1 纯逻辑判定，v2 加可见圆环边界（§9.2） |
| 破隐条件 A | 玩家 XY 距圆心超过 r（出圆），从激活瞬间起即生效，不考虑 z |
| 破隐条件 B | 玩家在空中（`z - floorz` 大于容差）。**空中激活例外**：激活时在空中则立即隐身，此条件在首次落地后才"武装"；落地后再离地（跳跃、坠落、被击飞均算）即破隐 |
| 消耗/冷却 | 无弹药消耗；破隐后 **5 秒冷却**（175 tics，调参入口见 §4.4 常量）；v2 在 `DrawBar_RNCClashman_W` 显示冷却余量（§9.3） |
| 开火 | Fire / AltFire 立即破隐（然后正常执行攻击） |
| 隐身期间加成 | **无敌**（`core_invulnerableplayer`，APROP_Invulnerable 栈）+ **unsolid**（`core_unsolidplayer`，不可阻挡/不可选中） |
| 视觉 | **完全隐身**；v1 用 PowerInvisibility，v2 改 mod 统一通道 `UH_00_AlphaPowerGiver`（APROP_Alpha=0，队友/观战者 0.25 下限，§9.1） |
| 隐身中再按 Reload | 无效果（不改圆心、不取消） |
| 时长上限 | 无，直到破隐条件触发或死亡 |

## 3. 技术依据（已对源码核实）

1. **Reload 键 → 武器状态**：引擎在 `WF_WEAPONRELOADOK` 置位且玩家按住 `BT_RELOAD`（=64）时调用 `P_ReloadWeapon` 跳入武器 `Reload:` 状态（`zandronum-stable-branch-default/src/p_pspr.cpp:1002-1014`）。`P_ReloadWeapon` 无 `Reload:` 状态时不跳转（同文件 :439-462）。
2. **WRF_ALLOWRELOAD 必须显式传**：`A_WeaponReady` 仅在参数含 `WRF_AllowReload`(16) 时调用 `DoReadyWeaponToReload` 置位 `WF_WEAPONRELOADOK`（`p_pspr.cpp:872,915`）。裸 `A_WeaponReady`（参数 0）**不**启用。标志在状态切换时被清（:210），随后被 Ready 循环重新置位——2-tic Ready 循环下等效每刻检测，不会漏按。
3. **本 mod 先例**：DLCCentaurman 4.0 的"Reload 维度跳跃"即此模式（`DLCCentaurman_W.dec:50` 的 `Reload:` 状态 + `:261-288` 的 `_Ready*_P` 在弹药充足时调 `A_WeaponReady(WRF_ALLOWRELOAD)`）。RNCClashman 无弹药门槛，可直接在武器 Ready 循环里加 flag，不需要 CustomInventory 中转。
4. **完全隐身（v2 改用 DTADD AlphaPower）**：mod 的统一隐身通道是 `UH_00_AlphaPowerGiver`/`UH_00_AlphaPower`（注册于 `uh_aprop.acs:311`，`DefinePowerAprop(..., APROP_Alpha, 0.0, NO)`），底层为 v6b DTADD 的 PowerAprop 系统（v6b `corescripts/api handlers/PUAPROP.acs:65-117`）：Giver 是 AUTOACTIVATE CustomInventory，激活时同步把 `APROP_Alpha × factor(0.0)` 应用到玩家；`core_clampalpha_client`（:148-160）附带**队友/观战者最低 0.25 可见度**（`ALPHA_MIN`）——同队玩家和观战者始终能看到 25% 轮廓，敌对玩家看到全透明。`A_TakeInventory("UH_00_AlphaPower")` 后系统的 watcher 自动恢复默认 alpha，且多 alpha 来源（GhostEye、Hellbot 等）叠加时撤销逻辑正确重算，不会互相踩踏。mod 先例：CXAirman、GBeast、BlueSpeciman（boss）、Kate（survivor）、ShadowPunch（copy weapon）。v1 用 `PowerInvisibility`（`a_artifacts.cpp:635-636,669-698`，Strength 100 → alpha 0）功能等价但不走 mod 统一系统，v2 换成 AlphaPower。
5. **无敌**：v6b 核心脚本 `core_invulnerableplayer`（v6b `acs_source/corescripts/utilities/PROPUTIL.acs:211-226`）——`toggle=true` 给 `PlayerPropertyInvulnerable` 标记（可叠加）并置 `APROP_Invulnerable`；`false` 弹一层，栈清零才解除属性。直接设 APROP，**没有** PowerInvulnerable 的 colormap 滤镜问题。栈语义与出生保护（SPWNPROT）等其他无敌来源正确叠加；mod 在 DECORATE 侧直接调用的先例：`UnholyInsurance.dec:63`、`InvincibleCandy.dec:67`。注意（mod 内 `clownpiece_spellcard.acs:123` 已注明）：`false` 只弹一层，这是栈的既定语义而非缺陷。
6. **unsolid**：v6b 核心脚本 `core_unsolidplayer`（v6b `acs_source/corescripts/utilities/PROPUTIL.acs:632-663`）。`USP_TOGGLEON` 给 `PlayerPropertyUnsolid` 标记；`USP_TOGGLEOFF_DAMAGE` 恢复固体，若恢复时与其他 actor 重叠则扣 `damage` 血（mod 惯例传 `core_getmaxhealth()/10`）。`USP_*` 常量在 DECORATE 中可用（v6b `actors/acspropconstants.txt:59` 起，`const int` 声明）——Balrog/EyelentoMajor/ShadowMan 等 boss 均直接在 DECORATE 里这样调用。
7. **冷却 token（v2 改为可读余量的 Inventory + ACS 计时）**：v1 的自过期 `Powerup` 无法从 DECORATE/ACS 读取剩余时间（Zandronum 无 GetPowerupTicsLeft），冷却条需要余量。改为 mod 惯例：普通 `Inventory { maxamount 175 }`，破隐时给满 175，由每刻 `A_TakeInventory(...,1)` 的计时脚本递减（Balrog 先例 `Balrog_Cooldown : Inventory` + Flash 状态递减，`Balrog_W.dec:397,48`；`TorontoCalifornia` 的cloak冷却 `The_Cloak_From_Harry_Potter` 同款）。守卫 `A_JumpIfInventory` 对 amount 语义不变。
8. **空中判定**：`GetActorZ(0) - GetActorFloorZ(0)`，mod 先例 `motion_helpers.acs:50`。
9. **圆判定**：定点数平方距离比较，无需开方：`FixedMul(dx,dx)+FixedMul(dy,dy) > FixedMul(r,r)`。
10. **存活检测**：Zandronum ACC 无 `ActivatorIsAlive`，用 `GetActorProperty(0, APROP_Health) > 0`（mod 先例 `shared_movement.acs:8`）。
11. **着地判定**：用核心脚本 `core_CheckFooting`（本 mod 的 UH override：`v6b_overrides/corescripts/utilities/footchec.acs:29`）。语义：`z-floorz==0`，或在脚下 1 单位处 Spawn 探针 `8bdmFootholdCheck` 失败（被地面挡住）→ 着地；否则 airborne。选它而非裸 `z-floorz` 的理由：a) mod 权威着地判定（`uh-BasePain.dec:122`、`eden_runtime.acs:146` 等在用）；b) UH override 内含 `CheckCeilingFootingFunc`——本 mod 存在反重力来源（GravityHold、Kamilia `CeilingFlag`），玩家贴天花板行走时裸 z-floorz 会误判空中而误破隐，`core_CheckFooting` 正确处理。每次调用含一次 Spawn+Remove，每刻一次×单个 boss，开销可忽略。
12. **着地容差参数（UH 扩展 core_CheckFooting）**：给 override 版 `core_CheckFooting` 加可选参数 `tol`——`tol=0` 走现有逻辑（位不变）；`tol>0` 时额外把 `z - floorz <= tol` 判为着地（正常重力），反重力分支对称放宽为 `ceilingz - z <= 58 + tol`。数值依据：下楼梯时玩家离脚下 floorz 至多一级台阶高（典型 8~32），而 jumpz 14 的跳跃顶点 = 14²/2 = **98 单位**（Zandronum 每刻重力恒 1.0 u/tic²），tol=32 即可让全部楼梯场景不离地、跳跃照常破隐。**兼容性已核实**：Zandronum ACS 命名脚本少传参时缺省读 0（v6b 核心自身先例：`core_unsolidplayer` 声明 3 参、DECORATE 只传 2 参，`damage` 读 0 走默认分支），故 mod 源码、v6b 编译库、DECORATE `CallACS("core_CheckFooting")` 等现存零参调用全部落到 tol=0 旧行为，无需改动。**实现要点**：tol>0 分支用 floorz 比较而非把探针 Spawn 到 `z-tol`——探针 actor 有半径，贴墙跳跃时深探针会撞墙误报着地，且 floorz 已正确处理 3D floor。
13. **冷却条（SetOverlayBar / BARFLS1）**：BARLIB 的 `SetOverlayBar(owned, capacity)` 写 `SBARFlashOverlayAmmo`，SBARINFO 把它画成 ammo bar 上的闪烁 overlay（H 布局用 VARFLS1、V 布局用 BARFLS1 图形；`v6b_overrides/_includes/mod_api/barlib.acs:2-4`）。boss bar + 生成选择器 + SetOverlayBar 组合的现成先例：Misery（`boss_bars.acs:174-183`，`Misery_DrawBar(UHBAR_*)` 与 `SetOverlayBar` 并存）、TorontoCalifornia 的 cloak 冷却（`:197`，`SetOverlayBar(CheckInventory("The_Cloak_From_Harry_Potter"), 200)` 无条件显示）。若要落在 CustSbarPos1 自定义条坐标上，备选走目录 slot：`SBARINFO.v.uhappend:83` 的 slot 77 即 `BARFLS1` 样式（`DrawCustomBar1(76, amount, capacity)`，slot+1=77）——实施时在游戏内确认哪个位置正确。
14. **圆边界可视化的硬约束**：Zandronum 3.x **不支持 `+FLATSPRITE`**（引擎源码无此 flag，GZDoom 特性），"单张贴图平躺地面"方案不可行；可行方案是**圆周标记点环**（N 个小 actor 等角分布）。可见范围：Zandronum 世界 actor 无按玩家过滤的可见性（服务端 authoritative 复制），clientside 脚本 Spawn 不在支持范围、易出视觉问题——**"仅自己可见"实际不可实现**，圆环必然全场可见（这不必然是坏事，见 §9.2 的取舍分析）。

## 4. 设计

### 4.1 判定规则精确语义

- 激活：`Reload:` 状态 → 给 `RNCStealthBegin_P`。守卫：已隐身（`RNCStealthActive_F` 在身）或冷却中（`RNCStealthCooldown` 在身）则静默拒绝。
- 激活瞬间快照圆心 `(cx, cy) = 当前玩家 XY`；`landed := core_CheckFooting(TOL)`（空中激活则为 false，空中判定未武装）。
- 每刻（ACS `Delay(1)` 循环）按序检查：
  1. 玩家死亡 → 退出循环（清理交给 `ClassDeath`）。
  2. `dx²+dy² > r²` → 破隐（此检查从激活起就生效，含空中激活期间）。
  3. `core_CheckFooting(32)` 为真（着地或在容差内）→ `landed := true` 并清零滞空计数；否则若 `landed` 且连续滞空超过 `RNCSTEALTH_AIR_DEBOUNCE`(4) tics → 破隐（容差覆盖楼梯，debounce 仅兜底奇异地形，见 §5.1）。
  4. 标记 `RNCStealthActive_F` 已不在（其他路径已破隐）→ 循环自然退出。
- 破隐 = 给 `RNCStealthBreak_P`（幂等）：取走隐身 Power 与标记 → `core_invulnerableplayer` false（弹无敌栈）→ `core_unsolidplayer` OFF（DAMAGE，`maxhealth/10`）→ 给 5 秒冷却 token。
- Fire/AltFire 顶部检查 `RNCStealthActive_F`，命中则先给 `RNCStealthBreak_P` 再继续原攻击流程。
- 死亡：`ClassDeath` 给 `RNCStealthBreak_P`（幂等；此时无敌已无法挽救，仅保证 unsolid 复原）。
- 出生：`Spawn` 首帧补一发 `core_unsolidplayer OFF NONE`（无惩罚、幂等），兜底回合重置时 unsolid 残留。

### 4.2 新增 actor（放在 `RNCClashman_W.dec` 底部）

```decorate
// 完全隐身：Strength 100 → alpha 0；Duration -1 无限，由 RNCStealthBreak_P 显式取走
// 不要 +CANTSEEK（破坏追踪武器，Power_ShadMan 注释先例）
actor Power_RNCStealth : PowerInvisibility
{
    Powerup.Strength 100
    Powerup.Mode "Translucent"
    Powerup.Duration -1
}

// 隐身期间无敌：core_invulnerableplayer 直接置 APROP_Invulnerable（栈式，见 §3.5）

actor RNCStealthActive_F : Inventory { inventory.maxamount 1 }

// 自过期冷却 token：5 秒 = 175 tics（与 rnc_clashman.acs 的 RNCSTEALTH_COOLDOWN 保持同步）
actor RNCStealthCooldown : Powerup { powerup.duration 175 }

actor RNCStealthBegin_P : CustomInventory
{
    States
    {
    Pickup:
        TNT1 A 0 A_JumpIfInventory("RNCStealthActive_F", 1, "Stop")
        TNT1 A 0 A_JumpIfInventory("RNCStealthCooldown", 1, "Stop")
        TNT1 A 0 A_GiveInventory("Power_RNCStealth")
        TNT1 A 0 ACS_NamedExecuteWithResult("core_invulnerableplayer", 0, true)
        TNT1 A 0 ACS_NamedExecuteWithResult("core_unsolidplayer", 0, USP_TOGGLEON)
        TNT1 A 0 A_GiveInventory("RNCStealthActive_F")
        TNT1 A 0 ACS_NamedExecuteAlways("uh_rncstealth_monitor", 0)
    Stop:
        TNT1 A 0
        stop
    }
}

// 幂等：仅在 RNCStealthActive_F 在身时执行
actor RNCStealthBreak_P : CustomInventory
{
    States
    {
    Pickup:
        TNT1 A 0 A_JumpIfInventory("RNCStealthActive_F", 1, 1)
        TNT1 A 0
        stop
        TNT1 A 0 A_TakeInventory("RNCStealthActive_F")
        TNT1 A 0 A_TakeInventory("Power_RNCStealth")
        TNT1 A 0 ACS_NamedExecuteWithResult("core_invulnerableplayer", 0, false)
        TNT1 A 0 ACS_NamedExecuteWithResult("core_unsolidplayer", 0, USP_TOGGLEOFF_DAMAGE, CallACS("core_getmaxhealth")/10)
        TNT1 A 0 A_GiveInventory("RNCStealthCooldown")
        stop
    }
}
```

### 4.3 修改点

**`RNCClashman.dec`**（对照 §1 现状，四处 A_SetShadow/A_ClearShadow 全部移除）：

```decorate
Spawn:
8A17 A 0 ACS_NamedExecuteWithResult("core_unsolidplayer", 0, USP_TOGGLEOFF_NONE)
8A17 B 1
8A17 A 1
Goto Spawn+2
See:
8A17 BCDE 5          // 原 A_SetShadow 删除
Goto Spawn
Missile:
8A17 F 5             // 原 A_ClearShadow 删除（开火破隐由武器侧处理）
8A17 G 4
goto Spawn+2
ClassPain:
8A17 H 0             // 原 A_ClearShadow 删除（隐身期间无敌，无疼痛）
Goto MegamanPain
ClassDeath:
8A17 H 0 A_GiveInventory("RNCStealthBreak_P")
Goto MegamanDeath
```

注意：See/Spawn 状态在隐身期间照常循环，必须删净 A_SetShadow/A_ClearShadow，否则会与 `PowerInvisibility` 的每刻 alpha 刷新互相打架（flag 只在 InitEffect 设置，被 A_ClearShadow 强清后不会自动恢复）。

**`RNCClashman_W.dec`**：

1. Ready 循环启用 reload 检测（裸调用不启用，见 §3.2）：
   - `ReadyX:` 的 `A_WeaponReady(WRF_NOSECONDARY)` → `A_WeaponReady(WRF_NOSECONDARY|WRF_ALLOWRELOAD)`
   - `ReadyX2:` 的 `A_WeaponReady` → `A_WeaponReady(WRF_ALLOWRELOAD)`
   - Fire 恢复段的 `A_WeaponReady(14)` 不动（reload 只需在 Ready 可用）。
2. 新增 `Reload:` 状态（放在 ReadyX2 之后、Fire 之前，与 DLCCentaurman 排布一致）：

```decorate
Reload:
8H17 A 0 A_GiveInventory("RNCStealthBegin_P")
goto ReadyX
```

3. Fire / AltFire 顶部插破隐检查（原逻辑不动，仅插入首行与续接标签）：

```decorate
Fire:
8H17 A 0 A_JumpIfInventory("RNCStealthActive_F", 1, "FireStealthBreak")
FireNormal:
8H17 A 0 A_JumpIfInventory("UnholyPower3000",3000,"RapistShot")
...（原 Fire 主体不变）
FireStealthBreak:
8H17 A 0 A_GiveInventory("RNCStealthBreak_P")
goto FireNormal

AltFire:
8H17 A 0 A_JumpIfInventory("RNCStealthActive_F", 1, "AltFireStealthBreak")
8H17 A 0 A_JumpIfInventory("UnholyBossAmmo150",150,"PowerFapping")
Goto ReadyX
AltFireStealthBreak:
8H17 A 0 A_GiveInventory("RNCStealthBreak_P")
8H17 A 0 A_JumpIfInventory("UnholyBossAmmo150",150,"PowerFapping")
Goto ReadyX
```

RapistShot 分支经由 `FireNormal` 顶部检查覆盖，无需单独处理。

**新增 `src/acs_source/classes/bosses/rnc_clashman.acs`**，并在 `src/acs_source/classes/uh_classes.acs` 的 include 列表（`bosses/pharaoh_mmsf.acs` 之后）加一行 `#include "bosses/rnc_clashman.acs"`。

### 4.4 监控脚本（完整实现）

```acs
// RNCClashman reload 主动隐身监控。
// 由 RNCStealthBegin_P 以玩家为 activator 启动；RNCStealthActive_F 消失即退出。

#define RNCSTEALTH_RADIUS 256    // 判定圈半径，地图单位（2026-09-11 用户拍板）
#define RNCSTEALTH_FOOTING_TOL 32  // core_CheckFooting 容差：≤ 一级台阶高，≪ 跳跃顶点 98（见 §3.12/§5.1）
#define RNCSTEALTH_AIR_DEBOUNCE 4  // 连续 airborne 超过此 tics 数才破隐（楼梯已由 TOL 覆盖，仅兜底奇异地形）
#define RNCSTEALTH_COOLDOWN 175  // 5 秒 @35tics；须与 RNCStealthCooldown 的 powerup.duration 同步

script "uh_rncstealth_monitor" (void)
{
    int cx = GetActorX(0);
    int cy = GetActorY(0);
    int rr = FixedMul(RNCSTEALTH_RADIUS << 16, RNCSTEALTH_RADIUS << 16);
    bool landed = ACS_NamedExecuteWithResult("core_CheckFooting", RNCSTEALTH_FOOTING_TOL);  // 空中激活例外
    int airtics = 0;

    while (CheckInventory("RNCStealthActive_F"))
    {
        if (GetActorProperty(0, APROP_Health) <= 0)
            terminate;  // ClassDeath 负责 RNCStealthBreak_P 清理
        int dx = GetActorX(0) - cx;
        int dy = GetActorY(0) - cy;
        if (FixedMul(dx, dx) + FixedMul(dy, dy) > rr)
            break;  // 出圆
        if (ACS_NamedExecuteWithResult("core_CheckFooting", RNCSTEALTH_FOOTING_TOL))
        {
            landed = true;      // 落地一次后空中判定武装
            airtics = 0;
        }
        else if (landed)
        {
            airtics++;
            if (airtics > RNCSTEALTH_AIR_DEBOUNCE)
                break;          // 持续滞空超容差+阈值：跳/坠/被击飞
        }
        Delay(1);
    }
    // 循环退出但标记仍在 → 是本脚本检出的破隐；其他路径破隐时标记已消失，此处跳过
    if (CheckInventory("RNCStealthActive_F"))
        GiveInventory("RNCStealthBreak_P", 1);
}
```

依赖：仅 zcommon（经 `uh_classes.acs` 头部）。`USP_*`、`core_*` 均在 DECORATE 侧调用（v6b acspropconstants / 核心库提供），本片段不新增 ACS 依赖；`uh_classes` 已在 LOADACS，无需改动。

**前置改动：`src/acs_source/v6b_overrides/corescripts/utilities/footchec.acs`**（UH override 文件，按文件头约定用 `//$UH` 标记改动；向后兼容依据见 §3.12）：

```acs
script "core_CheckFooting" (int tol) {  //$UH 可选容差：0 = v6b 原行为
	SetResultValue(CheckFootingFunc(tol));
}
// core_CheckFooting_ThruPlayer 保持 (void) 不变，内部调 CheckFootingFunc_ThruPlayer(0)

function bool CheckFootingFunc(int tol) {  //$UH
	if (CheckInvertedFooting()) return CheckCeilingFootingFunc("8bdmFootholdCheck", tol);

	int z = GetActorZ(0);
	if (z-GetActorFloorZ(0)==0.0) return true;
	if (tol > 0) return (z - GetActorFloorZ(0) <= tol << 16);  //$UH 容差用 floorz 比较，勿用深探针（贴墙误报）
	if (!SpawnFootingFunc("8bdmFootholdCheck", GetActorX(0), GetActorY(0), z-1.0)) return true;
	return false;
}

function bool CheckCeilingFootingFunc(str footingactor, int tol) {  //$UH 反重力分支对称放宽
	int z = GetActorZ(0);
	if (CheckInventory("OnCeilingFlag")) return true;
	if (GetActorCeilingZ(0) - z <= 58.0 + (tol << 16)) return true;
	if (!SpawnFootingFunc(footingactor, GetActorX(0), GetActorY(0), z + GetActorProperty(0, APROP_Height))) return true;
	return false;
}
```

（`CheckFootingFunc_ThruPlayer` 同步加 `int tol` 形参、`core_CheckFooting_ThruPlayer` 传 0，或保持原样调用 `CheckFootingFunc(0)`——实现时取改动最小的一种。）

**决策记录（2026-09-11）：就地 override 而非另写带参脚本。** 理由：a) 本文件的既有惯例就是就地改（反重力支持当年即直接修改 `CheckFootingFunc` 内部而非另立平行脚本），可选参数缺省位不变，侵入性更小；b) 反重力判定（`CheckInvertedFooting`/`CheckCeilingFootingFunc`）是库内私有 function，外部脚本无法复用、只能复制，孪生副本会随语义演进静默漂移，重新引入贴天花板误破隐类 bug；c) 单一着地判定 API，其他职业可直接复用 tol；d) v6c 迁移的 diff 量级两种方案相同。

## 5. 边界情况与已知取舍

1. **下楼梯（已由容差根治）**：着地判定 `core_CheckFooting(tol=32)`——下楼梯时玩家离脚下 floorz 至多一级台阶高（典型 8~32 单位），tol=32 让全部楼梯场景（含全速冲刺逐级连续滞空）始终判着地；debounce 降为 4 仅兜底奇异地形。跳跃（jumpz 14，顶点 98 单位）在离地约 3-4 tics 即超容差、约 8 tics 破隐；坠落超过 32 单位的崖边/台阶同样破隐。**语义代价**：≤32 单位的落差（小台阶、矮沿）不再视为"空中"——离地但仍在容差内不破隐。数值均可在 §4.4 常量处调。备选方案（若想连坠落也豁免）："仅 velz>0 判空中"——与"坠落也破隐"的原设计冲突，需用户拍板，本期不做。
2. **被动坠落/被击飞同样算空中**（武装后，滞空超过 debounce）。符合"离地即破隐"的语义。
3. **反重力（GravityHold/Kamilia）贴天花板行走不误破隐**：`core_CheckFooting` 的 UH override 经 `CheckCeilingFootingFunc` 正确判着地（裸 z-floorz 会误判）。
4. **空中激活期间出圆立即破隐**：圆判定不等落地，也不受 debounce 影响。
5. **Resolid 惩罚**：破隐时若与其他玩家重叠，按 mod 惯例扣 `maxhealth/10`（2500 血 → 250）。`RNCStealthBreak_P` 的弹无敌栈在 unsolid-off 之前，正常情况无敌已解除、惩罚生效；若其他来源（如出生保护）仍持有无敌栈则惩罚被挡——玩家确实还无敌，属栈语义的正确行为。不想要惩罚可改传 `USP_TOGGLEOFF_NONE`。
6. **Bots 不会按 reload**：与 DLCCentaurman reload 跳跃同等现状；boss 交给真人时技能生效。需要 bot 支持须另加 AI 钩子，本期不做。
7. **Reload 仅在武器 Ready 可触发**（Fire 动画中按键无效）——引擎 `WF_WEAPONRELOADOK` 机制如此。
8. **冷却双处定义**：`RNCSTEALTH_COOLDOWN`（ACS，当前仅作文档锚点）与 `RNCStealthCooldown.powerup.duration`（DECORATE，实际生效）。调整冷却改 DECORATE 处，ACS 常量同步改。
9. **完全隐身仍存在于记分板/小地图**（引擎层面）；`CANTSEEK` 不加，追踪武器仍可锁定（见 §3.4）。
10. **多次激活/多实例监控**：`Begin_P` 守卫 + 标记条件循环，天然防重入；`Break_P` 幂等，监控与 Fire 同刻竞争破隐安全。
11. **回合结束未死亡**：标记随重置清空，循环退出；`Spawn` 首帧的 unsolid-off 兜底复原固体。

## 6. 测试计划

构建：`src/` 打包为 `out/build.pk3`（ZIP，无构建工具），先跑 `./tools/validate-build-pk3.sh`。

MCP 冒烟（profile `mm8bdm-v6b-smoke`，`playerclass RNCClashman` 后重载地图）：

1. **激活**：`run_command("give RNCStealthBegin_P")`（控制台无法注入按键，Reload: 状态链按代码审查 + 手测；技能逻辑全走 Begin_P，与按键路径等价）→ `actor_state` 确认 `Power_RNCStealth`、`RNCStealthActive_F`、`PlayerPropertyInvulnerable`、`PlayerPropertyUnsolid` 在 inventory，alpha=0，且受到攻击不掉血（无敌生效）。
2. **出圆**：`run_command("puke ...")` 或移动 >256 单位后 → 三项消失、`RNCStealthCooldown` 出现、实体恢复。
3. **空中激活例外**：跳跃中给 Begin_P → 仍隐身；落地（`step` 推进）→ 再 `summon` 弹起/再次跳跃 → 破隐。
4. **下楼梯**：隐身状态下正常速度与全速跑下台阶/长楼梯 → 均不破隐；跳一次 → 数 tics 内破隐；走下超过 32 单位的崖/落差 → 破隐。
5. **反重力**：隐身状态下被 GravityHold 翻转 → 贴天花板行走不误破隐；翻转中向地面跳（离开天花板）→ 破隐。
6. **core_CheckFooting 兼容回归**：tol 参数落地后，验证既有调用方不受影响——受击落地判定（uh-BasePain 的 Grounded 分支）、Eden（eden_runtime）、DECORATE `CallACS("core_CheckFooting")`（ShadowMan 台阶尘土）行为与改动前一致（均走 tol=0 路径）。
6. **开火破隐**：隐身中 `step` 少量 + 触发 Fire（give `ClashingBombBoss_P` 或手测开火）→ 立即显形并正常射出。
7. **冷却**：破隐后立刻 give Begin_P → 无效果；`step 175+` 后 give → 生效。
8. **死亡清理**：隐身中杀死玩家（`run_command("damage ...")` 或 summon 敌人）→ 复活后 alpha 正常、可被推动（unsolid 已复原）。
9. **对局冒烟**：`./tools/mcp/smoke-test.sh --profile mm8bdm-v6b-full`。

## 7. 验收标准

- [ ] 走路/站立/受击不再自动隐身（原 A_SetShadow/A_ClearShadow 全部移除）
- [ ] 按 Reload 立即完全隐身 + 无敌（APROP，无任何滤镜）+ unsolid
- [ ] 出圆（256）立即破隐；冷却 5 秒内无法再次隐身
- [ ] 空中激活：立即隐身；落地后再离地（滞空超过 debounce）破隐；空中期间出圆也立即破隐
- [ ] 正常速度与全速走下楼梯均不破隐；跳跃/大落差坠落/被击飞破隐
- [ ] core_CheckFooting 加 tol 参数后，全部既有调用方行为不变（tol=0 路径）
- [ ] 被反重力翻转贴天花板行走不误破隐
- [ ] Fire/AltFire 立即破隐且攻击正常执行
- [ ] 死亡/回合重置后无状态残留（显形、实体、无幽灵冷却外的 token）
- [ ] 服务端无 ACS/DECORATE 报错（`get_startup_errors`、引擎日志干净）
- [ ] bots 局内不报错（不使用该技能即可）

## 8. 明确不做（后续可选）

- 破隐/隐身**音效**（HUD 冷却显示与圆环 FX 已列入 v2 §9）
- Bots 使用该技能的 AI 钩子
- "仅 velz>0 判空中"语义（彻底豁免楼梯与坠落，见 §5.1 备选 b，需用户拍板）

---

## 执行结果（2026-09-11）

### 已实现

- `footchec.acs`：`core_CheckFooting` 加可选 `int tol`（缺省 0），
  `CheckFootingFunc(tol)` / `CheckCeilingFootingFunc(footingactor, tol)`；
  `core_CheckFooting_ThruPlayer` 保持 `(void)`，内部传 0（改动最小）。
- 新增 `classes/bosses/rnc_clashman.acs`（`uh_rncstealth_monitor`），并加入
  `uh_classes.acs` include 列表。
- `RNCClashman.dec`：移除 See/Spawn/Missile/ClassPain 的
  `A_SetShadow`/`A_ClearShadow`；Spawn 首帧 `core_unsolidplayer OFF NONE`；
  ClassDeath 给 `RNCStealthBreak_P`。
- `RNCClashman_W.dec`：ReadyX/ReadyX2 加 `WRF_ALLOWRELOAD`；新增 `Reload:`；
  Fire/AltFire 顶部插入破隐检查；底部新增 `Power_RNCStealth` /
  `RNCStealthActive_F` / `RNCStealthCooldown` / `RNCStealthBegin_P` /
  `RNCStealthBreak_P`。

### 与计划的必要偏差（运行期发现）

1. **`Stop:` / `Break:` 是保留 state label**：`Stop:` 会触发 DECORATE 解析器
   崩溃（`LoadActors` SIGSEGV）。已改名 `NoOp:` / `BreakStealth:`。
2. **圆判定公式溢出**：计划的
   `FixedMul(dx,dx)+FixedMul(dy,dy) > FixedMul(r,r)` 在 16.16 定点下
   `256²` 超 32 位，`rr` 溢出为 0，任何移动都会破隐（实测 144 单位即破）。
   改为整数地图单位比较：`dx=(GetActorX-cx)>>16`，
   `dx*dx+dy*dy > RNCSTEALTH_RADIUS*RNCSTEALTH_RADIUS`。
3. **`Powerup.Duration -1` 不是无限**：Zandronum
   `thingdef_properties.cpp` 把负数解释为秒（`-i*TICRATE`），`-1` = 35 tics，
   隐身 1 秒后自动消失。改用 `Powerup.Duration 0`（`APowerup::Tick` 只在
   `EffectTics > 0` 时递减，0 = 永不失效），由 `RNCStealthBreak_P` 显式移除。

### MCP 验收（mm8bdm-v6b-smoke）

| 项 | 结果 |
|---|---|
| 激活（Begin_P） | alpha=0，`Power_RNCStealth`/`PlayerPropertyInvulnerable`/`PlayerPropertyUnsolid` 全在；`damage 1000` 不掉血 |
| 隐身持续 | 60+ tics 后仍 alpha=0（`Duration 0` 生效） |
| 出圆 | 距离 119 保持隐身；300 时破隐，冷却出现、alpha=1、invuln/unsolid 解除 |
| 冷却 | 冷却中 give Begin_P 无效；180 tics 后 cd=0，再 give 生效 |
| 空中激活例外 | 空中 give Begin_P → active=1、alpha=0；落地后武装 |
| 空中破隐 | 激活后起跳，约 5 个滞空 tic 后破隐 + 冷却 |
| 开火破隐 | `+attack` 立即 active=0、cd=1、alpha=1 |
| 死亡清理 | 死亡后 active/power/invuln/unsolid 归零、alpha=1 |
| `core_CheckFooting` 兼容 | tol 缺省 0，既有调用路径不变；全库编译 0 失败 |
| 启动 | `get_startup_errors` 无编译/致命错误；`smoke-test.sh --profile mm8bdm-v6b-full` status=ok、reportedLines=0 |

### 未覆盖 / 观察

- Bots 不按 reload（如计划 §5.6，未做 AI 钩子）。
- reload 按键路径本身未注入（MCP 无 gameplay 输入）；技能逻辑全走
  `RNCStealthBegin_P`，与按键等价，按键链按代码审查（`Reload:` +
  `WRF_ALLOWRELOAD`）。
- 调试中发现从近墙点开火会自伤；与本特性无关，未处理。

---

## 9. v2 增量变更（2026-09-11 第二轮，基于 v1 实测反馈）

用户自测通过基础逻辑后提出三项变更：隐身换用 mod 统一 AlphaPower 通道、
判定圈可视化、冷却在 boss bar 上显示。

### 9.1 隐身改用 `UH_00_AlphaPower(Giver)`

依据见 §3.4（DTADD PowerAprop 系统）。改动：

- 删除 `Power_RNCStealth` actor。
- `RNCStealthBegin_P`：`A_GiveInventory("Power_RNCStealth")` →
  `A_GiveInventory("UH_00_AlphaPowerGiver")`（AUTOACTIVATE，激活链同步把
  alpha 置 0；先例 `CXAirman_W.dec:180`）。
- `RNCStealthBreak_P`：`A_TakeInventory("Power_RNCStealth")` →
  `A_TakeInventory("UH_00_AlphaPower")`（DTADD watcher 自动恢复默认 alpha，
  且与其他 alpha 来源叠加时正确重算；先例 `CXAirman_W.dec:212`）。

**语义变化**（相对 v1 的 PowerInvisibility）：`core_clampalpha_client` 的
`ALPHA_MIN=0.25` 下限——**队友与观战者始终可见 25% 轮廓**，敌对玩家全透明。
与 mod 全体隐身职业（CXAirman/GBeast/Kate/BlueSpeciman/ShadowPunch）行为一致。
Unholy LMS 中 boss 独占 Bosses 队 → 幸存者（敌对）看到全透明，符合"完全隐身"
需求；观战者能看到微弱轮廓属可接受甚至有利（观战体验）。

### 9.2 判定圈可视化（圆环标记点）

硬约束见 §3.14（无 FLATSPRITE → 标记点环；无按玩家过滤的世界 actor 可见性）。
**新发现的引擎能力使"仅自己可见"成为可行方案**：
`ACS_NamedExecuteClientScript(script, client, args...)`（ACC `zspecial.acs:431`
`-145`；引擎 `p_acs.cpp:1758-1806`）允许**服务端脚本对单个指定客户端**执行
CLIENTSIDE 脚本（`SVCF_ONLYTHISCLIENT`）；CLIENTSIDE 脚本内 `Spawn` 的 actor
自动标记 `NETFL_CLIENTSIDEONLY`（`p_acs.cpp:4209-4212`）——纯本地、不广播、
其他客户端无此 actor。单机模式直接本地执行（`p_acs.cpp:1766-1771`）。

**方案 A（推荐）：仅 boss 自己可见。**

- `RNCStealthBegin_P` 末尾：
  `ACS_NamedExecuteClientScript("uh_rncstealth_ring", PlayerNumber(), cx, cy)`
  ——实际由 monitor 启动更顺（monitor 已持有 cx/cy）：monitor 首刻发一次。
- 新增 CLIENTSIDE 脚本（`rnc_clashman.acs`）：

```acs
#define RNCSTEALTH_RING_TID 3970   // 32 个点：3970-4001；实施前对 eden_tid_reserve.acs 确认无冲突
#define RNCSTEALTH_RING_DOTS 32

script "uh_rncstealth_ring" (int cx, int cy) clientside
{
    int cz = GetActorFloorZ(0);          // activator = boss 玩家（ExecuteClientScript 透传）
    for (int i = 0; i < RNCSTEALTH_RING_DOTS; i++) {
        int ang = i * (1.0 / RNCSTEALTH_RING_DOTS);
        Spawn("RNCStealthRingDot",
              cx + FixedMul(RNCSTEALTH_RADIUS << 16, cos(ang)),
              cy + FixedMul(RNCSTEALTH_RADIUS << 16, sin(ang)),
              cz + 8.0, RNCSTEALTH_RING_TID + i);
    }
    while (CheckInventory("RNCStealthActive_F"))   // 本地玩家自身 inventory 客户端已知
        Delay(2);
    for (int j = 0; j < RNCSTEALTH_RING_DOTS; j++)
        Thing_Remove(RNCSTEALTH_RING_TID + j);
}
```

  - 自清理：不需显式 remove 消息——marker 被任意破隐路径取走后，客户端循环
    自行观察到并删点；换图由引擎统一清 CLIENTSIDEONLY actor/重置脚本
    （`g_game.cpp:3428-3431,3453`）；玩家掉线同理无残留。
  - bot 持有 boss 时不显示（bot 无客户端；且 bot 本不触发 reload）——可接受。
  - 注意（skill 已载明）：CLIENTSIDE 脚本不能当 `A_JumpIf(CallACS(...))` 条件
    （服务端恒 false）——本设计不依赖该用法。

**方案 B（备选）：全场可见。** monitor 直接服务端 `Spawn` 同样的点（TID 同上），
破隐退出路径 `Thing_Remove`。给幸存者反制信息（知道 boss 被钉在哪个口袋），
实现更少一层。若联机环境下 CLIENTSIDE 环出问题，回退到 B。

**取舍**：A 保住伏击体验、圆环定位为"自我约束提示"；B 把圆环变成双方博弈
信息。默认 A。

**圆点实现（两方案共用）**：

- 贴图：TEXTURES 新增 `RNCSTEALTHDOT`——`__DOT.png`（mod 自带 1×1 点，
  `src/graphics/__DOT.png`）放大 + ClashMan 染色 Translation，无需新美术。
- actor `RNCStealthRingDot`：`+NOBLOCKMAP +NOSHOOTABLE +NOGRAVITY +BRIGHT`、
  RenderStyle Translucent、Alpha 0.55、scale ≈2（≈16 单位点）、慢脉冲
  （`A_FadeTo` 往返，纯装饰）；默认重力关闭、固定在激活平面 cz+8（抬升地面
  处允许被遮挡；若实测坡地/楼梯观感差再改带重力"垂坠"变体）。
- 32 点 / 11.25° 间距约 50 单位。

### 9.3 冷却显示（`DrawBar_RNCClashman_W` + `SetOverlayBar`）

- **前置：`RNCStealthCooldown` 改为可读余量的普通 Inventory**（v1 的自过期
  Powerup 读不到剩余时间，Zandronum 无 GetPowerupTicsLeft）：
  `actor RNCStealthCooldown : Inventory { inventory.maxamount 175 }`，
  `RNCStealthBreak_P` 给满 175，另起
  `ACS_NamedExecuteAlways("uh_rncstealth_cooldowntick", 0)`。
  不放 Flash 状态递减（RNCClashman 的 Flash 循环帧长 2/1-tic 不均匀，速率会漂；
  Balrog 的 Flash 递减不适用于本武器结构）。
- 新增计时脚本：`while (CheckInventory("RNCStealthCooldown")) { TakeInventory(...,1); Delay(1); }`
  ——每刻精确递减、自动终止；Break_P 幂等保证最多一个实例。
- `boss_bars.acs` 的 `DrawBar_RNCClashman_W` 加：
  `SetOverlayBar(CheckInventory("RNCStealthCooldown"), 175);`
  （cloak 冷却同款先例 `boss_bars.acs:197` 无条件显示；H/V 布局自动用
  VARFLS1/BARFLS1 图形。若 overlay 落点与 CustSbarPos1 自定义条不重合，
  备选 `DrawCustomBar1(76, amount, 175)` 走 slot 77=BARFLS1 目录样式，
  `SBARINFO.v.uhappend:83`——实测二选一。）
- 可选配套：`DrawReloadIcon("R017B0")` + 新增
  `src/graphics/ReloadIcons/R017B0.png`（本 mod reload 技能图标的既有惯例，
  依 DLCCentaurman `Reload:` 先例配图）。

### 9.4 v2 修改文件清单

| 文件 | 改动 |
|------|------|
| `RNCClashman_W.dec` | 删 `Power_RNCStealth`；Begin/Break 改 AlphaPower；`RNCStealthCooldown` 改 Inventory；新增 `RNCStealthRingDot` |
| `classes/bosses/rnc_clashman.acs` | 新增 `uh_rncstealth_ring`（CLIENTSIDE）与 `uh_rncstealth_cooldowntick`；monitor 首刻触发圆环 |
| `hud/boss_bars.acs` | `DrawBar_RNCClashman_W` 加 `SetOverlayBar`（可选 `DrawReloadIcon`） |
| `src/TEXTURES`（或 `TEXTURES.bars`） | 新增 `RNCSTEALTHDOT`（`__DOT` 放大 + 染色） |
| `src/graphics/ReloadIcons/R017B0.png` | 可选新增 |

### 9.5 v2 测试与验收补充

- [ ] 破隐后 alpha 完全恢复 1.0；激活期间敌对视角全透明（方案 A 联机或双端验证）、观战/队友视角 0.25 轮廓
- [ ] 圆环：激活即现、任意破隐路径（出圆/空中/开火/死亡）即消；换图/掉线无残留；仅 boss 客户端可见（方案 A）
- [ ] 冷却条从满格每刻递减、5 秒归零消失；归零前 reload 拒绝、归零后可用
- [ ] 冷却递减不受开火动画影响（ACS 计时而非 Flash/Ready 递减）
- [ ] 单机与联机（net mode）各验一遍 CLIENTSIDE 环

---

## 10. v2 执行结果（2026-09-11）

### 已实现

- **9.1**：删除 `Power_RNCStealth`；`RNCStealthBegin_P` 改给
  `UH_00_AlphaPowerGiver`，`RNCStealthBreak_P` 改取 `UH_00_AlphaPower`。
- **9.2**：`TEXTURES` 新增 `sprite RNCXA0`（`__DOT` ×8 + `Translation "4:4=204:204"`）；
  `RNCStealthRingDot` actor（`+NOBLOCKMAP -SHOOTABLE +NOGRAVITY +BRIGHT`、
  Translucent 0.55、Scale 2、`A_FadeTo` 脉冲）；`rnc_clashman.acs` 新增
  `uh_rncstealth_ring` CLIENTSIDE（32 点，TID 3970-4001，标记消失即自清），
  monitor 首刻用 `NamedExecuteClientScript` 触发。
- **9.3**：`RNCStealthCooldown` 改为 `Inventory { maxamount 175 }`；
  `RNCStealthBreak_P` 给满 175 并启动 `uh_rncstealth_cooldowntick`（每刻 -1）；
  `DrawBar_RNCClashman_W` 加 `SetOverlayBar(CheckInventory("RNCStealthCooldown"), 175)`。
- 未做可选项 `DrawReloadIcon("R017B0")`（需要新美术）。

### 与计划的偏差（实现/运行期发现）

1. **内置函数名是 `NamedExecuteClientScript`，没有 `ACS_` 前缀**
   （ACC `zspecial.acs:431` `-145:NamedExecuteClientScript`；mod 先例
   `uh_bosscore.acs:40`）。计划写的 `ACS_NamedExecuteClientScript` 编译不过。
2. **`+NOSHOOTABLE` 不是 flag**（引擎报 unknown flag），用 `-SHOOTABLE`。
3. 圆点用普通 `Spawn`（与计划一致）：`DoSpawn(force=false)` 会
   `P_TestMobjLocation`，落在墙里的点被销毁，所以狭窄房间内不会满 32 点
   （实测出生小房间 8 点）；开阔处才完整。若要恒定 32 点需改 `SpawnForced`。
4. `TEXTURES` 用 `sprite` 关键字而非 `graphic`：只有 `sprite` 类型的
   TEXTURES 定义会被 sprite 查找命中（`texturemanager.cpp` 顶层关键字）。

### MCP 验收（mm8bdm-v6b-smoke）

| 项 | 结果 |
|---|---|
| 激活 | `alpha=0`、`UH_00_AlphaPower=1`、`RNCStealthActive_F=1`、invuln/unsolid=1 |
| 圆环 | 激活即生成 `RNCStealthRingDot`（开间内可满 32；墙内点按引擎规则剔除） |
| 圆环清理 | 开火破隐后圆点数 = 0 |
| alpha 恢复 | 破隐后 `alpha=1`、`UH_00_AlphaPower=0` |
| 冷却 | `RNCStealthCooldown` 175→0，每刻 -1；`SBARFlashOverlayAmmo` 同步 175→0 |
| 启动 | 无编译/致命错误；`smoke-test.sh --profile mm8bdm-v6b-full` status=ok、reportedLines=0 |

### 未覆盖

- 联机双端验证 CLIENTSIDE 环的"仅自己可见"（需真实双客户端；单机路径已验）。
- `DrawReloadIcon` 图标美术。
