# Bonus Event 动态数据库实施方案

## 结论

将 `bonus event` 拆成“可注册的数据”和“命名脚本回调”两层，并把数据库放进现有 `UHDT → UHADDR → UHADD` API 链，是当前工程中风险最低、也真正允许后加载 addon 扩展的做法。

建议新增 `DefineBonusEvent` 作为主注册函数，以不区分大小写的 `stem` 作为跨 PK3 稳定身份；保留现有整数 ID 作为 v4/RCON 兼容入口。事件名称、音乐、提示、随机权重、人数范围、通用分类和 EX 关系进入 UHDT；事件启动与复活重建等特殊行为保存为命名 ACS 脚本回调。这样可以删除当前候选数组及大部分按事件 ID 分派的 `switch`，同时不假装 ACS 能储存函数指针。

不建议把 bonus event 并入现有 `DefineLMSEvent` 表。二者虽然都属于 LMS 流程，但生命周期不同：`DefineLMSEvent` 是普通回合中的 last-survivor 奖励，而 bonus event 会替换整轮选人、阵营、变形、胜负监听及复活恢复逻辑。应复用它的 API 架构，而不是复用同一张表。

## 调研依据

### 当前硬编码位置

- `src/acs_source/unholy/uh_def.acs`
  - `UHEVENT_*` 固定 ID。
  - `bonuseventlist[200][6]` 稀疏二维表。
  - `bonuseventcandidates` 与 `bonuseventlowcandidates` 两个固定随机池。
- `src/acs_source/unholy/uh_event_helpers.acs`
  - `CheckEventList` 用白名单 `switch` 判断有效事件。
  - `PickRandomBonusEvent` 在两个固定数组中抽取。
  - `IsAllEyeEvent`、`HasEyeTeamEvent` 用重复的 ID `switch` 表达类别。
  - `ExEventChecker` 假定 EX ID 等于基础 ID `+100`，并把阈值固定为 3。
- `src/acs_source/unholy/uh_events.acs`
  - `ub_EventManagementACS` 用大 `switch` 将 ID 转成启动脚本和参数。
  - `IsFFAEvent`、`OneVsAllRawFromEvent` 再次按 ID 分类/映射。
  - `RebuildActiveRoundState` 用第三套 `switch` 重建复活玩家状态。
  - 若干专用流程仍直接读取 `bonuseventlist[0/13/51/100/106/113/151]`。
- `src/acs_source/unholy/uh_lifecycle.acs` 与 `uh_bossselect.acs`
  - 预告文字及个别音乐仍直接索引 `bonuseventlist`。

这意味着当前“增加一个事件”不只是增加一行：还可能需要同步白名单、候选池、分类函数、启动分派、复活重建和兼容映射。漏掉任一点都可能出现“可强制但不能随机”“能开局但复活后状态错误”或“有行为但没有预告元数据”。

### 可复用的现有架构

项目已有完整的动态 LMS event 先例：

- `src/acs_source/_imports/uhdt.acs` 保存表，提供 `DefineLMSEventCore`、按 stem 查找、加权抽取和附属 drop 行。
- `src/acs_source/corescripts/api_handlers/uhaddr.acs` 是命名脚本 handler。
- `src/acs_source/_includes/mod_api/uhadd.acs` 通过临时 cvar 传递字符串/多参数，再用 `ACS_NamedExecuteWithResult` 调用 handler。
- `src/acs_source/systems/lms/definitions/uh_lmsdefs.acs` 用普通 `OPEN` 和 `OPEN CLIENTSIDE` 双注册内建条目。

这与 MM8BDM v6b 的 `DTADD.acs → DTADDR.acs → 8bdt` 设计一致：addon-facing include 不直接共享调用者的局部数组，而是经 cvar + 命名脚本进入公共 LOADACS 库。v6b 的 DefineWeapon、team color、training definition 等 API 均采用这一边界。

Zandronum/ACC 源码也确认了此方案的语言边界：ACC 暴露 `ACS_NamedExecute`、`ACS_NamedExecuteWithResult` 和 `ACS_NamedExecuteAlways`；引擎的 `P_StartScript` 会在静态 ACS 模块中按脚本名解析并启动脚本，找不到时返回失败并记录 unknown script。ACS 本身没有可储存在数组里的函数指针，因此特殊行为必须以脚本名间接调用。

## 建议的数据模型

### 主表

在 `UHDT` 末尾追加 bonus event 表，避免改变既有 import 符号的索引。建议容量先定为 256；整数 ID 合法范围为 `0..255`，`-1` 表示自动分配 addon ID。

| 字段 | 类型 | 用途 |
|---|---:|---|
| `defined[id]` | int | 槽位是否有效 |
| `stem[id]` | str | 稳定、大小写不敏感的跨 PK3 身份 |
| `name[id]` | str | 回合预告名称 |
| `music[id]` | str | 默认音乐 lump |
| `musicCredit[id]` | str | 音乐说明 |
| `bonusSound[id]` | str | 可选开场音效 |
| `hudMessage1/2[id]` | str | 通用开场提示 |
| `startCallback[id]` | str | 服务端启动回调 |
| `rebuildCallback[id]` | str | 服务端复活/重连状态重建回调 |
| `arg1/arg2/arg3[id]` | int | 传给启动和重建回调的声明参数 |
| `flags[id]` | int | 仅存核心流程确实需要查询的通用语义 |
| `weight[id]` | int | 随机权重；0 表示仅强制 |
| `minPlayers/maxPlayers[id]` | int | 随机抽取资格；`maxPlayers=0` 表示无上限 |

建议的第一批通用 flags：

- `UHBE_FLAG_FFA`：核心在复活重建前清除三类友军保护。
- `UHBE_FLAG_ONEVSALL`：核心恢复 boss/survivor life status。
- `UHBE_FLAG_ALL_EYE`：替代 `IsAllEyeEvent`。
- `UHBE_FLAG_EYE_TEAM`：替代 `HasEyeTeamEvent`。

不要为只被一个事件使用的细节继续增加 flag。比如 Sumo/Quick 的独特属性、Boss FFA 的已抽 boss、Satan Seal 的物品恢复，都应在该事件的 `rebuildCallback` 内处理。否则数据库会退化成另一套隐式 `switch`。

### EX 关系表

不要保留 `baseId + 100` 作为数据库语义。新增以 stem 绑定的关系：

```acs
SetBonusEventEX("ffa", "truepower_ffa", 3);
SetBonusEventEX("football_ffa", "rune_ffa", 3);
```

UHDT 内部保存 `baseEventId → exEventId + threshold`；没有 EX 时为失败值。这样 addon 自动 ID 也能拥有 EX 事件，且不与整数段发生碰撞。现有 `eventexcountarray` 可暂时继续按基础 event ID 索引，第二阶段再迁到 UHDT 私有数组。

### API 草案

主入口建议控制在一项完整定义，辅助关系另设 setter：

```acs
function int DefineBonusEvent(
    int id, str stem, str name,
    str music, str credit,
    str sound, str hud1, str hud2,
    str startCallback, str rebuildCallback,
    int arg1, int arg2, int arg3,
    int flags, int weight,
    int minPlayers, int maxPlayers);

function int SetBonusEventEX(str baseStem, str exStem, int threshold);
function int UH_FindBonusEventByStem(str stem);
function int UH_IsBonusEventDefined(int id);
```

ACS 脚本参数数量有限且上述定义含多个字符串，因此 `UHADD.acs` 应继续采用 v6b/UHADD 已验证的 cvar mailbox：逐字段写入 `uh_be_*` cvar，再调用 `uh_DefineBonusEvent_S`。handler 立即消费，不在 cvar 中保留数据库状态。

内部 UHDT getter 至少包括 `GetBonusEventName/Music/Credit/Sound/HudMessage1/HudMessage2/Flags/StartCallback/RebuildCallback/Arg1..3`，另提供：

```acs
PickBonusEvent(playerCount, excludedId)
ResolveBonusEventEX(baseId)
RunBonusEventStart(id)
RunBonusEventRebuild(id, tid, reason)
```

`PickBonusEvent` 对所有 defined 行执行 `weight >= 1`、人数上下界和排除上一事件检查后做加权抽取。由此同时取代两个 candidate 数组以及当前“抽到上一项就 Delay(1) 重抽”的循环。

回调约定：

- 启动回调：`script "..." (int eventId, int arg1, int arg2)`；需要第三个自定义参数时可由 callback 根据 event ID 从 UHDT 读取 `arg3`，或把通用 handler 包成事件专用脚本。
- 重建回调：`script "..." (int eventId, int tid, int reason)`；回调自行读取注册参数。
- 回调必须是普通服务端脚本，不能标记 `CLIENTSIDE`，也不能依赖调用者局部状态。
- 调度使用 `ACS_NamedExecuteAlways`，允许多玩家重建并行；需要同步返回值的校验/查询才使用 `ACS_NamedExecuteWithResult`。

## 内建事件迁移方式

新增 `src/acs_source/systems/bonus_events/definitions/uh_bonusdefs.acs`，作为单独 LOADACS 库，结构照 `uh_lmsdefs.acs`。编译产物/LOADACS 名称应沿用项目现有的命名与打包方式，并在实现时用 `validate-build-pk3.sh` 核对最终 lump，而不是仅凭源文件长名推断。

1. `UH_RegisterVanillaBonusEvents()` 集中调用 `DefineBonusEvent`。
2. 普通 `OPEN` 在服务端注册。
3. `OPEN CLIENTSIDE` 注册本地副本，保证今后客户端 HUD getter 和加入中途的客户端一致。
4. 在 `LOADACS` 中放到 `UHADDR` 之后、`unholy` 之前；不要依赖 LOADACS 顺序来推断各 OPEN 脚本完成顺序。

第一轮注册应保留现有稳定 ID，包括 13=Football、113=Runes，以及 51/151 等 force-only 事件。旧 Razon3 输入别名 `50→13`、`150→113` 可以留在 RCON 解析层，但不得写入数据库成为第二身份。

示意定义：

```acs
DefineBonusEvent(
    UHEVENT_MLG, "mlg_eyes", "MLG eyes",
    "M_EYE01 10", "Snake's Revenge (NES) - Enemy Alert Lv.1 Theme",
    "", "\\cjMLG Tourney! Last one standing gets paid!", "",
    "ub_DemoneyeEvent", "uh_RebuildEyeEvent",
    1, 1, 0,
    UHBE_FLAG_ALL_EYE | UHBE_FLAG_EYE_TEAM,
    1, 0, 0);
```

现有 0–10 在低人数池和全人数池均出现，可统一为 `weight=1, minPlayers=0, maxPlayers=0`。现有 11–16 只在 `PlayerCount() >= MULTIB_PLAYERLIMIT3` 时出现；当前 `MULTIB_PLAYERLIMIT3` 为 12，因此应注册为 `minPlayers=12`，而不是保留“low/full pool”这一实现概念。51、100、106、111、112、113、151 当前不在普通池的项目先设 `weight=0`；若某个是 EX 目标，则只通过 EX 关系进入。

## 调度器重构

按以下顺序迁移，保证每一步都可编译、可回退：

1. **只增加数据库和 API。** 在 UHDT 末尾添加表/Core 函数，在 UHADDR 添加 handler，在 UHADD 添加 public wrapper 与 addon recipe；原 bonus 逻辑仍不读取新表。
2. **注册全部内建事件。** 新定义库用现有表逐项注册；增加 debug 验证脚本，检查稳定 ID、唯一 stem、有效权重/人数范围、随机事件具有启动 callback、EX 两端均已定义。
3. **替换纯元数据读取。** 将 `bonuseventlist[...]` 改为 getter，覆盖预告、音乐、credits、音效和 HUD 文本。确认后删除稀疏二维表。
4. **替换选择与有效性。** `CheckEventList` 改为 `IsBonusEventDefined`；`PickRandomBonusEvent` 改为加权/人数过滤器；删除两个候选数组。强制事件仍接受稳定整数 ID，并新增按 stem 的内部查找能力。
5. **替换启动分派。** `ub_EventManagementACS` 的事件 `switch` 改为取 `startCallback` 并执行。内建条目可以先继续指向现有通用脚本（`ub_FreeForAll`、`ub_DemoneyeEvent`、`ub_OneVsAllEvent` 等）及其参数，无需立刻重写事件本体。
6. **替换分类与重建。** `IsFFAEvent`、`IsAllEyeEvent`、`HasEyeTeamEvent` 改查 flags；`RebuildActiveRoundState` 保留通用 FFA/one-vs-all 前处理，之后执行 `rebuildCallback`。把现有每个 case 的内容搬进小型命名脚本。
7. **迁移 EX。** 用 `SetBonusEventEX` 替代 `+100` 推导；保留旧 ID 常量作为兼容别名，但核心不再依赖数值关系。
8. **删除遗留硬编码。** 全库 `rg` 确认除内建定义、兼容常量和确有协议意义的地方外，不再出现事件 ID `switch` 或直接数组索引。

## 初始化与联网注意事项

- 不要假定 LOADACS 列表顺序等于同 tic 内各库 `OPEN` 完成顺序。当前 boss combo 已明确处理过这个问题。bonus 选择发生在倒计时后，通常已有充足时间，但 debug 校验仍应使用有上限的等待（建议复用 35 tic 约定），不能永久等待。
- 服务端数据库决定随机选择与行为。`OPEN CLIENTSIDE` 副本只服务本地 HUD/查询；客户端不能执行 start/rebuild callback。
- `DefineBonusEvent` 重复注册同一 `(id, stem)` 应整行更新，以便 server/client 双注册和 addon 重载模式保持幂等；同 stem 不同 ID、同 ID 不同 stem 必须失败。
- 字符串身份用 `StrICmp` 去重；原样保存 actor/script/lump 字符串。ACS 标识符大小写不敏感，但普通字符串比较默认大小写敏感。
- 自动 ID 建议从一个明确的 addon 起点开始（例如 160 或 200），而不是“最大已有 ID + 1”；目前内建稳定 ID 已到 151，固定起点更能避免未来新增内建项抢占 addon 槽位。最终起点要在实现前冻结并写进 public API。
- 容量、权重总和和 `eventexcountarray` 下标都要做边界检查。权重可沿用现有 API 的最大权重保护，避免 32 位累加溢出。

## 兼容策略

- `UHEVENT_*` 常量暂时保留，供现有代码、RCON 和外部 addon 编译；它们只表示内建稳定 ID，不再是注册表完整性的来源。
- `uh_sv_BonusEventNum` 继续接受整数。无效或未注册 ID 保持现有 warning 行为。
- 保留 `NormalizeForcedBonusEvent(50/150)` 一版兼容周期，并在注释中标成 legacy input alias。
- 现有事件行为第一阶段不改，只把分派改为回调，因此游戏平衡、提示文本和音乐应逐字保持。
- addon 新事件必须提供独立脚本名，避免命名冲突；引擎对同名静态脚本会按静态模块查找顺序解析，因此 API 文档应要求带 addon 前缀。

## 验证计划

### 静态与编译

1. 编译所有受影响库：至少 `UHDT`、`UHADDR`、新 definitions 库和 `unholy`。
2. 搜索确认：
   - 不再存在 `bonuseventlist`、`bonuseventcandidates`、`bonuseventlowcandidates`。
   - `CheckEventList` 若为兼容 wrapper，只委托 `IsBonusEventDefined`。
   - 启动和重建不再含列举全部事件的 `switch`。
3. 运行 `./tools/validate-build-pk3.sh` 检查成品入口和 ACS lumps。

### 数据库单元式检查（debug ACS）

- 所有内建稳定 ID 均 defined，stem 唯一。
- 0–16 的元数据与旧 `bonuseventlist` 一致。
- force-only 事件不会被 `PickBonusEvent` 抽到。
- 低人数时不会抽到原高人数事件；满足阈值后会进入候选。
- 排除 last event 后，只有一个候选时有明确行为：允许重复或返回 fail，必须在实现中选定并记录；建议允许重复，避免死循环。
- EX 计数达到阈值时解析到已注册目标，缺失目标时安全回退到基础事件并记录 warning。
- 重复注册幂等，冲突 ID/stem 和容量耗尽返回 `UHBE_FAIL`。

### 运行时回归

实现完成后才需要 MCP 运行测试；本方案阶段不启动引擎。建议至少覆盖：

1. 普通眼事件（MLG）：启动、moola/protection、复活重建。
2. 有额外状态事件（Sumo 或 Quick）：确认 callback 重建特殊属性。
3. One-vs-all（Eye Parade）及暗场变体（Clone/Mosquito）：阵营、HP、灯光、结束监听。
4. FFA（Football/Runes）：保护清除、物品/rune 重建。
5. Boss FFA：复活后复用 `eventbossid`，不得重抽。
6. force-only 事件和旧别名 50/150。
7. 一个独立测试 addon 用 `DefineBonusEvent(-1, ...)` 注册新 stem，验证它可随机、可 RCON 查找/强制、可启动、可复活重建。
8. 服务端 + 客户端各检查一次加入中途 HUD/名称读取，确认 client UHDT 已注册而不会在客户端执行行为 callback。

## 完成标准

只有同时满足以下条件，才能认为 bonus event 已真正动态化：

- 新事件可由后加载 PK3 仅通过 public `UHADD` API 注册，无需修改 Unholy 的候选数组、白名单或 dispatcher。
- 元数据、人数资格、权重、EX 关系、启动和复活重建均由注册项驱动。
- 内建稳定 ID 与 RCON 兼容行为不变。
- 普通池不再依赖连续 ID、固定范围或 `+100` 关系。
- 服务端行为与客户端显示数据库在联网环境均可用，且回调只在权威服务端执行。
