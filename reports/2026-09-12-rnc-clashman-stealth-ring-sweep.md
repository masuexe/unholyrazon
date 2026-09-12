# RNCStealthRingDot 旋转扫描改造方案 — MXP1 BCDE 拖尾 + 双交点连续生成

- 日期：2026-09-12
- 状态：**已实施并验证**（§4 = 实现代码，§10 = 执行与 MCP 验收结果）
- 涉及文件（2 个，改动都很小）：
  - `src/actors/classes/bosses/RNCClashman_W.dec` — 只改 `RNCStealthRingDot`（515-524 行）
  - `src/acs_source/classes/bosses/rnc_clashman.acs` — 只改常量块（11-16 行）与 `uh_rncstealth_ring`（65-80 行）
- 不改动：`LOADACS`、`KEYCONF`、DECORATE 包含链、判定半径/圆心快照/破隐条件/冷却/HUD、`uh_rncstealth_monitor` 的启动方式（仍是 monitor 首刻 `NamedExecuteClientScript`，`rnc_clashman.acs:24`）

## 1. 现状

actor（`RNCClashman_W.dec:515-524`）：

```decorate
actor RNCStealthRingDot : BasicGraphicEffect {
  +FORCEXYBILLBOARD
  Alpha 0.55
  States {
   Spawn:
    MMFX B 4  // A_FadeTo(0.15, 0.1)
    MMFX B 4  // A_FadeTo(0.55, 0.1)
    loop
  }
}
```

脚本（`rnc_clashman.acs:65-80`）：一次性在圆周上放 32 个点，等 `RNCStealthActive_F` 消失后 `Thing_Remove` 清掉。

为什么现在看到的是"**一整圈实线**"：

- 32 点均分 → 圆心角 11.25°；半径 256 → 相邻点圆心距 = 2π×256/32 ≈ **50 单位**；
- `BasicGraphicEffect` 基类自带 **`scale 2.5`**，MMFX B 是 16×16 px → 世界里是 **40×40 单位**的大圆点，比 50 单位的间距只小一点 → 32 个点直接连成一整圈。
- 状态只有 `MMFX B` 一帧，所以是"静止的一圈"，没有时间维度的信息。

## 2. 需求（用户原案，2026-09-12）

| 项 | 决定 |
|---|---|
| 点的动画 | `MMFX B`（静止循环）→ **`MXP1 B → C → D → E → stop`**（一次性"缩小消失"粒子） |
| 生成位置 | 圆（半径 256、圆心 = 激活瞬间玩家 XY）与**绕圆心旋转的直线**的**两个交点**（θ 与 θ+180°） |
| 生成方式 | **持续生成**（不再是"一次摆一圈"）；靠粒子自身的寿命形成拖尾 → 视觉上是两条对称彗尾在圆周上扫 |
| 半径/圆心/z/判定/冷却 | 全部不变（`RNCSTEALTH_RADIUS`、`cz + 8.0` 快照、`RNCStealthActive_F` 生命周期） |
| 可见性 | 不变（CLIENTSIDE，仅 boss 自己的客户端可见） |

## 3. 技术依据（已对引擎 / 基游戏源码核实）

### 3.1 ACS 的 `cos`/`sin` 角度单位是"整圈"，不是度 ← 本次改造最容易踩的坑

引擎 `zandronum-stable-branch-default/src/p_acs.cpp:12280,12284`：

```cpp
case PCD_SIN: STACK(1) = finesine[angle_t(STACK(1)<<16)>>ANGLETOFINESHIFT]; break;
case PCD_COS: STACK(1) = finecosine[angle_t(STACK(1)<<16)>>ANGLETOFINESHIFT]; break;
```

配合 `tables.h:49-53`（`FINEANGLES 8192`、`ANGLETOFINESHIFT 19`）：索引 = `raw >> 3`，而 `raw = 65536`（即 ACS 里写的 `1.0`）正好落在索引 8192 = 一整圈。

结论：

- 步进必须写 **`1.0 / N`**（N = 一圈分多少步）；写 `6.0` 想表示 6° 实际是 **6 整圈 = 0°**，点会原地不动。
- **180° 就是 `0.5`** → 对跖点直接 `cos(ang + 0.5) / sin(ang + 0.5)`。
- 现有代码 `int ang = i * (1.0 / RNCSTEALTH_RING_DOTS);` 正是这个约定，所以那 32 个点是**正确的整圈**，不是 bug。
- 对照：**DECORATE 的 `cos()/sin()` 用的是"度"**（本文件 `ClashSpreadingBoss1` 里 `cos(user_angle)` 配 `random(0, 359)`）；两套单位不同，别互相套用。
- 超过一圈的角度（例如 `ang` 接近 1.0 时的 `ang + 0.5`）无需先归一化：`raw << 16` 的 32 位回绕周期恰好等于一整圈，结果仍是正确角度。代码里的 `if (ang >= 1.0) ang -= 1.0;` 只是防止定点数长期累积，不是为了正确性。

### 3.2 `Spawn()` 是 ACC 内建函数

引擎 `p_acs.cpp:11694-11697`（`PCD_SPAWN`）→ `DoSpawn(class, x, y, z, tid, angle, force = false)`，**返回生成数**。尾部参数可省略（缺省 0）：本文件现在就是 5 参调用（`class, x, y, z, tid`），v6b `acs_source/_includes/common/8BDMEFCT.acs:131` 用的是 6 参带 angle 的形式。

- `tid = 0` 合法（`DoSpawn` 直接 `actor->tid = tid`，`p_acs.cpp:4186`），即点可以完全不留 TID。
- 我们的点用 `+FORCEXYBILLBOARD`，不需要 angle。

### 3.3 非 force 的 `Spawn` 会做落点测试

`force || P_TestMobjLocation(actor)`（`p_acs.cpp:4183`）；测试失败 → 当场 `Destroy()`（`:4214-4221`）。

- 圆周扫进墙里 / 出开间时，这些点**直接不生成** → 拖尾被几何自然"切掉"，不会穿墙。
- 想无视地形恒定显示 → 用 `SpawnForced`（ACC `zspecial.acs:322` 的 `-36:SpawnForced(4,6)`；引擎 `ACSF_SpawnForced`，`p_acs.cpp:6338`，`force = true`）。点是 `+NOINTERACTION`，塞进墙里也不会被推出来，只是被墙面遮挡。

### 3.4 CLIENTSIDE 脚本里 Spawn 出来的 actor 自动本地化

`NETWORK_InClientMode()` 时 `actor->NetworkFlags |= NETFL_CLIENTSIDEONLY`（`p_acs.cpp:4208-4212`）；反过来服务端生成这类 actor 会**立刻销毁**（`:4205-4206`）。所以这些点只可能存在于客户端本地，不占网络、别的玩家看不到（与 v2 现状一致）。

另外 `BasicGraphicEffect` 类自带 `+CLIENTSIDEONLY`（`thingdef/thingdef_data.cpp:281`：`DEFINE_FLAG(NETFL, CLIENTSIDEONLY, AActor, NetworkFlags)`）——本来就是客户端专属 actor。

### 3.5 `+NOINTERACTION` 不影响状态机 → 一次性动画能自己消亡（本方案的基础）

`AActor::Tick` 的 NOINTERACTION 分支只跳过物理、**不 return**（`p_mobj.cpp:4019-4047`），状态推进在其后的公共段（`:4540-4556`）：`--tics <= 0` → `SetState(state->GetNextState())`，而 `NextState == NULL`（即 `stop`）时 actor 自我销毁。

**推论**：点的"死亡"就是拖尾的"淡出"，不需要任何清理逻辑。这正是把静态点改成一次性动画后能得到旋转拖尾的原因。

### 3.6 `BasicGraphicEffect` 基类已经给好的属性（v6b `actors/basicactors.txt:62-89`）

```
+CLIENTSIDEONLY +NOINTERACTION +NOGRAVITY -SOLID +MISSILE +DONTBLAST
renderstyle "Translucent"  alpha 1.0  radius 2  height 2  scale 2.5
```

它的 `Spawn:` 是"先给 `MM8BDMProjSpawnFuncClient` 再 `A_JumpIf(true, "SpawnFrame")`"，所以 v6b 子类惯例是覆盖 `SpawnFrame:`；而 `MM8BDMProjSpawnFuncClient` 的 Pickup 会跑 `ACS_NamedExecuteWithResult("core_runspawnfuncs_client", SFT_PROJCLIENT)`（`actors/inventory/spawnfunc.txt:53-60`）——**每个点一次 ACS 调用**。

本 mod 直接覆盖 `Spawn:` 有大量先例（`items/tow/PlasticChair.dec:120`、`player/uh-BasePain.dec:436`、`coopenemies/bosses/HeatMan.dec:161`）：本地生成的特效不需要走服务端 spawn-func 通道。本方案**继续覆盖 `Spawn:`**（与现状一致、diff 最小，还省掉每点一次 ACS）。

### 3.7 MXP1 贴图与帧速惯例

- `sprites/effects/explosions/MXP1B0/C0/D0/E0.png` = **16 / 12 / 10 / 4 px 的同心实心圆**（实测：B 与现在用的 MMFX B 形状完全一致，都是 208 个不透明像素；MXP1 B 是纯白 `255,255,255`，MMFX B 是灰白 `248,248,248`）。
  → 换过去后"头"和现在一样大，多出来的是后面越缩越小的尾。
- v6b 帧速惯例 **2 tics**：`actors/misc/effects.txt:461-468`（`ExplosionEffect1`：`MXP1 ABCDE 2 A_SetTics(mass)`，带 `+BRIGHT`）、`actors/inventory/buster/protobuster.txt:207-214`（`ProtoShotFX`：`MXP1 ABCD 2`）。
- 因此寿命 = 4 帧 × 2 tics = **8 tics**。

### 3.8 `Thing_Remove(tid)` 删除**所有**匹配 tid 的 actor

`p_lnspec.cpp:1310-1332` 用 `FActorIterator` 遍历全部匹配项逐个 `P_RemoveThing`。→ 轮转 TID 池时，退出循环清一次池即可清掉当时还活着的点（不需要记录哪些槽在用）。

### 3.9 两个硬禁忌：一次性动画不能用 `wait`、不能用 `loop`

- `wait` → `realstates[i].NextState = &realstates[i]`（`p_states.cpp:928-930`）：该帧永远自我重复，**`stop` 永远到不了** → 点永远留在原地。
- `loop` → 回到 `Spawn:` 重播 → 点永不消亡 → 每 tic 2 个点无限堆积（actor 数量无上限、拖尾糊成实心圆）。

所以新动画**必须以 `stop` 结尾**。

### 3.10 TID 区间

`RNCSTEALTH_RING_TID 3970` + 32 槽 = **3970..4001**，已与 Eden C396 预留区间（1500-1563 / 1600-1663，`eden_tid_reserve.acs:5-8`）核对无冲突，继续沿用。（`src/README.md` 的 TID 表未列本区间，属可选补充。）

## 4. 设计

### 4.1 视觉模型

- **点 = 一次性粒子**：出生即 MXP1 B（最大最亮），8 tics 内 B→C→D→E 缩到消失。
- **每 tic 在两个交点各生成一个** → 每侧圆周上同时活着 8 个"不同年龄"的点，越旧越小、越旧越靠后 → **彗尾**（头大尾细）。
- **两个交点** = 旋转直线与圆的交点 = `θ` 与 `θ + 0.5`（+180°），永远对跖、永远对称。
- **转速** = 每步 `1.0 / RING_STEPS` 圈；`RING_STEPS = 96` → 3.75°/tic → 一圈 ≈ 97 tics ≈ 2.8 s（见 §4.4 精度备注）。
- **方向**：`ang` 递增 → 从 +X 轴转向 +Y 轴（俯视地图的逆时针）。

示意（某一刻）：

```
            ○  ← 头：刚生成（MXP1 B，16px）
          ·
        ·          ← 尾巴：越旧越小（C/D/E）
      ·
  ────┼────        圆心 = 激活瞬间玩家 XY（水平面 cz+8）
      ·
        ·
          ·
            ·  ○  ← 对侧的头（θ+180°）
```

### 4.2 actor 改动（整段替换 `RNCClashman_W.dec:515-524`）

```decorate
// Judgement-circle sweep dot (clientside; see uh_rncstealth_ring).
// 2026-09-12: 静态点 -> 一次性"缩小消失"粒子（MXP1 B..E -> stop）。
// 由脚本每 tic 在圆周的两个交点生成，靠 4 帧动画自然消亡形成彗尾；
// 寿命 = 4 帧 x 2 tics = 8 tics（与脚本 RNCSTEALTH_RING_SPAWN_TICS 配套）。
// 不要改成 loop / wait：点会永不消失（见方案 §3.9）。
actor RNCStealthRingDot : BasicGraphicEffect {
  +FORCEXYBILLBOARD        // 保持：否则扫到侧视角会变成薄片
  Alpha 0.55               // 与现状一致（基类 renderstyle 已是 Translucent）
  Scale 1.5                // 基类默认 2.5（16px -> 40 单位）；见 §4.4
  States {
   Spawn:
    MXP1 B 2
    MXP1 C 2
    MXP1 D 2
    MXP1 E 2
    stop
  }
}
```

要点：

- `Scale` 是本方案唯一新增的视觉参数。基类 `2.5` 会让"头"有 40 单位宽（和现在一样，但拖尾会糊成一坨粗线），建议 `1.5`（24 单位）。
- 想更"能量/爆炸感"可加 `+BRIGHT`（v6b `ExplosionEffect1` 同款）。
- 不用在 `Spawn:` 前插 `TNT1 A 0` 空帧：那只会让点整体晚出生 1 tic（两侧依旧对称），无必要。

### 4.3 脚本改动（`rnc_clashman.acs`）

**常量块**（替换现有 `RNCSTEALTH_RING_TID` / `RNCSTEALTH_RING_DOTS` 两行；其余常量不动）：

```acs
#define RNCSTEALTH_RING_TID 3970        // TID 池起点：3970..4001（32 槽，见 §3.10）
#define RNCSTEALTH_RING_SLOTS 32        // 池大小，与上面区间宽度一致
#define RNCSTEALTH_RING_STEPS 96        // 一圈分多少步（每步 1.0/96 圈 = 3.75°）
#define RNCSTEALTH_RING_STEP (1.0 / RNCSTEALTH_RING_STEPS)
#define RNCSTEALTH_RING_SPAWN_TICS 1    // 每几个 tics 生成一对交点（1 = 每 tic）
```

（`RNCSTEALTH_RING_DOTS` 不再需要；`RNCSTEALTH_RADIUS`、`RNCSTEALTH_RING_TID` 的区间语义保持。）

**脚本**（整段替换 `uh_rncstealth_ring`，原 65-80 行）：

```acs
// Judgement-circle sweep: 在圆与"绕圆心旋转的直线"的两个交点各生成一个拖尾点。
// CLIENTSIDE：只在本机（boss 自己的客户端）生成 NETFL_CLIENTSIDEONLY 点。
// 点自身 8 tics 后 stop，拖尾无需维护；TID 池只用于退出时一次性清空。
script "uh_rncstealth_ring" (int cx, int cy) CLIENTSIDE {
  int cz = GetActorFloorZ(0);
  int ang = 0;                       // 定点角：1.0 = 360°（§3.1）
  int slot = 0;                      // TID 池轮转下标

  while (CheckInventory("RNCStealthActive_F")) {
    // 交点 1：θ
    Spawn("RNCStealthRingDot",
          cx + FixedMul(RNCSTEALTH_RADIUS << 16, cos(ang)),
          cy + FixedMul(RNCSTEALTH_RADIUS << 16, sin(ang)),
          cz + 8.0, RNCSTEALTH_RING_TID + slot);
    slot = (slot + 1) % RNCSTEALTH_RING_SLOTS;

    // 交点 2：θ + 180°（定点里的半圈就是 0.5）
    Spawn("RNCStealthRingDot",
          cx + FixedMul(RNCSTEALTH_RADIUS << 16, cos(ang + 0.5)),
          cy + FixedMul(RNCSTEALTH_RADIUS << 16, sin(ang + 0.5)),
          cz + 8.0, RNCSTEALTH_RING_TID + slot);
    slot = (slot + 1) % RNCSTEALTH_RING_SLOTS;

    ang += RNCSTEALTH_RING_STEP;
    if (ang >= 1.0) ang -= 1.0;      // 回绕，避免定点数无限增长

    Delay(RNCSTEALTH_RING_SPAWN_TICS);
  }

  // 破隐/死亡/出圈：清掉池里可能还活着的点（每侧 ≤ 8 个）
  for (int j = 0; j < RNCSTEALTH_RING_SLOTS; j++)
    Thing_Remove(RNCSTEALTH_RING_TID + j);
}
```

与现状的差异摘要：

| 原 | 新 |
|---|---|
| 一次性 `for (i < 32)` 摆满一圈 | `while` + `Delay` 每 tic 生成两个交点 |
| 角度 = `i * (1.0 / 32)`（静态均分） | 角度 = 累加 `1.0 / 96`（旋转） |
| 等待循环 `Delay(2)` | 生成循环 `Delay(1)`（与 `SPAWN_TICS` 一致） |
| 退出清 32 个固定 TID | **不变**（池语义相同） |
| `Spawn` 的 5 参调用形式 | **不变** |

### 4.4 参数速查 / 调参

术语：**点寿命** = 4 帧 × 每帧 tics（默认 2 → 8 tics）；**每侧活点数** = 寿命 / `SPAWN_TICS`；**一圈** = `RING_STEPS` × `SPAWN_TICS` tics（35 tics = 1 s）；**相邻点弧长** = 2π×256 / `RING_STEPS` ≈ 1608 / `RING_STEPS` 单位。

| RING_STEPS | SPAWN_TICS | 每帧 tics | 一圈 | 相邻点弧长 | 每侧活点数 | 单侧拖尾跨度 |
|---|---|---|---|---|---|---|
| 64 | 1 | 2 | 1.83 s | 25.1 u | 8 | 45° |
| **96** | **1** | **2** | **2.77 s** | **16.8 u** | **8** | **30°（推荐）** |
| 128 | 1 | 2 | 3.66 s | 12.6 u | 8 | 22.5° |
| 96 | 2 | 2 | 5.54 s | 16.8 u | 4 | 15° |
| 96 | 1 | 3 | 2.77 s | 16.8 u | 12 | 45° |

- 想更"长/密"的尾：加大每帧 tics（3~4）或减小 `SPAWN_TICS`；想更"雷达点/断续"：加大 `SPAWN_TICS` 或 `RING_STEPS`。
- 精度备注：`1.0 / 96` 在编译期被 ACC 截断成 `682`（真值 682.67），96 步只累积到 0.999 圈，所以一圈实际是 **97 步 ≈ 2.77 s**（差 1%，肉眼无感）。要严格整除就用 2 的幂：`64`（1024）或 `128`（512）。
- `Scale` 取舍：`1.0`（16 u，相邻点刚好相切，最锐利）／`1.5`（24 u，**推荐**，头明显且尾连续）／`2.5`（基类默认，40 u，最粗最糊）。
- 帧速保持 2 是 v6b 惯例（§3.7）；改成 1 会一闪即逝。

### 4.5 备选（按需取用）

- **A. 不要 TID 的极简版**：`Spawn(..., cz + 8.0, 0)`（tid 传 0，见 §3.2），删掉 `slot` 与结尾的 `Thing_Remove` 循环。代价：破隐瞬间不会立刻清空，残余 ≤ 8 个点会在 8 tics（≈0.23 s）内自然缩小消失——观感更柔和、代码更短。若采用，连同 `RNCSTEALTH_RING_TID/SLOTS` 与 §3.10 的区间占用一起删掉。
- **B. 无视地形强制显示**：`Spawn` → `SpawnForced`（§3.3）；点仍会被墙面遮挡，不会真的"穿墙可见"。
- **C. 更亮**：加 `+BRIGHT`，或 `RenderStyle "Add"`（暗场更抢眼，浅色地面上对比度会掉，建议游戏内 A/B）。
- **D. 非对称双扫**：第二个交点用 `ang * 2` 或 `-ang`，就不是对称双彗尾而是"双速/反向扫"。需求是对称，故不作默认。

### 4.6 边界与陷阱清单

1. **角度单位**：任何"看起来像度数"的常量（`6.0`）都是整圈，只用 `1.0/N` 与 `0.5`（§3.1）。
2. **必须 `stop` 结尾**；`loop` / `wait` 都会让点永远活着（§3.9）。
3. **TID 池安全性**：每 tic 用 2 个槽，32 槽 → 同一槽 16 tics 后才复用，而点 8 tics 就死 → 复用时旧点必然已消亡，池清空不会漏（§3.8）。
4. **墙里的点**：非 force `Spawn` 会剔除（§3.3）→ 狭窄房间拖尾会断成弧段。这与现状一致（v2 实测：小房间里 32 点只剩 8 点）。
5. **z 是快照**：`cz = GetActorFloorZ(0)` 只在脚本启动时取一次，坡地/楼梯上点会埋进地面或悬空（现状一致，不在本次范围）。
6. **性能**：每 tic 本地生成 2 个、销毁 2 个；同屏约 16 个 `+NOINTERACTION` actor（无物理、只有状态机），CLIENTSIDE 零网络流量。
7. **死亡 / 换图 / 掉线**：CLIENTSIDE 脚本与点由引擎统一回收（沿用 v2 结论），无需额外处理。
8. **bot 持有 boss**：没有客户端 → 看不到环（现状一致）。
9. **monitor 调用点不变**：`NamedExecuteClientScript("uh_rncstealth_ring", PlayerNumber(), cx, cy)`（`rnc_clashman.acs:22-24`）与脚本签名 `(int cx, int cy)` 都不动。

## 5. 实施步骤

1. 改 `src/actors/classes/bosses/RNCClashman_W.dec` 的 `RNCStealthRingDot`（§4.2）。
2. 改 `src/acs_source/classes/bosses/rnc_clashman.acs` 的常量块与 `uh_rncstealth_ring`（§4.3）。
3. 重新编译 `uh_classes`（源 `src/acs_source/classes/uh_classes.acs`；include 目录与 `acc.exe` 调用形式见 `examples/eyemorph_addon/README.md` 的 "Compile and load"）→ `src/acs/uh_classes.o`。
4. 把 `src/` 递归打包成 `out/build.pk3`（ZIP）。
5. 按 §6 用 MCP 验证。

## 6. 测试计划（profile `mm8bdm-v6b-smoke`，已含 `out/build.pk3`）

1. `launch_instance` profile `mm8bdm-v6b-smoke`。
2. 触发隐身：正规流程（选 RNCClashman → 按 Reload），或直接 `give RNCStealthActive_F` 后手工触发 `uh_rncstealth_ring`；先给无敌以免被打断。
3. `wait_for_actor` / `actors_near`（class `RNCStealthRingDot`）核对：
   - 同屏同时约 **16** 个（每侧 8）；
   - 每个点到圆心距离 ≈ 256（`player_state` 取激活点作圆心；`actor_state` 核对两个"头"相差 180°）；
   - 连续 `step` 若干 tic：活点数稳定不累积；两帧截图对比可见点沿圆周移动、且贴图从 B 缩到 E。
4. `screenshot`：目视确认两条对称彗尾（头大尾细）。
5. 破隐（开火或 `take RNCStealthActive_F`）→ 点数归 0（方案 A：立刻；§4.5-A：8 tics 内）。
6. `read_engine_log` 无 DECORATE/ACS 编译错误与警告；`tools/mcp/smoke-test.sh --profile mm8bdm-v6b-full` status=ok。

## 7. 验收标准

- [ ] 屏幕上不再是"静止一整圈"，而是两条对称拖尾在圆周上扫。
- [ ] 点贴图序列为 MXP1 B→C→D→E，且 8 tics 后消失（不是静止 B）。
- [ ] 破隐后圆周上无残留点（方案 A 立刻；§4.5-A ≤ 8 tics）。
- [ ] 判定半径/圆心快照/破隐条件/冷却/HUD/alpha 恢复与 v2 完全一致（本次只动视觉）。
- [ ] 启动无 ACS/DECORATE 报错。

## 8. 明确不做

- 不用 `+FLATSPRITE`（Zandronum 3.x 无此 flag，v2 已确认）。
- 不改判定半径、圆心快照、破隐条件、冷却、HUD。
- 不渲染"直线本体"（需求只要两个交点上的点；画一条随角度旋转的线需要多条贴图或额外 actor，收益低）。
- 不做服务端权威版本（`BasicGraphicEffect` 是 `+CLIENTSIDEONLY` 类，服务端生成即销毁，§3.4）。

## 9. 引用清单

| 结论 | 出处 |
|---|---|
| ACS `cos`/`sin` = 定点整圈（1.0 = 360°） | `zandronum-stable-branch-default/src/p_acs.cpp:12280,12284`；`src/tables.h:49-53` |
| `Spawn` 内建签名 / 返回值 / force | `p_acs.cpp:11694-11697`；`DoSpawn` `p_acs.cpp:4170-4225` |
| 落点测试失败即销毁 | `p_acs.cpp:4183,4214-4221` |
| CLIENTSIDEONLY 标记与"服务端不生成" | `p_acs.cpp:4205-4212`；`thingdef/thingdef_data.cpp:281` |
| `+NOINTERACTION` 仍跑状态机 / `stop` 自毁 | `p_mobj.cpp:4019-4047`、`4540-4556` |
| `wait` = 下一状态指向自身 | `p_states.cpp:928-930` |
| `Thing_Remove` 删除全部匹配 tid | `p_lnspec.cpp:1310-1332` |
| `BasicGraphicEffect` 属性与 `scale 2.5`、`Spawn:`→`SpawnFrame:` 机制 | `mm8bdm-v6b/actors/basicactors.txt:62-89`；`actors/inventory/spawnfunc.txt:53-60` |
| MXP1 四帧尺寸与形状 | `mm8bdm-v6b/sprites/effects/explosions/MXP1{B,C,D,E}0.png` |
| MXP1 帧速惯例（2 tics） | `mm8bdm-v6b/actors/misc/effects.txt:461-468`；`actors/inventory/buster/protobuster.txt:207-214` |
| `SpawnForced` | ACC `zspecial.acs:322`（`-36`）；`p_acs.cpp:6338` |
| 本 mod 覆盖 `Spawn:` 的先例 | `src/actors/items/tow/PlasticChair.dec:120`；`src/actors/player/uh-BasePain.dec:436`；`src/actors/coopenemies/bosses/HeatMan.dec:161` |
| TID 预留无冲突 | `src/acs_source/classes/survivors/eden/eden_tid_reserve.acs:5-8` |
| 现状与 v2 实测 | `reports/2026-09-11-rnc-clashman-stealth-reload.md` §9.2、§10 |

## 10. 执行结果（2026-09-12，已实施 + MCP 验证）

### 已实现

- `RNCStealthRingDot`（`src/actors/classes/bosses/RNCClashman_W.dec`）：`MMFX B` 循环 → **`MXP1 B/C/D/E` 各 2 tics → `stop`**，新增 `Scale 1.5`；`+FORCEXYBILLBOARD`、`Alpha 0.55` 保持不变。
- `rnc_clashman.acs`：常量块改为 `RING_SLOTS / RING_STEPS / RING_STEP / RING_SPAWN_TICS`（`RNCSTEALTH_RING_DOTS` 删除）；`uh_rncstealth_ring` 由"一次摆 32 点"改为**每 tic 在 θ 与 θ+180° 各生成一个拖尾点**，角度按 `1.0/96` 累加并整圈回绕，TID 池 32 槽轮转，退出时 `Thing_Remove` 清池。
- 编译：`/home/user/appfiles/acc-1.60-linux64/acc`（include 路径同 `uh_bars` 那套）→ `src/acs/uh_classes.o`（27377 B，0 error / 0 warning）。
- 打包：`src/` → `out/build.pk3`（16563 项，与旧包条目列表逐项一致；`tools/validate-build-pk3.sh` status=ok）。

### MCP 验收（profile `mm8bdm-v6b-smoke`，地图 MM2DW1）

| 项 | 结果 |
|---|---|
| 启动 | 无 DECORATE/ACS 编译错误，16563 lumps 正常载入 |
| 激活 | `RNCStealthActive_F=1`、alpha=0、invuln/unsolid=1 |
| 点生成 | `give RNCStealthBegin_P` 后立刻出现 `RNCStealthRingDot` |
| 圆弧半径 | 实测各点到激活圆心 **255.7~256.2 u**（半径 256 ✓） |
| 两个交点 | 观测到两段相差 **180°** 的弧（52–74° 与 232–254°）→ θ 与 θ+180° 都在生成 |
| 旋转方向/速率 | 25 tics 后弧段前进 **93.75° ≈ 25 × 3.75°**（每步 1/96 圈，逆时针）✓ |
| 拖尾形态 | 单侧同时 7~8 点、跨度 ≈ 22–26°；相邻点圆心角 3.75° |
| 动画推进 | 同一点 `actor_state`：`MXP1 B(2 tics) → C(2) → D(2) → E(2)`，与 actor 定义一致 |
| 自毁/无堆积 | 连续生成 ~150 tics（约 300 次生成）后同屏仍只有 6~16 点 → `stop` 生效、TID 池正常回收 |
| 本地化与外观 | 生成点 `networkFlags = 16`（NETFL_CLIENTSIDEONLY）、`alpha 0.549988`、`scale 1.5`、`renderStyle Translucent` ✓ |
| 破隐清理 | `take RNCStealthActive_F`（人工）与 `give RNCStealthBreak_P`（真实路径）两种方式，3 tics 内点数 = **0**；alpha 恢复 1、冷却 80→78（每 tic -1）、invuln/unsolid 已移除 |

### 与计划的偏差 / 运行时观察

1. **非 force `Spawn` 的落点剔除比预想更明显**：MM2DW1 出生房间（走廊、地面向北抬升）里同屏只剩 6~10 点，两段弧经常不对称（有时只剩一侧）。原因正是 §3.3 的 `P_TestMobjLocation` + §4.6-5 的"z 取激活地面快照"——圆扫进墙里、或扫到地面抬高处（点仍在 z = 激活地面 + 8）时点被剔除。行为符合设计；若想"任何地形都恒定两条完整尾巴"，把两处 `Spawn` 换成 `SpawnForced`（§4.5-B）。
2. 破隐是**立即**清空（脚本退出时 `Thing_Remove`），不是自然缩小消失——主方案（TID 池）的既定行为；想要 0.23 s 柔和淡出就用 §4.5-A。
3. **成品截图未取到**：smoke 档出生点的视野里当时存活的弧段被墙/栅栏挡住（点不会穿墙显示），而背景窗口的转向输入不稳定。观感是本方案唯一需要人眼判断的验收项，请在自己的客户端确认。
4. 与本次改动无关的既有不一致（未改动）：`#define RNCSTEALTH_COOLDOWN 175`（`rnc_clashman.acs:14`）已无人引用，而 `RNCStealthCooldown` 的 `inventory.maxamount` 是 80（`RNCClashman_W.dec:512`）。

## 11. 调参记录：转速 ×2（2026-09-12，第二轮）

用户确认 §10 观感无误（并已把实现提交为 `533ba4b2`，其中把首帧 `MXP1 B` 换成 `NCXP A`），随后要求加快扫描速度。

### 改动

| 文件 | 改动 | 理由 |
|---|---|---|
| `rnc_clashman.acs:17` | `RNCSTEALTH_RING_STEPS 96 → 48` | 生成间隔已是 1 tic 的下限，转速只能靠"一圈步数"调；每 tic 3.75° → **7.5°**，一圈 48~49 tics ≈ **1.4 s**（原 2.77 s） |
| `RNCClashman_W.dec` | `Scale 1.5 → 2.0` | 相邻点弧距随步长变大到 2π·256/48 ≈ **33.5 u**，点宽由 24 u → 32 u 才能盖住缝隙 |

编译（ACC 1.60）→ `src/acs/uh_classes.o`；重建 `out/build.pk3`（16563 项，条目零差异，`validate-build-pk3.sh` status=ok）。

### MCP 复测

- 同一段拖尾相邻点圆心角实测 **7.5°**（本轮之前为 3.75°）→ 转速确为 ×2；
- 点属性：`scale = 2`、`alpha = 0.549988`、`networkFlags = 16`（NETFL_CLIENTSIDEONLY）、状态 `MXP1 D tics 6`（与 actor 定义一致）；
- 圆弧半径仍为 256（实测各点到激活圆心 255.7~256.2 u）。

### 两个必须知道的耦合（本次实测到）

1. **寿命 × 每 tic 角度 = 单侧拖尾跨度**。用户把每帧时长改成 **6 tics**（寿命 24 tics），在 2× 速度下单侧跨度 = 24 × 7.5° = **180°** —— 两条对跖尾巴正好首尾相接，**圆周会重新被点铺满**（整体仍在旋转，两个头部最大最亮，但不再有"空档"）。
   - 想要彗尾观感，2× 速度下建议每帧 **2~3 tics**（寿命 8~12 tics → 跨度 60°~90°）；4 tics → 120°（两尾接近相接）；6 tics → 180°（接死）。
   - 参考：改速度前 6 tics 时跨度是 24 × 3.75° = 90°，所以那时看起来没问题。
2. **TID 池被超额占用**：32 槽 vs 24 tics 寿命 × 每 tic 2 点 = **48 个同屏点** → 每个 TID 平均被 1.5 个活点共用（实测 `actorsnear` 中 TID 3994/3996/3998 各出现两次，分别为 `MXP1` 与 `NCXP` 两代）。
   - 破隐清理**仍然正确**（`Thing_Remove(tid)` 删除同 TID 的全部匹配，`p_lnspec.cpp:1310-1332`）；
   - 但"一个槽最多一个活点"的前提不再成立。要恢复，就把寿命压到 ≤16 tics（每帧 ≤4 tics），或把池扩到 64 槽（`3970..4033`，需要重新核对 Eden 等 TID 预留，并同步 `RNCSTEALTH_RING_SLOTS`）。

## 12. TID 方案调整：完全不使用 TID（2026-09-12，第三轮）

起因：`RNCSTEALTH_RING_TID 3970..4001` 是硬编码区间，用户担心与其他 mod / 地图的 TID 冲突。

### 核实结论

| 结论 | 出处 |
|---|---|
| `UniqueTID()` 无参调用走**随机分支**，只返回正整数（`pr_uniquetid.GenRand32() & INT_MAX`） | `p_mobj.cpp:3651-3697` |
| `UniqueTID(start, limit)` 才是从 start 起线性找 limit 个；全占用返回 0 | 同上 |
| `DefineReservedTIDRange` 是 v6b/DTADD 的**注册表**，不是引擎功能；**不约束**引擎的 `UniqueTID()` | `DTADDR.acs:296-303`、`8BDT.acs:581-593` |
| 生态惯例：固定 FX TID 段放**负数区**（CBM `-3263..-3200` 等），正因为引擎随机分配器永不返回负数 | `classes-v9gh_/acs_source/cbm_core/CBM_TRAINING.acs:62-68` |
| `tid == 0` 的 actor 不进入 TID 哈希（等于"完全无 TID"） | `p_mobj.cpp:3575-3582` |

**为什么不用 `UniqueTID()`**：① 返回值随机、不可预期 → 想清理就必须把每个点的 TID 存进数组（32~48 个）再逐个删；② clientside 的点在服务端不存在，服务端 `UniqueTID()` 之后完全可能把同一个号发给真实 actor，我们的 `Thing_Remove` 会把它在**该客户端本地**删掉且服务端不会补发（永久不可见）；③ 每 tic 2 次全 actor 列表扫描。负 TID 段（方案 B）能规避 ②，但方案 A 连号都不用。

### 改动（方案 A）

- 删除 `RNCSTEALTH_RING_TID` / `RNCSTEALTH_RING_SLOTS` 两个宏（连同"checked against eden reserve"注释）。
- `uh_rncstealth_ring`：两处改为 `Spawn("RNCStealthRingDot", x, y, z, 0)`（tid 0）；删除 `slot` 轮转与退出时的 `Thing_Remove` 循环；注释说明"停止生成后残余点自行消失"。
- `.dec` actor 注释补充："spawned with NO TID (tid 0) and deletes itself through stop"。
- **`3970..4001` 从此不再被本 mod 占用**（如需它用可直接取）。

**行为变化**：破隐不再是"立即清空"，而是停止生成 + 残余点在一个寿命内缩没（当前 4 帧 × 6 tics = **24 tics ≈ 0.7 s**，观感是尾巴自然收尾）。§11 提到的"32 槽 < 48 活点"超额占用问题也随池一起消失。

### MCP 验收（profile `mm8bdm-v6b-smoke`，地图 MM2DW1）

| 项 | 结果 |
|---|---|
| 生成 | 激活后同屏 `RNCStealthRingDot` 的 TID **全部为 0**；两段弧（半径 256）同时存在 |
| 破隐后 3 tics | 残留 14 点，无新点生成（继续播动画） |
| 破隐后 15 tics | 残留 **2** 点 |
| 破隐后 ~29 tics | 点数 **0**（寿命耗尽自动消失，无需任何清理） |
| 破隐其余路径 | alpha 恢复 1、`UH_00_AlphaPower`/invuln/unsolid 已移除、`RNCStealthCooldown` 正常递减 |
| 编译/打包 | 0 error / 0 warning；`uh_classes.o` 27377 → **27297 B**；`out/build.pk3` 16563 项条目零差异、`validate-build-pk3.sh` status=ok |

## 13. 隐身变身特效：MXP1 BCDE + A_Warp（2026-09-12，第四轮）

需求：boss 隐身时播放一个 `MXP1 BCDE 2` 特效，**用 warp** 模拟"boss 变成 MXP1 然后一起消失"。
选型（用户拍板）：**全场可见**（服务端特效，敌人也看得到这一瞬）。

### 实现

**新 actor `RNCCloakTransformFX`**（`RNCClashman_W.dec`，紧跟 `RNCStealthRingDot`）——**派生自 `BasicGraphicEffect`**，只清掉一个 flag：

```decorate
actor RNCCloakTransformFX : BasicGraphicEffect {
  -CLIENTSIDEONLY          // 唯一与本 mod 其他 FX 不同之处，原因见下
  +FORCEXYBILLBOARD
  +BRIGHT
  States {
   Spawn:
    NCXP A 2 A_Warp(AAPTR_TARGET, 0, 0, 32, 0, WARPF_COPYINTERPOLATION|WARPF_NOCHECKPOSITION)
    MXP1 C 2 A_Warp(...)   // 同上
    MXP1 D 2 A_Warp(...)
    MXP1 E 2 A_Warp(...)
    stop
  }
}
```

（`+NOINTERACTION +NOGRAVITY -SOLID +DONTBLAST`、`Translucent`、`Alpha 1.0`、`Scale 2.5`、`radius/height 2` 全部继承自 `BasicGraphicEffect`。）

- **每帧 A_Warp 把自己贴回 boss 身上**（脚底 +32 = 胸口），`COPYINTERPOLATION` 让渲染位置跟着 boss 的插值一起滑动；boss 边走边隐身时，MXP1 球是"贴在人身上"而不是留在原地。

#### ⚠️ 更正（2026-09-12，用户指出后复核）

本文档早先写过"**不能用 `BasicGraphicEffect`，因为它 `+CLIENTSIDEONLY`，服务端生成即销毁，所以别人看不到**"——**这个结论是错的**，实测与源码都推翻了它：

- clientside-only 的 actor 在**每个客户端各有一份本地副本**：服务端 `DoSpawn` 先发 `SERVERCOMMANDS_SpawnThing` 再把服务端自己那份销毁（`p_acs.cpp:4194-4206`），客户端收到后由 `CLIENT_SpawnThing` 建一份本地 actor（`cl_main.cpp:2809`）。
- 而 `NETWORK_IsActorClientHandled(actor) = (NetworkFlags & NETFL_CLIENTSIDEONLY) || (NetID == 0)`（`network.cpp:1598-1605`）→ 这类副本在客户端**由客户端自己跑状态机与 action 函数**。所以 MM8BDM / 本项目大量 `BasicGraphicEffect` 特效（爆炸 pop、弹道特效）对所有人都是可见的，只是"每人一份、各自本地模拟"。

**真正需要服务端 actor 的原因不是可见性，而是指针**：`SERVERCOMMANDS_SpawnThing` 只带 class/x/y/z(/NetID)（`sv_commands.cpp:1464-1470`），`CLIENT_SpawnThing` 也不会设置任何指针 → 各客户端的副本 `target == NULL` → `A_Warp` 会在 `if (!reference)` 提前返回（`thingdef_codeptr.cpp:5581-5585`），**pop 就钉死在出生点、不会跟着移动中的 boss**。而本项目这次要的正是"A_Warp 跟人"，所以这一份 actor 必须由服务端持有并模拟：服务端跑 warp，再靠 `SERVERCOMMANDS_MoveThingIfChanged`（`thingdef_codeptr.cpp:5684-5685`）把每刻位置广播给所有客户端。

结论：**基类照用 `BasicGraphicEffect`，只把 `+CLIENTSIDEONLY` 清掉**（`-CLIENTSIDEONLY`），既与项目风格一致，又拿到服务端模拟。

#### ⚠️ 更正二（同日晚，用户举 `LeafShieldWep`/`BasicShieldWarper` 反例后复核）

用户指出：`BasicShieldWarper` 也是 clientside 的，也用了 `A_Warp(AAPTR_TARGET, …)`，所以"清掉 `-CLIENTSIDEONLY`"没必要。**反例成立**（v6b `actors/basicactors.txt:172-195`：`+CLIENTSIDEONLY` + `STAR AABBCCDD 1 A_Warp(AAPTR_TARGET, 0, 0, 16, 0, WARPF_INTERPOLATE|WARPF_NOCHECKPOSITION)`），但它能跑通的原因不是"clientside 也能 warp"，而是**生成它的那条 DECORATE 自己带出了指针**：

| 生成路径 | 指针从哪来 |
|---|---|
| DECORATE `A_SpawnItemEx` | 引擎默认 `mo->target = originator ? originator : self`（`thingdef_codeptr.cpp:2476-2479`）；且 `+MISSILE` 时服务端还会 `SERVERCOMMANDS_SetThingTarget` 把指针同步给客户端（`:2692-2694`）。`BasicShieldWarper` 正带 `+MISSILE` |
| ACS `Spawn`/`SpawnForced`（**本项目这条路**） | `DoSpawn` 只发 type/x/y/z/tid/angle，**完全没有指针同步**（`p_acs.cpp:4194-4206`、`sv_commands.cpp:1464-1470`） |

所以：pop 若改成 `+CLIENTSIDEONLY`，各客户端副本 `target == NULL` → `A_Warp` 在 `if (!reference)` 提前返回（`thingdef_codeptr.cpp:5581-5585`）→ **单机跟着人走、联机时客户端上的 pop 钉在出生点不动**（最难查的"单机好联机坏"）。`-CLIENTSIDEONLY` 换来的正是"服务端跑 warp + `SERVERCOMMANDS_MoveThingIfChanged` 广播（`:5684-5685`）"，让 host/客户端行为一致。

**决定（用户确认）：保持 `-CLIENTSIDEONLY`（服务端持有）。** 另一条可行路线记录在此备查：pop 的 `Spawn:` 里调一个 CLIENTSIDE 脚本，扫 `PLN_TID + i` 找带 `RNCStealthActive_F` 的玩家并 `SetPointer(AAPTR_TARGET, 该 tid)`，这样每份客户端副本能本地 warp、服务端不需要该 actor（代价：多一个脚本 + 一次 64 次扫描）。

**未验证项**：listen server 的 host 对"服务端 ACS 生成的 clientside-only actor"是否可见。代码上 `SERVER_DestroyActorIfClientsidedOnly` 会在派发后销毁服务端那份（`sv_main.cpp:5653-5667`），host 渲染的就是服务端世界 → 推测 host 看不到；但用 `-host` 起 listen server 后用 MCP 验证失败（server 模式下 `currentpos`/`give` 全部超时），所以仅作推断。

**新 ACS 脚本 `uh_rncstealth_transform`**（`rnc_clashman.acs`）：

```acs
script "uh_rncstealth_transform" (void) {
  int bosstid = ActivatorTID();   // RNCStealthBegin_P 的 activator = boss
  int fx = UniqueTID();
  if (SpawnForced("RNCCloakTransformFX",
                  GetActorX(0), GetActorY(0), GetActorZ(0) + 32.0, fx, 0)) {
    SetActivator(fx);
    SetPointer(AAPTR_TARGET, bosstid);   // A_Warp 的偏移是"相对 boss 脚底 +32"
    Thing_ChangeTID(fx, 0);
  }
}
```

- 沿用本 mod 既有范式：`SetActivator(u)` + `SetPointer(AAPTR_TARGET, …)`（`weather.acs:18-23`、`shared_warp_and_cone.acs:236-240`）、事后清 TID（`item_effects.acs:44-52`）——所以这个 pop **不留任何 TID**。
- `RNCStealthBegin_P` 在两个守卫**之后**、给 `UH_00_AlphaPowerGiver` **之前**调用它 → 冷却中/已隐身时是 NoOp，不会白放特效。

### 技术依据（已核实）

| 结论 | 出处 |
|---|---|
| `A_Warp` 是**瞬移**到 `reference + offset`，不是逐刻位移；`WARPF_INTERPOLATE/COPYINTERPOLATION` 只改渲染插值 | `thingdef_codeptr.cpp:5640-5680` |
| `WARPF_NOCHECKPOSITION` 必需：否则目标点被 boss 自己的碰撞体挡住会静默失败 | 同上 `:5646` |
| 服务端 `A_Warp` 会广播位移（`SERVERCOMMANDS_MoveThingIfChanged`） | 同上 `:5684-5685` |
| 服务端生成的 `+CLIENTSIDEONLY` actor：服务端只当派发器（发 SpawnThing 后销毁自己那份），客户端各建一份本地副本并**本地模拟** → 全场可见 | `p_acs.cpp:4194-4206`、`cl_main.cpp:2809`、`network.cpp:1598-1605` |
| `SpawnThing` 命令**不带任何指针** → 客户端副本 `target == NULL` → `A_Warp` 静默失效（DECORATE `A_SpawnItemEx` 则相反：自带 `target = originator` 且 `+MISSILE` 会同步） | `sv_commands.cpp:1464-1470`、`thingdef_codeptr.cpp:2476-2479,2692-2694,5581-5585` |
| `SetPointer` 只能改 **activator** 的指针，必须先 `SetActivator(fx)` | `p_acs.cpp:5940-5952` |
| `ActivatorTID()` 取 activator 的 TID（玩家 = 1000+n） | mod 先例 `item_effects.acs:9`、`weather.acs:28` |
| `tid == 0` 的 actor 不进 TID 哈希 | `p_mobj.cpp:3575-3582` |

### MCP 验收（profile `mm8bdm-v6b-smoke`，地图 MM2DW1）

| 项 | 结果 |
|---|---|
| 生成 | `give RNCStealthBegin_P` 后 1 tic 内出现 `RNCCloakTransformFX`；坐标 = boss 的 XY，z = 脚底 + 32 ✓ |
| 指针 | 调试日志实测 `boss=1000 fx=840276687 ptr=1` → `SetPointer(AAPTR_TARGET, 玩家)` 成功 |
| 继承与 flag | `actor_state`（临时保留 TID 观察）：`networkFlags = 0`（`-CLIENTSIDEONLY` 生效）、`target = 1000 LuckyLass`、`renderStyle Translucent`、`alpha 1`、`scale 2.5`、`size 2/2`、状态 `NCXP A(2) → MXP1 C(2)` —— 全部继承自 `BasicGraphicEffect` ✓ |
| 跟随（warp 生效） | 按住前进走动：玩家 y −1182.1 → −1178.6，pop 同步 −1182 → −1179；另一次 x 97.3 → 99.9 / pop 97 → 100 ✓（每 2 tics 一次 warp，其余由插值补平） |
| 无 TID 残留 | 该 actor 在 `actorsnear` 里 TID 恒为 **0** ✓ |
| 自毁 | 4 帧播完自动消失，无残留、引擎日志无 error |
| 观感 | 第三人称（`chase`）截图：boss 身上是一整个白色 MXP1 球 ✓；**第一人称自己看不到**（贴脸 sprite 被近平面裁掉）→ "别人看得见、自己不糊屏"，如需自己也看到可调 z 偏移或 Scale |

### 备注 / 可调项

- 亮度：`+BRIGHT` + Translucent + Alpha 1.0（基游戏 `ExplosionEffect1` 观感）；嫌亮就去 `+BRIGHT` 或降 Alpha。
- 尺寸：`Scale 2.5` = 40 单位；想更夸张可 3.0。
- **z 偏移在两处**：ACS 的 `+ 32.0` 与 actor 里 `A_Warp(..., 32, ...)` 必须一致，改一处要改两处。
- 破隐时目前**不放**特效（需求只说"隐身时"）。要破隐也来一发，就在 `RNCStealthBreak_P` 的 `BreakStealth:` 里加同一行 `ACS_NamedExecuteAlways("uh_rncstealth_transform", 0)`。
- 测试注意（本轮踩到）：**不要在实例运行期间重建 `out/build.pk3`**——引擎会边跑边读 ZIP，热替换会导致 `Corrupt zlib stream` 刷屏；而且 ACS 只在**启动时**加载，改了 `.acs` 必须重启实例（`load_map` 不会重载库）。
