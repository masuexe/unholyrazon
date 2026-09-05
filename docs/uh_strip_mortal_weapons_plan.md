# RemoveWeaponsOfMortals_P 注册表化改造 —— 实施方案

状态：**v3 —— P1a/P1b/D3/P2 已实施并通过 MCP 冒烟+端到端验证；P3（退役旧 246 行 take 清单）与 P4（Eden 清理挂钩）待办** · 日期：2026-09-05
范围：把 `RemoveWeaponsOfMortals_P`（`src/actors/inventory/bosswepbase.dec`）的
246 行硬编码 `A_TakeInventory` 改为注册表驱动，使现在遗漏的武器和未来第三方
modder 的武器自动被覆盖。

**实施落地差异（相对 v2 草案）**：
- 入口 actor 已重命名 `RemoveSurvivorWeps_P`；Pickup = 旧清单（暂留）+
  `ACS_NamedExecuteWithResult("uh_StripSurvivorWeps")`（P3 后旧清单退役）。
- DTADD 兜底读取不用 `#import "8bdt.acs"` 进 `unholy`：**8bdt 与 uhdt 都定义
  `getItemName`/`getItemActor`，ACC 标识符不区分大小写，单模块同时 import
  两者无法编译**（v6b 已编译的 CORE8BDT.o 钉死了 8bdt 侧名字）。改为 glue
  脚本 `uh_GetDTADDWepActor_S` 放进 **UH_TOOLS**（唯一 import 8bdt 的 UH 库，
  `systems/tools/dtadd_query.acs`），经 `uh_dsw_out_str` 临时 cvar 回读。
- 新增 UHADD cvar 时**必须同步在 `src/CVARINFO` 注册**（`local noarchive
  string uh_dsw_actor/uh_dsw_out_str`）：未注册的名字落入 Zandronum 动态
  cvar 池，与 bot 系统等动态创建的 cvar 互相串扰（实测读回 bot 名
  "MechaDragon"）。这也是既有 `uh_ds_*`/`uh_db_*` 都注册在 CVARINFO 的原因。
- `uh_define_vanilla_survweps` OPEN **故意不加 UHInPlay 守卫**（仿 survivors
  的 `_cs` 孪生）：注册必须在任何地图模式下完成，仅靠 count 守卫幂等。

**v2 变更**：
- D1 已拍板——Eden、Crystrap 注册为 survivor id **59、60**（KEYCONF 顺序一致）。
- 命名统一：原方案中的 "mortal weapon" 注册表/API 全部改名为 **survivor weapon**
  （`DefineSurvivorWep` 等）；新 strip 脚本名 `uh_StripSurvivorWeps`；入口
  actor 建议随 P2 机械重命名为 `RemoveSurvivorWeps_P`（见 P2 步骤 3）。
- take 数量：strip 一律 `TakeInventory(actor, 1)`（武器 `maxamount 1`，
  单次 take 即销毁；ACS 端 amount ≤ 0 是 no-op，不能省略）——见 §4。

---

## 1. 背景与已核实的问题

### 1.1 现状

`RemoveWeaponsOfMortals_P` 是一个 `CustomInventory`，Pickup 状态里逐个
`A_TakeInventory` 移除 survivor 武器。调用点共 3 处（均为"先 strip、后发
boss/morph 武器"的顺序）：

| 调用点 | 流程 |
|---|---|
| `src/actors/inventory/bosswepbase.dec:33` | `BasicBossItem`（survivor → boss 化） |
| `src/acs_source/unholy/uh_bosscore.acs:263` | `uh_DemoneyeMorph`（→ Demoneye） |
| `src/acs_source/systems/tools/morph_helpers.acs:15` | `uh_shinyclassmorpher`（→ Shiny 形态） |

### 1.2 引擎约束（已核对 Zandronum 源码）

- DECORATE `A_TakeInventory` 与 ACS `TakeInventory` 都经 `FindInventory()`
  **精确类名匹配**（`thingdef_codeptr.cpp` 的 `DoTakeInventory`、
  `p_acs.cpp:1401` 的 `DoTakeInv`）。没有通配符、没有子类/基类匹配、没有
  枚举接口。
- 唯一的通用原语是 ACS `ClearInventory`（`PCD_CLEARINVENTORY`），但它会把
  ClassBase 标记栈（速度/跳跃/保护/weakness 等）一并清掉；`BasicBossItem`
  的现有流程刻意保留这些状态，因此不可用。

**结论：清单不可能消灭，只能换一个"自动增长"的宿主。**

### 1.3 现有清单已证实的遗漏（本 mod 自己的职业）

以下 `<Class>_W` 均已定义（`src/actors/classes/survivors/`），但**不在**
`RemoveWeaponsOfMortals_P` 里，boss 化/Demoneye/Shiny 转换后不会被移除：

| 遗漏 | v2 修复途径 |
|---|---|
| `BusterMistress_W`（id 4）、`CaptainAss_W`（id 42）、`LuckyLass_W`（id 6）、`Rameses_W`（id 32） | survivor 表 + 命名推导（P2 自动覆盖） |
| `Eden_W`、`Crystrap_W` | 注册为 survivor id 59/60 后同上（P1） |
| `Eden118_W`、`Eden678_W` | survivor-wep 显式注册（P1，见 §5） |

---

## 2. 命名约定审计（"各职业 weaponname 是否符合约定"）

对 KEYCONF 全部 61 个职业 + 各武器定义做静态审计，结论：

| 分类 | 约定情况 | 处理 |
|---|---|---|
| 59 个已注册 survivor（id 0–58） | 全部存在 `<Class>_W`；`_W1.._W9` 槽位变体全部符合家族规则 | 注册表 + 命名推导覆盖 |
| Eden（注册为 59） | `Eden_W` 符合；**`Eden118_W`、`Eden678_W` 以道具编号命名**（C118 Brimstone / C678 CSection），**不匹配 `_W1.._W9` 槽位规则** | `Eden_W` 走推导；118/678 显式注册 |
| Crystrap（注册为 60） | `Crystrap_W` 符合 | 走推导 |
| `FrostBiteSpike_W` | 是 `BasicProjectile` 弹体（`FrostBite_W.dec:489`），不是背包武器 | 排除 |
| `src/actors/classes/bosses/` 下的 `*_W`（ArchArcanist_W、MakeAGoodZero_W、FinalSampi_W、FBeast_W、SinfulBusterExpert_W、BalladeGB_W 等） | 全部是 **boss 武器**（`BaseUnholyBossWep` 家族），本就不该被 strip | 排除 |
| `DecoyCopy_*` / `DecoyShinyCopy_*` | DecoyBot 克隆体内部武器，不在本体背包 | 排除 |
| Shiny 变体 `*_Shiny_W` | Shiny 转换在 strip 之后才发武器 | 排除 |

命名推导（`<Actor>_W`、`<Actor>_W1.._W9`）是**运行时按名字
`CheckInventory`**，不要求源码定义可静态发现（PartyBomber_W、Raider_W2、
SumoWrestler_W 等运行时同样被推导覆盖）。

---

## 3. 现有 Define 架构的覆盖能力（v2：配合 D1 后可以覆盖 Eden）

三个既有注册来源与 strip 需求的比对（以 `RemoveWeaponsOfMortals_P` 现有
246 项为基准）：

| 注册来源 | 位置 | 对现有清单的覆盖 | 对 Eden/Crystrap |
|---|---|---|---|
| Copywep 注册表 | `copy_weapon_registration.acs`（库 `uh_copyweps`，表在 `uhdt`），`DefineCopyWep` | **103/103 个 `*WepU` 全覆盖**，Nega 系与 Qwant 系（FireBlastWep 等）全覆盖 | 不适用（非 copy 类） |
| Survivor 注册表 + 命名推导 | `uh_survdefs.acs`，`DefineSurvivor(id, actor, name, mugshot)` | 覆盖全部已注册职业的 `<Class>_W`/`_W#`（顺带修复 §1.3 的 4 个现有遗漏） | **注册 59/60 后**：`Eden_W`、`Crystrap_W` 走推导 |
| DTADD 武器注册表（v6b `core8bdt`，可选兜底） | `DefineWeapon` → `core_DefineWeapon_S`，`max_weapons_global`/`getWeaponActor(i)` | 第三方走 `DefineWeapon` 的武器自动纳入 | 不适用 |

**结论：D1 落地后，唯一推不出的只剩 `Eden118_W` / `Eden678_W`**（道具编号
命名，结构性缺口），用 2 行 survivor-wep 显式注册解决。

另有一个顺带发现：`RockSlideWep`（`BaseQwantWep` 家族，
`qwant_copyweps/RockSlide.dec`）**没有**出现在 copywep 注册表里——
它今天靠硬编码清单被 take，注册表化后会漏；这个缺口可能同时影响 Qwant
的复制轮换/弹药系统，建议单独修复（见 §8 D3）。

### 3.1 Eden / Crystrap 注册的影响面（已审计）

survivor 表的在库消费方只有三处：

- `uh_events.acs:389`（`FindSurvivorByActor`，事件里 boss data → survivor id）
- `uh_display.acs:291,320`（`GetSurvivorName` / `GetSurvivorMugshot`，HUD 显示）

未发现硬编码 `0..58` 的遍历。注册后 **Eden/Crystrap 的 boss 化形态在事件与
HUD 中获得正确的名字与头像**（当前是查表失败的退化路径），属修复而非风险。

注册所需资产已就绪：`ICN59`/`ICN60` 与 `UCNUM_59`/`UCNUM_60`
（`src/TEXTURES.classes.faces:373-375`）、`EdenShiny`（`Eden.dec`）、
`CrystrapShiny`（`Crystrap.dec`）。**唯一缺口：`TEXTCOLO` 无 `UH59`/`UH60`**
（`src/TEXTCOLO` 止于 `UH58`），P1 需补两段配色（配色值待定，见 P0）。

---

## 4. 目标架构

```
RemoveSurvivorWeps_P（原 RemoveWeaponsOfMortals_P，入口机制不变）
  Pickup: ACS_NamedExecuteWithResult("uh_StripSurvivorWeps")
                 │
                 ▼
  uh_StripSurvivorWeps（unholy 库，uh_bosscore fragment）
    1. copywep 全表遍历        → TakeInventory(actor, 1)
    2. survivor 表遍历（0..60 + 自定义段）→ 对每个 survivor actor：
                                   CheckInventory/Take <Actor>_W, <Actor>_W1.._W9
    3. survivor-wep 显式表遍历 → TakeInventory(注册名, 1)
    4. （可选，D2）DTADD core8bdt 表遍历 → 兜底 DefineWeapon 注册的第三方武器
```

- **take 数量语义**：ACS `TakeInventory` 的 amount ≤ 0 是 no-op
  （`p_acs.cpp:1443` 直接 return），必须传 1；Weapon 默认
  `inventory.maxamount 1`，背包内 Amount 为 1，`DoTakeInv` 扣减后 ≤ 0 即
  `Destroy()`——take 1 即完整移除。边角：若未来出现 `maxamount > 1` 且
  同持多份的堆叠武器，需对该项改回 take-all（旧 DECORATE 清单省略 amount
  即 take-all 语义）。

- 三个调用点**机制零改动**（仍是 give 入口 actor；若采纳重命名则仅改字符串）。
- 各来源重叠无害：对不存在的物品 `TakeInventory` 是 no-op，天然幂等。
- 顺序安全：三个调用点都是 strip 之后才发 boss/morph 武器；boss 武器
  （`BaseUnholyBossWep` 家族）不在任何被遍历的注册表中。
- 网络安全：`TakeInventory` 服务端执行自带同步
  （`SERVERCOMMANDS_TakeInventory`，见 `DoTakeInv`）；同 Pickup 状态里的
  `uh_NoHitStunplayer` 等已采用同一执行模型。

---

## 5. P1：注册变更（含 D1 落地）

### 5.1 Survivor 注册 59/60

`src/acs_source/classes/survivors/definitions/uh_survdefs.acs` 的
`RegisterVanillaSurvivors()` 追加两行（id 与 KEYCONF 顺序一致）：

```
DefineSurvivor(59, "Eden",     "\c[UH59]Eden",     "C@ICN59");
DefineSurvivor(60, "Crystrap", "\c[UH60]Crystrap", "C@ICN60");
```

配套：

- `src/TEXTCOLO` 新增 `UH59`（Eden）、`UH60`（Crystrap）两段配色，
  格式仿 `UH51..UH58`（主色 + 亮色 + Console 段）；**具体色值待定**（P0）。
- `uh_survdefs.acs` 头注释 `stable id 0..58` → `0..60`。
- `_includes/mod_api/uhadd.acs` recipe 注释中两处 "KEYCONF append is 59+"
  → **61+**（第三方职业段顺延）。
- Shiny 形态无需动作：`EdenShiny`/`CrystrapShiny` 已定义，注册后走既有
  `actor + "Shiny"` 约定（Eden 另有 `rz_EdenShinyMinit` 特判，不变）。

### 5.2 survivor-wep 显式注册表（唯一的新表）

仿照 UHADD 既有模式（cvar 暂存参数 → named script → UHADDR handler，
参照 `DefineSurvivor`/`uh_DefineSurvivor_S`）：

- UHDT（`_imports/uhdt.acs`）新增表：`uh_survwepstr[UH_MAX_SURVWEP]`
  + `uh_survwepcount`（`UH_MAX_SURVWEP` 建议 256），失败码
  `UHSURVWEP_FAIL`。
- UHADD（`_includes/mod_api/uhadd.acs`）新增：
  `DefineSurvivorWep(str wepActor) : int`（重复注册返回既有行，幂等），
  读取器 `UH_GetSurvivorWep(i)` / `UH_SurvivorWepCount()`。
- UHADDR（`corescripts/api_handlers/uhaddr.acs`）新增
  `uh_DefineSurvivorWep_S` 等 handler。

### 5.3 内置注册的落点（避免 LOADACS 变更）

放在 `uh_survdefs.acs`（库 `uh_survdefs` 已在 LOADACS，已
`#include "uhadd.acs"`，与 `RegisterVanillaSurvivors()` 同处最自然）：

- 新增 `RegisterVanillaSurvivorWeps()`，由新 OPEN 脚本
  `uh_define_vanilla_survweps` 调用（带 `IsSurvivorDefined(0)` 防重入，
  仿既有脚本）。仅服务端注册即可——目前只有 strip（服务端）读该表；
  若未来出现 CLIENTSIDE 消费方再补 OPEN CLIENTSIDE 孪生脚本。

初始内容（= D1 后仍推不出的全部 survivor 侧武器）：

```
Eden118_W
Eden678_W
```

### 5.4 addon 配方（UHADD 注释增量）

在 `uhadd.acs` 的 recipe 注释中补一节：第三方 survivor 若武器命名不符合
`<Class>_W`/`_W#` 家族规则（自定义形态变体名），在现有
`your_define_survivors` OPEN 脚本中追加
`DefineSurvivorWep("YourWepVariant")`。符合约定的武器无需任何额外注册。

---

## 6. Eden 专项

### 6.1 武器（第一阶段覆盖）

- `Eden_W : BaseMM8BDMWep_UH`（`src/actors/classes/survivors/Eden_W.dec`）
  → 注册 59 后由命名推导覆盖。
- `Eden118_W : Eden_W`、`Eden678_W : Eden_W` → survivor-wep 显式注册
  （结构性必需，见 §5.3）。

### 6.2 残留状态清理（第二阶段，独立于武器目标）

武器移除后 Eden 仍会残留的状态，建议引入**每职业 strip 清理挂钩**一并解决
（仿既有 `SetBossMorphSetupByActor(actor, script)` 的按 actor 挂钩模式）：

- API：`DefineSurvivorStripCleanup(str survActor, str cleanupActor)` ——
  注册一个 `CustomInventory` giver，`uh_StripSurvivorWeps` 末尾按当前玩家
  职业给予。
- Eden 的 cleanup giver 内容（多数积木已存在）：
  - `A_GiveInventory("ResetEdenAttr_P")`（已存在，清 8 项 Eden*Attr）；
  - take `EdenToyAmmo`、`EdenTearCoolDown`、`BobHeadFlag`、`BobHeadLeft_F`、
    `DuoBusterFlag`、C 系道具标记（C42Flag/C356Flag/C358Flag/C678Flag 等，
    按 `main_items/`、`alt_items/` 清单核对）；
  - 染色复位（`EDEN_DYE 20060` 系翻译，`eden_runtime.acs`）；
  - C396 Ventricle Razor 端点回收（固定 TID 段 1500–1663，见
    `eden_tid_reserve.acs`）与 familiars（`eden_familiars.dec`）——
    复用/补全 `eden_helpers.acs` 中的回收路径。
- 该挂钩同时是未来其他职业残留（如 DecoyBot 标记现在写在
  `BasicBossItem` 里的内联 take）的收敛点；现有内联项**不要求**本期迁移。

---

## 7. 行为变化清单

| 变化 | 影响 |
|---|---|
| 新增被 take：`BusterMistress_W`、`CaptainAss_W`、`LuckyLass_W`、`Rameses_W`、`Eden_W/118/678`、`Crystrap_W` | 修复遗漏；这些职业 boss 化/Demoneye 后不再残留原武器（预期行为） |
| Eden/Crystrap 进入 survivor 名册消费方（uh_events / uh_display） | 事件与 HUD 中获得正确名字/头像（当前为查表失败）；若设计上不希望两者进入未来新增的"全 survivor"类消费方，需在消费方显式排除 |
| DTADD 兜底（若采纳 §8 D2） | 可能 take 到" survivor 直接持有 v6b 原版武器"的边角情况——本就是转换应移除的，属修复 |
| 入口 actor 重命名（若采纳） | `RemoveWeaponsOfMortals_P` → `RemoveSurvivorWeps_P`：改 1 处定义 + 2 处 ACS 字符串 + 1 处 DEC give，纯机械 |
| 其余 | 无；现有被 take 集合是三来源的子集（已静态比对） |

---

## 8. 决策点状态

- **D1（已拍板 v2）**：Eden、Crystrap 注册为 survivor id 59/60。
  KEYCONF 顺序一致；第三方职业段顺延为 61+；TEXTCOLO 补 `UH59`/`UH60`。
- **D2（待定）**：是否纳入 DTADD（core8bdt）兜底遍历？
  收益：第三方职业直接 StartItem v6b 注册武器的边角场景；代价：Unholy 的
  `v6b_overrides/_imports/8bdt.acs` 必须与 v6b 编译布局保持同步（现有
  override 已承担该约束）。**建议：纳入**，但做成独立开关便于排查。
- **D3（已查明，v2.1）**：`RockSlideWep` **不是缺注册**——注册表里有
  `DefineCopyWep(UHCOPY_QWANT, UHCOPY_QWANT_ROCK, "RockslideWep")`
  （`copy_weapon_registration.acs:135`），只是类名大小写写错。运行时无影响：
  注册去重（`FindCopyWepByKindActor`/`FindCopyWepByActor`）、regen 查找、
  MegaCopy 伤害 id 的 stem 匹配均已是 `StrICmp`/`StrIStartsWith`，引擎的
  Give/Take/类查找也原生大小写不敏感。修复 = 把注册串改成规范名
  `RockSlideWep`（显示/调试/静态审计一致性）。
  **大小写策略结论（v2.1）**：API 层不需要再改；新增
  `DefineSurvivorWep` 的去重沿用 `StrICmp`（与 `FindCopyWepByKindActor`
  一致），注册串一律书写规范类名；damage alias 表的 `StrCmp` 保持精确
  匹配（两侧均为本仓库字面量，故意严格）。

---

## 9. 分阶段实施步骤

- **P0 审计确认**：
  - 与策划/记录核对 §1.3 的遗漏确属 bug 而非特判；
  - 核对 Eden C 系道具标记全集（`main_items/`、`alt_items/`）；
  - 选定 `UH59`/`UH60` 配色（Eden "Repent your sins" / Crystrap
    "ASCENSION" 主题，可参考各自类目配色先例）。
- **P1 注册**：
  1. `uh_survdefs.acs`：`DefineSurvivor(59/60, ...)` 两行 + `TEXTCOLO`
     `UH59`/`UH60` + 注释与 addon 段修正（§5.1）；
  2. UHDT 表 + UHADD API + UHADDR handler + `RegisterVanillaSurvivorWeps()`
     （2 行初始内容，§5.2/§5.3）；
  3. UHADD recipe 注释补 `DefineSurvivorWep` 一节（§5.4）。
- **P2 strip 脚本**：
  1. `uh_StripSurvivorWeps` 落在 `unholy` 库 `uh_bosscore` fragment
     （`#import "uhdt.acs"`，D2 采纳则加 `#import "8bdt.acs"`）；
  2. 入口 actor Pickup 改为一行 ACS 调用；旧 246 行 take **暂留**（双保险）；
  3. （随 P2 机械重命名）入口 actor → `RemoveSurvivorWeps_P`，同步 3 处
     调用点字符串。
- **P3 并行验证后退役旧清单**：确认无回退后删除 246 行 take（保留
  `BasicBossItem` 里非武器的标记/计数器 take 原样不动）。
- **P4 Eden 清理挂钩**（§6.2，独立 PR）。

## 10. 验证计划（MCP 冒烟矩阵）

| 用例 | 断言 |
|---|---|
| `mm8bdm-v6b-smoke` 启动 | 无 ACS/DECORATE 编译错误（`get_startup_errors`） |
| P1 注册 | `FindSurvivorByActor("Eden")==59`、`("Crystrap")==60`；HUD 名字/头像（UCNUM_59/60）正常；`\c[UH59]`/`\c[UH60]` 不再退化 |
| Boss 化（`BasicBossItem`） | 背包无任何注册表武器；boss 武器正常在；ClassBase 标记（速度/跳跃/保护）不受影响 |
| `uh_DemoneyeMorph` / `uh_shinyclassmorpher` | 同上；Shiny 武器在 strip 之后正常给予；Eden/Crystrap 的 Shiny 形态转换正常 |
| 针对性回归：Rameses / BusterMistress / CaptainAss / LuckyLass / Eden / Crystrap | 转换后 `CheckInventory(<Class>_W)` == 0（旧行为下为 1，即本方案修复点）；Eden 转换后另验 `Eden118_W`/`Eden678_W` == 0 |
| Eden 转换 | EdenToyAmmo/Attr/familiars 处置符合 P4 验收（第二阶段） |
| 第三方模拟 | 临时测试 pk3 注册 `DefineSurvivor` + 非约定名武器 + `DefineSurvivorWep`，转换后武器被 take；addon 段 61+ 不与 59/60 冲突 |
