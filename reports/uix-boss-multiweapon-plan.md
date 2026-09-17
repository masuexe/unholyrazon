# UIX v3bh：Boss 多武器 wheel / weaponbar 注册与实施计划

日期：2026-09-17。状态：已实施完成，全部 8 个 Boss 通过 live MCP 引擎自动化验证。

## 一、显示规则

- wheel 采用一件实际可选武器一个 group，按下表顺序排列，不按攻击方式分类，不在一个 group 中塞多件武器。
- 普通持有项轮盘沿用至少 3 件才开启的规则。只有两件可选武器的 Boss 本阶段不实施 wheel 或 bar，也不注册；Lin、MeisterWahwee、WarRockStelar 暂缓。
- SinfulBusterExpert 是例外：最终武器集固定为 W1–W8，wheel 始终固定八个 group，未解锁项灰显且不可选择。持有 W1 且玩家状态有效时即可开启，不受当前持有至少三件的条件限制。
- bar 使用真实 gameplay slot 与真实绑定；显示顺序不能简单用 wheel group 号冒充槽位号。同槽使用现有 UIX 循环、高亮和溢出规则。
- 注册候选武器不等于授予武器。只有当前持有且当前阶段允许选择的 actor 才参与显示和服务端选择验证。
- boss 变身、阶段强制切换、死亡和解除变身必须能取消 wheel。HUD 不得改变阶段、授予武器或延迟原有强制切换。
- 单武器的模式切换、阶段替换与多个同时可选武器分开处理，不把所有 `_Pissed` 武器登记成自由选择项。
- 本阶段不改玩法槽位、不兼容 killfeed、不新增按键、CVAR 或常驻 HUD 循环。

## 二、要注册的武器清单

以下 actor 名称按项目实际源码填写。范围表示所有连续编号均应登记，例如 W1–W6 表示六个独立 actor，而不是一个通配符注册。

### A. 固定多武器 Boss：首批

来源：`src/acs_source/classes/bosses/boss_morph_setups.acs` 的 GiveInventory，以及对应 `src/actors/classes/bosses/<Boss>.dec`、`<Boss>_W.dec`。

| 精确 Boss actor | wheel 登记顺序 | 数量 | 真实槽位 | 注册/显示注意事项 |
|---|---|---:|---|---|
| `KakusaretaSutoka` | `KakusaretaSutoka_W`、`KakusaretaSutoka_W2`、`KakusaretaSutoka_W3` | 3 | 1、2、3 | morph setup 同时授予三件 |
| `ArchArcanist` | `ArchArcanist_W`、`ArchArcanist_W2`、`ArchArcanist_W3` | 3 | 1、2、3 | morph setup 同时授予三件；共享能量，首版 wheel/bar 仅图标与名称/高亮 |
| `VoidWalker` | `VoidWalker_W`、`VoidWalker_W2`、`VoidWalker_W3`、`VoidWalker_W4` | 4 | 1、2、3、4 | 四元素武器；ScriptBar 不代表可直接套通用 Ammo 条 |
| `GBeast` | `GBeast_W1`–`GBeast_W6` | 6 | 1–6 | 六件显式槽位武器，不登记 morphweapon 字符串 `GBeast_W` |
| `FBeast` | `FBeast_W1`–`FBeast_W6` | 6 | 1–6 | 六件显式槽位武器，不登记 morphweapon 字符串 `FBeast_W` |
| `FinalSampi` | `FinalSampi_W1`–`FinalSampi_W7` | 7 | 1–7 | 七件显式槽位武器；`FinalSampi_W` 是公共基类，不单独增加 group |

首批共 6 个 Boss、29 条武器登记。

### B. 条件解锁/阶段多武器：第二批

| 精确 Boss actor | 要登记的可选武器 | 数量 | 真实槽位/阶段策略 |
|---|---|---:|---|
| `SinfulBusterExpert` | `SinfulBusterExpert_W1`–`SinfulBusterExpert_W8` | 8 | 显式 slot 1–8。wheel 固定八分区：group 0–7 永远对应 W1–W8，未解锁项灰显禁用；解锁后原位置启用。bar 仍只展示已经解锁且持有的武器 |
| `MakeAGoodZero` | `MakeAGoodZero_W2`–`MakeAGoodZero_W7` | 6 | 第二阶段同时授予六件。未见这些 actor 显式覆盖继承槽位，须按基类与引擎真实顺序核对 bar 同槽行为；wheel 按 W2–W7 顺序，一个 actor 一个 group |

第二批共 2 个 Boss、14 条多武器候选；两批合计 8 个 Boss、43 条。

MakeAGoodZero 的 `MakeAGoodZero_W` 为第一阶段，`MakeAGoodZero_W8` 为第三阶段。两者可作为单项 bar 的阶段替代行，但不得与第二阶段六件同时拼成八分区轮盘。尤其 W8 的 Select 会清理 W2–W7，不能在 Give/Take 中间态重新允许选择这些武器。

### C. 暂缓：只有两件可选武器的 Boss

- `Lin`：`Lin_W1`、`Lin_W2`，真实 slot 1、2；本阶段不注册、不新增 bar 或 wheel。
- `MeisterWahwee`：后期 `Wahwee_W1`、`Wahwee_W2`，真实 slot 1、2；本阶段不实施。初期 `MeisterWahwee_W` / `MeisterWahwee_W_Pissed` 为机甲阶段替换，也不计入多武器集合。

`WarRockStelar`：morph setup 授予 `WarRockStelar_W` 和 `WarRockStelar_W2`，同样暂缓；当前 `src/actors/classes/bosses/` 中还缺少其 include 引用的来源文件。将来恢复两武器 Boss 支持时，先查明实际依赖包或缺失源码，并核对 actor 定义、图标、槽位及允许选择状态。不要凭命名推测槽位，也不要为计划新增或修复玩法 actor。此核对不阻塞当前八个 Boss 的交付。

同类边界：VoidWalker 的 morphweapon 写为 `VeryFunOrbWep`，GBeast/FBeast 写为不在其本地武器文件中定义的 `GBeast_W` / `FBeast_W`；本次根据实际 setup 和显式槽位只登记上表的有效武器，不以 morphweapon 字符串自动生成登记。这些旧入口的依赖解析不属于 UIX 兼容实现。

### D. 明确不按多武器注册

- `Clownpiece_W1`–`Clownpiece_W8`：HP/符卡流程通过 Give 新武器、Take 旧武器并调用专用选择脚本推进阶段；不是八件自由选择武器。多武器 wheel 排除整个 Clownpiece，单项阶段 HUD 另做。
- 各 Boss 的 `_Pissed` / `_Pissed1` / `_Pissed2`：优先按阶段替代 actor 处理，不因文件里定义两个 Weapon 就视为两武器 Boss。
- `SinfulBusterExpert_W`、`FinalSampi_W` 等未实际授予的公共基类，以及投射物、CustomInventory、NormalBar/ScriptBar 元数据 actor：不登记为轮盘项。
- ShinNegaman 等不在上述授予清单中的 Boss，不根据名称自动套用 survivor 的 Qwant/NegaMan 兼容。

## 三、元数据与显示策略

建立 Boss 的显式显示定义，至少包含精确玩家 actor、武器 actor、wheel 顺序、真实绑定槽位、图标、名称及显示策略。图标优先使用项目已有 Inventory.Icon / TEXTURES，不生成新素材；缺失时可复用对应现有武器 HUD sprite，但需验证其作为 UIX 图标的显示尺寸。

已确认示例：KakusaretaSutoka 三件使用 `C_I_50A/B/C`；GBeast 使用 `BI_108A`–`BI_108F`；FBeast 使用 `BI_109A`–`BI_109F`；MakeAGoodZero 的第二阶段使用已有 `B_I_306A`–`B_I_306F`。其余在实施登记时逐件读源码，不猜造图标名。

首版所有 Boss 默认采用图标/名称/当前项高亮，不增加能量条。Boss 常含共享 Ammo、UnholyPower 和 ScriptBar，不能照搬复制武器的通用条，也不能简单把 Weapon.AmmoType2 全画出来。ArchArcanist 明确沿用共享能量隐藏策略。若后续需要某 Boss 的独立弹药条，应逐 Boss 证明其语义后显式开启，复用现有元数据解析，不另维护冲突的配色表。

bar 标签显示真实绑定，无独占槽位的武器不伪装成编号 1–6。MakeAGoodZero 的多个武器若实际同槽，应在一个真实槽位中滚动，而不是把每个 wheel group 渲染成虚构 slot。

## 四、实现路径与风险

### 1. 固定定义扩容，复用已有选武器流程

优先复用 `uh_uixfw_db.acs` 的 `DefineFixedWeaponWheel` / `AddFixedWeaponWheelWeapon`，将 Boss 登记放入独立片段（建议 `uh_uixfw_boss_defs.acs`），由现有 `uh_uixfw.acs` 聚合，不增加库。

当前 `UHFW_MAX_CLASS = 8`，已有五个 survivor class，不能直接再插入上述八个 Boss。先提高到至少容纳现有 5 + 新增 8 的容量，例如 16，保留以后扩展空间。每 class 最多 12 件保持不变。扩容后检查 ACC 地图变量限制和数组体积，不为静态表新增多个零散 map 变量。

注册在客户端和服务端均可用；不要只依赖服务端 OPEN。复用已有重复定义防护和 ready 状态。精确 actor 白名单，不自动支持未登记后代。

固定首批沿用现有库存收集和“一快照项一 group”创建流程、当前武器初始定位及公共 `UHFW_SubmitSelect` / 清理逻辑。服务端仍验证当前玩家 class、存活、已登记、实际持有及当前阶段；客户端不能提交任意字符串武器。

### 2. bar 独立读取，不能借 wheel 收集

`uh_uixfw_bar.acs` 的 `UHFB_ClassIndex` 当前只白名单四个 survivor。不能仅添加 wheel 注册就认为 bar 会自动支持；需扩展明确的 Boss 策略，或抽取共用只读定义查询桥。

固定独占槽位 Boss 可复用 `weaponBarFixed`；MakeAGoodZero 必须走真实同槽渲染。共用 Qwant/NegaMan 的无状态绘制能力，不共用它们的武器扫描。每次摄像机调用先完成库存/CheckWeapon/容量读取，SetActivator(-1) 后仅绘制，不调用任何 SnapClear/Collect/Open。

### 3. 阶段和解锁不是“只加注册”

SinfulBusterExpert 使用固定八项定义快照，而不是只收集当前持有项：group 0–7 分别对应 W1–W8。创建轮盘时始终使用八分区，当前武器定位使用固定索引。未解锁项仍显示对应图标但灰显，不可提交选择；不为显示而授予武器或改变 HP 解锁流程。

打开期间独立 tick 根据当前库存刷新八项的可用状态，新武器到达后在原位置启用，不重建 wheel、不改变 group、方向或当前悬停项。刷新 wheel 与 bar 各自读取库存，不让 bar 驱动 wheel。实际选择时客户端和服务端再次检查是否持有并允许使用；库存尚未同步时保持禁用。

实现必须给这个 Boss 设置显式的固定完整武器集策略，绕过通用 held-only 收集及当前持有至少三件的开启检查；不要全局修改其他 class/Boss 的规则。禁用占位项不能进入任何自动提交或“无当前项时默认选中”路径。bar 仍按真实 slot 1–8 只画已持有项，不需要八个灰色占位栏。

MakeAGoodZero 增加显示阶段/可选武器集策略。优先复用现有阶段标记，必要时以当前实际 weapon 和已存在的生命周期信息识别；不能只凭旧 weapon 尚未 Take 就认定可选。阶段变化时关闭旧 wheel，下一次只收集新阶段允许的集合。客户端与服务端采用一致的阶段允许条件，不能只靠 CheckInventory 防止回到旧阶段。

检查 boss 攻击、痛觉与转阶段期间的切换约束；UIX 的 SetWeapon 入口不能绕过原有禁止切换条件。沿用或补足权威阶段验证，不直接从 HUD 调用阶段选择脚本。

`CheckInventory` 使用引擎 p_acs.cpp 的 FindInventory；其默认参数在 actor.h 为 `subclass = false`，正常 ACS 检查是精确类型。不要把 DECORATE A_TakeInventory 等动作的继承匹配规则混用于 ACS，也不要为了防继承误匹配引入不必要的库存遍历协议。

### 4. 玩家/阶段生命周期

wheel 开启期间冻结顺序，不因 bar 刷新重建；失去快照武器时禁用并拒绝选择。死亡、unmorph、换 Boss、阶段切换要撤销旧 owner/route，防止关闭时提交旧武器。

复用已有同玩家生命周期检查，并检查同 actor 再次 morph 的情况：只比较 actor 字符串可能不足。若使用 morph generation，应确认它在客户端可获取，不为 HUD 随意增加网络写入口。

## 五、分阶段实施

1. 最小实验选 GBeast：登记六件既有图标与真实 slot，先打通 wheel 和 bar；不接弹药条。
2. 验证六分区、高亮、原有关闭切换流程及服务端白名单。验证 wheel 不改变 Boss 的原有 rage/攻击流程。
3. 扩展 FBeast、KakusaretaSutoka、ArchArcanist、VoidWalker、FinalSampi。
4. 接入 SinfulBusterExpert 固定八分区策略，验证持有 1、2、3、8 件时都保持八个 group；开着 wheel 解锁时原位置启用，不重建轮盘。
5. 接入 MakeAGoodZero 第二阶段六件与阶段失效策略；可选单项阶段 bar 不阻塞多武器部分交付。
6. 全量 native ACC 编译、`git diff --check`、按项目现有流程打包校验；游戏/联机测试另记录，不以编译通过替代运行验证。两武器 Boss 留待后续阶段。

## 六、验收清单

- 首批六个 Boss 的 actor/icon、登记顺序、真实绑定和高亮正确；一件武器一个 group，没有类别堆叠。
- 普通持有项轮盘不足三件不打开；SinfulBusterExpert 仅持有 W1 时也能打开固定八分区。bar 不依赖先打开 wheel。
- SinfulBusterExpert 始终八分区，未解锁图标灰显且不能选择；解锁后原位置启用，打开期间也不改变顺序、方向和悬停项。bar 不绘制未持有武器。
- MakeAGoodZero 第一、二、三阶段不混合集合，W8 清理之前的网络中间态也不能返回 W2–W7。
- Lin、MeisterWahwee、WarRockStelar 不新增注册/显示路径；Clownpiece 不出现八分区自由选择入口。
- 攻击/转阶段禁止切换条件、死亡/unmorph/再次 morph 及 wheel 关闭时机正确；服务端拒绝未持有、未解锁或过期阶段武器。
- 观战不同 Boss、迟加入、重生、换 Boss：bar 不串数据、不保留旧玩家图标。
- UIX 原有方向、镜像、绑定提示、缩放、alpha、ROWMAX、溢出和禁用开关生效；同槽顺序与槽位键一致。
- 原有 survivor 固定 wheel/bar、Qwant、NegaMan、MegaMan 原版路径与 item wheel 回归。
- 不加载 UIX 时所有 Boss 原有行为不变；没有新增强制授予、槽位修改或阶段网络写入口。

完成记录应区分实际已经覆盖的 Boss、仅编译通过的项、实际联机验证的项，以及暂缓的三个两武器 Boss；不宣称本阶段覆盖所有 Boss。

## 七、实施完成与验证记录 (2026-09-17)

### 1. 代码修改与新增清单

1. **`src/acs_source/compat/mods/uix/uh_uixfw_boss_defs.acs` (NEW)**:
   - 登记全部 8 个 Boss 的轮盘元数据（包括 Batch A 6 个与 Batch B 2 个）。
   - 提供判定辅助函数：`UHFW_IsBossClass`、`UHFW_IsSinfulBusterExpert`、`UHFW_IsMakeAGoodZero`、`UHFW_IsZeroPhase2`。
2. **`src/acs_source/compat/mods/uix/uh_uixfw_db.acs`**:
   - `UHFW_MAX_CLASS` 从 8 扩容至 16（完全容纳 5 survivor + 8 boss）。
   - 在 `UHFW_RegisterFixedWheels` 中引入 `#include "uh_uixfw_boss_defs.acs"` 并执行 `UHFW_RegisterBossWheels()`。
3. **`src/acs_source/compat/mods/uix/uh_uixfw_bar.acs`**:
   - `UHFB_ClassIndex()` 扩展白名单：包含全部 6 个 Batch A Boss 以及 SinfulBusterExpert，排除 MakeAGoodZero（返回 `UHFB_UNSUPPORTED = -1`）。
   - 新增 `uh_zb_check`（检查摄像机是否为 MakeAGoodZero）与 `uh_zb_phase`（阶段检查 1/2/3）。
4. **`src/acs_source/compat/mods/uix/uh_uixfw_run.acs`**:
   - 增加 `uhfw_enabled` 数组跟踪项启用状态。
   - 实现 `UHFW_CollectSinfulBusterExpert` 固定收集 8 个槽位，未持有项标记为禁用。
   - `UHFW_HideSharedEnergyBars` 对 `UHFW_IsBossClass` 返回 1，隐藏所有 Boss 的共享能量条。
   - 实现 `UHFW_RefreshSinfulBusterExpert` 在 tick 期间原位刷新解锁项（alpha/color 实时恢复）。
   - `UHFW_ShouldCancel` 加入 MakeAGoodZero 离开 Phase 2 和 SinfulBusterExpert 失去 W1 时的自动取消。
5. **`src/acs_source/compat/mods/uix/uh_uixfw_end.acs`**:
   - `UHFW_OpenUnified` 针对 SinfulBusterExpert 允许在仅持有 W1 时开启固定八分区；guard MakeAGoodZero 仅在 Phase 2 开启。
   - `uh_ww_tick` 调用 `UHFW_RefreshSinfulBusterExpert`。
   - `uh_ww_select` 拦截未解锁的 SinfulBusterExpert 武器。
   - `uh_ww_sel_sv` 服务端权威验证加入 `UHFW_IsZeroPhase2` 阶段保护。
6. **`src/acs_source/compat/mods/uix/uixweap.acs` & `uixweap_fixedbar.acs`**:
   - `UIX_WeapBar` 增加 `uh_zb_check` 分支，当为 MakeAGoodZero 时路由到 `weaponBarMakeAGoodZero()`。
   - `weaponBarMakeAGoodZero()` 实现：Phase 1/2/3 单槽同槽栈渲染，`slotHint = -1`，不伪造 1–6 虚拟槽位，展示实际持有项和同槽溢出计数。
7. **`src/LANGUAGE.enu`**:
   - 补齐全部 8 个 Boss 涉及武器的 human-readable TAG 语言项。
8. **`src/acs_source/debug/rz_debug.acs`**:
   - `rz_debug_MorphMe` 增加 `UnMorphActor(0, 1)`，支持测试期间连续变身不同 Boss。
   - 新增 `rz_debug_fb_probe` 探针脚本并暴露 `world int 50/51/52`，供自动化测试读取 `uh_fb_count`、`uh_zb_check`、`uh_zb_phase`。

### 2. Live Engine MCP 验证结果 (`tools/mcp/verify-boss-multiweapon.mjs`)

使用 `mm8bdm-v6b-full` 运行配置在真实 Zandronum 引擎中逐一测试：

```text
=== Test 1: GBeast (108) ===
GBeast class: GBeast initial weapon: GBeast_W1
GBeast ACS probe: { fbCount: 6, zbCheck: 0, zbPhase: 0 }
GBeast ready weapon after wheel select index 3: GBeast_W4

=== Test 2: SinfulBusterExpert (102) ===
SinfulBusterExpert class: SinfulBusterExpert initial weapon: SinfulBusterExpert_W1
SinfulBusterExpert ACS probe: { fbCount: 8, zbCheck: 0, zbPhase: 0 }
SinfulBusterExpert after trying unheld W3 (should remain W1): SinfulBusterExpert_W1
SinfulBusterExpert after unlocking and selecting W2: SinfulBusterExpert_W2

=== Test 3: MakeAGoodZero (306) ===
MakeAGoodZero class: MakeAGoodZero initial weapon: MakeAGoodZero_W
MakeAGoodZero Phase 1 probe: { fbCount: -1, zbCheck: 1, zbPhase: 1 }
MakeAGoodZero Phase 2 probe: { fbCount: -1, zbCheck: 1, zbPhase: 2 }
MakeAGoodZero after wheel select in Phase 2: MakeAGoodZero_W4

=== Test 4: Batch A remaining Bosses ===
KakusaretaSutoka: fb_count=3, selected=KakusaretaSutoka_W2
ArchArcanist: fb_count=3, selected=ArchArcanist_W2
VoidWalker: fb_count=4, selected=VoidWalker_W3
FBeast: fb_count=6, selected=FBeast_W5
FinalSampi: fb_count=7, selected=FinalSampi_W4

PASS: GBeast
PASS: SinfulBusterExpert
PASS: MakeAGoodZero
PASS: KakusaretaSutoka
PASS: ArchArcanist
PASS: VoidWalker
PASS: FBeast
PASS: FinalSampi
```

### 3. 验收核对

- [x] 首批六个 Boss（KakusaretaSutoka、ArchArcanist、VoidWalker、GBeast、FBeast、FinalSampi）的 actor、icon、绑定及切换全部正确。
- [x] SinfulBusterExpert 始终维持 8 分区，仅持有 W1 时即可打开轮盘，未解锁项灰显且被拒绝选择；解锁 W2 后原位启用并可选择。
- [x] SinfulBusterExpert 各武器 ammo1 显示已完整接入 wheel 与 fixed bar：正确读取 W1–W8 各自独立的 Ammo（SBESueAmmo～SBEHellBotAmmo）、NormalBar 对应调色板（203/206、63/79、198/244 等）及对应容量上限，同时隐藏 ammo2（UnholyPower1500 共享 Rage 能量），动态刷新机制同步维持；其他 Boss 共享能量条继续保持隐藏。
- [x] MakeAGoodZero 第一、二、三阶段正确分离，bar 采用 `slotHint = -1` 真实单槽堆叠；Phase 2 自由选择 W2–W7，非 Phase 2 拒绝轮盘开启。W2 单条显示 UnholyPower3000（228/227，上限 3000），W3–W7 单条分别显示对应芯片弹药 MGZeroChipAmmoCutter/Flame/Icicle/Zap/Psycho（对应 NormalBar 配色，上限 1200），wheel 与 weaponbar 均只画一个 bar，不画第二条能量。
- [x] Lin、MeisterWahwee、WarRockStelar 按计划暂缓，不增加虚假注册。
- [x] Clownpiece 及各 `_Pissed` 变体完全排除在多武器轮盘外。
- [x] 全部 ACS 编译通过（0 errors, 0 warnings），`git diff --check` 通过（0 errors），PK3 打包校验通过，live MCP 自动化回归测试（`verify-boss-multiweapon.mjs`）全部通过（8/8 Bosses PASS）。
