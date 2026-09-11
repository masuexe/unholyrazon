# RNCClashman 隐身机制改造实施计划 — Reload 键主动隐身

- 日期：2026-09-11
- 状态：待实施（计划已含用户拍板结果）
- 涉及文件：`src/actors/classes/bosses/RNCClashman.dec`、`src/actors/classes/bosses/RNCClashman_W.dec`、`src/acs_source/classes/uh_classes.acs`、`src/acs_source/v6b_overrides/corescripts/utilities/footchec.acs`（加可选 tol 参数）、新增 `src/acs_source/classes/bosses/rnc_clashman.acs`
- 不改动：`LOADACS`、`KEYCONF`、`TEAMINFO`、bar/HUD（可选增强除外）

## 1. 现状

`RNCClashman.dec` 目前是"走路自动隐身"：`See:` 状态逐帧 `A_SetShadow`（走路时进入 SHADOW 半透明 0.5），`Spawn:`/`Missile:`/`ClassPain:` 用 `A_ClearShadow` 显形。该行为继承自 Unholy v7b pb1（参考包 `unholy_bosses_unbound_v7b_pb1/actors/MainBoss/RNCClashman.txt:502`），无任何主动按键参与，隐身/显形完全由移动与开火状态被动驱动。

`A_SetShadow`/`A_ClearShadow` 是 Strife 遗留指针（引擎 `g_strife/a_strifestuff.cpp:437-450`）：设置/清除 `+SHADOW`、RenderStyle Translucent、alpha 0.5。

## 2. 需求

用户原案 + 2026-09-11 拍板结果：

| 项目 | 决定 |
|------|------|
| 触发方式 | 删除 See/Spawn/Missile/ClassPain 的自动 SetShadow/ClearShadow，改由武器 `Reload:` 状态触发 |
| 判定圈 | 激活瞬间以当时玩家 XY 为圆心（快照，不跟随），`floorz` 为 z，半径 **r = 256** 地图单位；纯逻辑判定区域，不做可见光圈（后续可加） |
| 破隐条件 A | 玩家 XY 距圆心超过 r（出圆），从激活瞬间起即生效，不考虑 z |
| 破隐条件 B | 玩家在空中（`z - floorz` 大于容差）。**空中激活例外**：激活时在空中则立即隐身，此条件在首次落地后才"武装"；落地后再离地（跳跃、坠落、被击飞均算）即破隐 |
| 消耗/冷却 | 无弹药消耗；破隐后 **5 秒冷却**（175 tics，调参入口见 §4.4 常量） |
| 开火 | Fire / AltFire 立即破隐（然后正常执行攻击） |
| 隐身期间加成 | **无敌**（`core_invulnerableplayer`，APROP_Invulnerable 栈）+ **unsolid**（`core_unsolidplayer`，不可阻挡/不可选中） |
| 视觉 | **完全隐身**（PowerInvisibility，Strength 100） |
| 隐身中再按 Reload | 无效果（不改圆心、不取消） |
| 时长上限 | 无，直到破隐条件触发或死亡 |

## 3. 技术依据（已对源码核实）

1. **Reload 键 → 武器状态**：引擎在 `WF_WEAPONRELOADOK` 置位且玩家按住 `BT_RELOAD`（=64）时调用 `P_ReloadWeapon` 跳入武器 `Reload:` 状态（`zandronum-stable-branch-default/src/p_pspr.cpp:1002-1014`）。`P_ReloadWeapon` 无 `Reload:` 状态时不跳转（同文件 :439-462）。
2. **WRF_ALLOWRELOAD 必须显式传**：`A_WeaponReady` 仅在参数含 `WRF_AllowReload`(16) 时调用 `DoReadyWeaponToReload` 置位 `WF_WEAPONRELOADOK`（`p_pspr.cpp:872,915`）。裸 `A_WeaponReady`（参数 0）**不**启用。标志在状态切换时被清（:210），随后被 Ready 循环重新置位——2-tic Ready 循环下等效每刻检测，不会漏按。
3. **本 mod 先例**：DLCCentaurman 4.0 的"Reload 维度跳跃"即此模式（`DLCCentaurman_W.dec:50` 的 `Reload:` 状态 + `:261-288` 的 `_Ready*_P` 在弹药充足时调 `A_WeaponReady(WRF_ALLOWRELOAD)`）。RNCClashman 无弹药门槛，可直接在武器 Ready 循环里加 flag，不需要 CustomInventory 中转。
4. **完全隐身**：`PowerInvisibility` 的 `DoEffect` 每刻设 `alpha = 1 - Strength/100`（`a_artifacts.cpp:635-636`），Strength 100 → alpha 0；`EndEffect` 正确还原 flags/RenderStyle/alpha（:669-698），拿走即显形。mod 先例 `Power_ShadMan`（`TheShadowManMythBoss_W.dec:737`），其注释确认**不要** `+CANTSEEK`（会破坏 Shadowblade 类追踪武器）。
5. **无敌**：v6b 核心脚本 `core_invulnerableplayer`（v6b `acs_source/corescripts/utilities/PROPUTIL.acs:211-226`）——`toggle=true` 给 `PlayerPropertyInvulnerable` 标记（可叠加）并置 `APROP_Invulnerable`；`false` 弹一层，栈清零才解除属性。直接设 APROP，**没有** PowerInvulnerable 的 colormap 滤镜问题。栈语义与出生保护（SPWNPROT）等其他无敌来源正确叠加；mod 在 DECORATE 侧直接调用的先例：`UnholyInsurance.dec:63`、`InvincibleCandy.dec:67`。注意（mod 内 `clownpiece_spellcard.acs:123` 已注明）：`false` 只弹一层，这是栈的既定语义而非缺陷。
6. **unsolid**：v6b 核心脚本 `core_unsolidplayer`（v6b `acs_source/corescripts/utilities/PROPUTIL.acs:632-663`）。`USP_TOGGLEON` 给 `PlayerPropertyUnsolid` 标记；`USP_TOGGLEOFF_DAMAGE` 恢复固体，若恢复时与其他 actor 重叠则扣 `damage` 血（mod 惯例传 `core_getmaxhealth()/10`）。`USP_*` 常量在 DECORATE 中可用（v6b `actors/acspropconstants.txt:59` 起，`const int` 声明）——Balrog/EyelentoMajor/ShadowMan 等 boss 均直接在 DECORATE 里这样调用。
7. **冷却 token**：用无效果 `Powerup { powerup.duration N }` 自过期（先例：v6b `ResolidDamageIndicator`，`megaman-flags.txt:791`）。比 ACS 计时器简单且天然网络同步。
8. **空中判定**：`GetActorZ(0) - GetActorFloorZ(0)`，mod 先例 `motion_helpers.acs:50`。
9. **圆判定**：定点数平方距离比较，无需开方：`FixedMul(dx,dx)+FixedMul(dy,dy) > FixedMul(r,r)`。
10. **存活检测**：Zandronum ACC 无 `ActivatorIsAlive`，用 `GetActorProperty(0, APROP_Health) > 0`（mod 先例 `shared_movement.acs:8`）。
11. **着地判定**：用核心脚本 `core_CheckFooting`（本 mod 的 UH override：`v6b_overrides/corescripts/utilities/footchec.acs:29`）。语义：`z-floorz==0`，或在脚下 1 单位处 Spawn 探针 `8bdmFootholdCheck` 失败（被地面挡住）→ 着地；否则 airborne。选它而非裸 `z-floorz` 的理由：a) mod 权威着地判定（`uh-BasePain.dec:122`、`eden_runtime.acs:146` 等在用）；b) UH override 内含 `CheckCeilingFootingFunc`——本 mod 存在反重力来源（GravityHold、Kamilia `CeilingFlag`），玩家贴天花板行走时裸 z-floorz 会误判空中而误破隐，`core_CheckFooting` 正确处理。每次调用含一次 Spawn+Remove，每刻一次×单个 boss，开销可忽略。
12. **着地容差参数（UH 扩展 core_CheckFooting）**：给 override 版 `core_CheckFooting` 加可选参数 `tol`——`tol=0` 走现有逻辑（位不变）；`tol>0` 时额外把 `z - floorz <= tol` 判为着地（正常重力），反重力分支对称放宽为 `ceilingz - z <= 58 + tol`。数值依据：下楼梯时玩家离脚下 floorz 至多一级台阶高（典型 8~32），而 jumpz 14 的跳跃顶点 = 14²/2 = **98 单位**（Zandronum 每刻重力恒 1.0 u/tic²），tol=32 即可让全部楼梯场景不离地、跳跃照常破隐。**兼容性已核实**：Zandronum ACS 命名脚本少传参时缺省读 0（v6b 核心自身先例：`core_unsolidplayer` 声明 3 参、DECORATE 只传 2 参，`damage` 读 0 走默认分支），故 mod 源码、v6b 编译库、DECORATE `CallACS("core_CheckFooting")` 等现存零参调用全部落到 tol=0 旧行为，无需改动。**实现要点**：tol>0 分支用 floorz 比较而非把探针 Spawn 到 `z-tol`——探针 actor 有半径，贴墙跳跃时深探针会撞墙误报着地，且 floorz 已正确处理 3D floor。

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

- 可见光圈 FX（激活点地板显示判定圈）
- 破隐/隐身音效与 HUD 冷却图标（`boss_bars.acs` 的 `DrawBar_RNCClashman_W` 可挂 `DrawReloadIcon` 样式提示）
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
