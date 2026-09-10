# Unholy Razon 日志等级调查

调查日期：2026-09-10

本报告只提出迁移方案，不修改 ACS/DECORATE。目标是让后续 agent 引入统一的四级日志函数，迁移现有诊断输出，最后删除 `DebugLog`。

## 结论

建议统一为 `UH_Log(int level, str message)`，输出格式固定为：

```text
[Unholy] [DEBUG] message
[Unholy] [INFO] message
[Unholy] [WARN] message
[Unholy] [ERROR] message
```

建议颜色如下（均是 v6b `TEXTCOLO` 与 Zandronum 支持的命名色）：

| 等级 | 颜色代码 | 含义 |
|---|---|---|
| `DEBUG` | `\c[LightBlue]` | 高频、开发期状态与数值 |
| `INFO` | `\c[Green]` | 低频、正常生命周期或管理操作成功 |
| `WARN` | `\c[Gold]` | 输入/配置有问题，但已拒绝、回退或修正，游戏仍可继续 |
| `ERROR` | `\c[Red]` | 不变量、注册表或资源错误，当前操作无法正确完成 |

每条前缀之后应加 `\c-`，防止日志正文继承等级颜色。不要依赖 `Log` 自己区分严重度：Zandronum 的 ACS `Log` 最终只是把带颜色转义的字符串送到控制台；写入磁盘 logfile 时引擎会剥掉颜色码，因此文本等级前缀必须保留。

建议保留现有 `uh_sv_BossDebugText`/`debug_txt` 作为 `DEBUG` 的开关；`INFO`、`WARN`、`ERROR` 不受它控制。否则当前藏在 `DebugLog` 内的真实配置错误会在正常服务器上继续不可见。

## 扫描范围与数量

- 扫描了 `src/acs_source/**/*.acs` 中 `DebugLog`、`Log`、`Print`、`PrintBold`，以及 `src/actors/**/*.{dec,txt}` 中 `A_Log`。
- 找到 142 个“非整行注释”的文本候选。其中 3 个其实是行尾注释（`projectile_and_xray.acs:35,37`、`uh_bossselect.acs:147`），所以有效候选为 139 个。
- 原始构成是 67 个 `DebugLog` 匹配（包含函数定义，即 66 个调用）、63 个 `Log`、12 个 `Print`/`PrintBold`。其中还包括 `DebugLog`/`ACSUtils_ProgramError` 内部的输出实现，以及明确的玩家提示；不能把 139 个全部机械替换。
- 活跃 `A_Log` 只有 1 个：`src/actors/player/uh-BasePain.dec:14`。
- 另找到 77 个 ACS 注释日志和 60 个 DECORATE 注释 `A_Log`，恢复建议见后文。扫描大小写不敏感，因此旧代码中的 `log`/`print`/`debugLog` 也包括在内。
- `tools/` 下 Python/JS/shell 的 stdout/stderr 不属于游戏内 ACS logging API，本次不要求改成 `UH_Log`；它们已有各自的 `status=error`、`warn:`、异常和退出码约定。

## 新函数的落点与接口

推荐把函数和等级常量放进 `src/acs_source/_imports/uh_acsutils.acs`，而不是继续放在 `unholy/uh_funclib.acs`。`uh_acsutils` 已被 `unholy`、`uh_tools`、`uh_classes`、`uh_copyweps`、`uh_shared`、`uh_items`、`rz_debug`、HUD 库等共同 `#import`，可覆盖目前跨库散落的日志。若把函数只留在 `unholy` 库，其余库无法统一调用。

建议接口：

```c
#define UH_LOG_DEBUG 0
#define UH_LOG_INFO  1
#define UH_LOG_WARN  2
#define UH_LOG_ERROR 3

function void UH_Log(int level, str message);
```

ACS 函数不是可变参数函数；调用端应使用 `StrParam(...)` 先组装消息。实现用 `switch` 选择完整的、静态写出的 `Log(s:"...")` 分支，未知等级按 `ERROR` 输出并注明 invalid level。不要把等级颜色存成运行期字符串再假定嵌套颜色解析行为。

`DEBUG` 开关有一个架构问题：`debug_txt` 是 `unholy` 库状态，`uh_acsutils` 不应反向依赖它。后续 agent 应二选一：

1. 推荐：`UH_Log` 的 DEBUG 分支直接读取 server CVAR `uh_sv_BossDebugText`；这样所有库一致，也不依赖 `unholy` 的 include 顺序。
2. 或新增更通用的 `uh_sv_LogLevel`，但这扩大了本任务配置面，需要维护者先确认。

迁移完成后删除 `unholy/uh_funclib.acs:16-20` 的 `DebugLog`。在删除前用 `rg -n '\bDebugLog\s*\(' src/acs_source` 确认只剩定义，再删除定义并复查为零。

## 活跃日志分级清单

下表按行为相同的调用点合并；列出的行号覆盖全部需要迁移的活跃诊断日志。

### DEBUG

| 文件与行 | 内容/用途 | 建议 |
|---|---|---|
| `debug/rz_debug.acs:17,25,35,38,54,60,94,107,112,125,128,129,132,137,211,219,234,241` | 手动 debug 命令的前置条件、结果与 GBTest/SpawnEx 数据 | 全部 `DEBUG`；这些失败只代表调试命令失败，不是游戏错误 |
| `systems/tools/motion_helpers.acs:103` | 每次调用打印角度、sin/cos、推力 | `DEBUG`；最好同时确认此无条件高频日志是否应保留 |
| `classes/bosses/centaur_option.acs:128,139` | 离线 quick-tune 脚本输入与结果 | `DEBUG`，包括 bad player；调用者本身就是 debug 脚本 |
| `classes/shared/copy_weapons/copy_weapon_runtime.acs:142-147` | Qwant user array dump | `DEBUG`；建议合成一条或保留有意义的字段名 |
| `classes/shared/copy_weapons/copy_weapon_damage.acs:200,204` | 每日伤害倍率 debug dump | `DEBUG` |
| `classes/shared/copy_weapons/copy_weapon_team_ff.acs:129,134` | 每日 team-FF/leak debug dump | `DEBUG` |
| `unholy/uh_lifecycle.acs:34,52,361` | 玩家死亡、断线、LMS 状态 | `DEBUG` |
| `unholy/uh_dickhead_revival.acs:123,130,201` | versus 阻止复活、复活 TID | `DEBUG` |
| `unholy/uh_events.acs:488,493,533,587,789` | 胜负、事件结束、目标和 morph-managed 分支 | `DEBUG` |
| `unholy/uh_funclib.acs:30,50,54,169,176,187,203,212,218,299,579,588,601,622,922,951` | CVAR 清理、玩家/数组、boss 解析与 TID 状态 | `DEBUG`；第 30 行也可升为 INFO，但启动时会和专门的 RCON 通知重复 |
| `unholy/uh_bossselect.acs:26,59,117,119,127,213,327` | boss 选择/morph/fakeout 正常流程 | `DEBUG` |
| `unholy/uh_arena_fx.acs:71,80` | rage 命中与使用者 TID | `DEBUG` |
| `unholy/sakiko_mujica.acs:81` | 特殊流程开始 | `DEBUG` |
| `unholy/uh_display.acs:161` | health watcher 正常结束 | `DEBUG` |

### INFO

| 文件与行 | 内容/用途 | 建议 |
|---|---|---|
| `v6b_overrides/corescripts/systems/teamcolors/teamcol.acs:177,361` | 应用颜色、重置预设成功 | `INFO`；这是低频管理操作确认 |
| `unholy/uh_funclib.acs:24` (`ShowMeTheRCON`) | RCON 设值通知，使用 `HUDMSG_LOG` | 保持 HUD 行为；若还需要独立统一日志，在现有消息旁调用 `UH_Log(INFO, ...)`，不要用新函数取代 HUD |

目前没有其他必须常驻的纯 INFO 诊断；大部分“正常完成”消息只在 debug 模式下有价值，因此归 DEBUG，避免服务器控制台泛滥。

### WARN

| 文件与行 | 内容/用途 | 建议 |
|---|---|---|
| `systems/tools/input.acs:4,15` | 非法玩家号/指针，函数返回默认值 | `WARN` |
| `systems/tools/health.acs:32,87` | 非法枚举参数，当前查询不能按要求完成 | `WARN`（调用被拒绝但不破坏全局状态） |
| `classes/survivors/marksman_support.acs:29`; `classes/survivors/decoybot_wisp.acs:92` | 非法 mode | `WARN` |
| `classes/survivors/eden/eden_helpers.acs:34` | 未知 Eden attribute | `WARN` |
| `_imports/uhedenisaac.acs:239` | quality 越界并 clamp | `WARN` |
| `compat/legacy/uh_legacy.acs:32,39` | 废弃脚本被调用（server/client 转发） | `WARN`；保留现有网络转发，避免 server/client 重复输出 |
| `compat/legacy/uh_legacy.acs:84` | legacy health 参数非法并 terminate | `WARN`；属于已废弃 API 的调用错误 |
| `unholy/uh_funclib.acs:13` (`ConsoleCommandWithWarn`) | 自动修正不兼容 CVAR | 改为 `UH_Log(WARN, ...)`，函数名可暂不动 |
| `unholy/uh_events.acs:8,57,71,797,804` | 非法 event id/强制值，或 round-state 无规则后跳过/回退 | `WARN` |
| `unholy/uh_funclib.acs:575,585,594,598,611,619,626,694,698,702,710` | boss combo 配置被拒绝并回退 | `WARN` |
| `unholy/uh_bossselect.acs:273` | shadow fallback 出现重复目标并走后备路径 | `WARN` |
| `unholy/uh_arena_fx.acs:74` | rage owner 没有 opponent | `WARN`；如果这是合法的无目标使用，则降为 DEBUG |

### ERROR

| 文件与行 | 内容/用途 | 建议 |
|---|---|---|
| `actors/player/uh-BasePain.dec:14` | 子类未定义必须的 `Check` state | `ERROR`。DECORATE 不能直接调用 ACS function；改为 `CallACS`/named script bridge，或保留 `A_Log` 但统一同样的文本前缀和颜色。不可直接写 `UH_Log(...)` |
| `v6b_overrides/corescripts/systems/colotrns.acs:132` | 颜色函数参数非法 | `ERROR`；当前文本已自带 ERROR，迁移后删除旧手写前缀 |
| `v6b_overrides/_imports/8bdt.acs:470,480` | 请求了不支持的 actor property | `ERROR`；这是 v6b 派生 import 的 `PrintBold`。如迁移必须保留调用者可见反馈，不能只改成 server console `Log` |
| `_imports/uhedenisaac.acs:95,108,128,207,235` | 注册数组溢出或组合定义结构不成立 | `ERROR` |
| `_includes/mod_api/uhadd.acs:614` | boss actor 未注册，morph setup 无法挂接 | `ERROR` |
| `classes/shared/special_watchers.acs:430` | Floovy death type 不可能识别 | `ERROR`（内部协议/枚举不变量） |
| `classes/shared/copy_weapons/copy_weapon_runtime.acs:105,114` | Qwant 必需变量/招式不存在 | `ERROR`；删除旧手写 ERROR 前缀 |
| `classes/shared/copy_weapons/copy_weapon_runtime.acs:246,248` | 已删除的旧检查路径仍被调用 | `ERROR` |
| `unholy/uh_lifecycle.acs:178` | boss registry 等待超时，后续验证仍运行 | `ERROR`，因为表示启动注册不完整或 include/OPEN 顺序问题 |
| `unholy/uh_funclib.acs:552,557` | `ApplyBossCombo` 收到越界/畸形内部数据 | `ERROR`（调用契约/表结构不变量） |
| `unholy/uh_funclib.acs:842,845,851,864,872,1010` | event/boss 注册资源缺失、组合表损坏、morph setup script 缺失 | `ERROR` |
| `unholy/uh_versus.acs:172` | versus 必须为 2 slots，但实际不符并 abort | `ERROR` |

`ACSUtils_ProgramError`（`_imports/uh_acsutils.acs:97-121`）已经是独立的程序错误通道：它带 tic、server/client 标签，并按 `acsutils_noerrors` 决定 `PrintBold`。不要简单改成 `UH_Log` 后丢失这些行为。可让它内部额外/改为调用 ERROR 格式，但必须保持 dedicated server 的 `Log`、客户端 `PrintBold` 和抑制 CVAR 语义。

## 不应迁移为调试日志的活跃输出

这些是玩家可见的游戏提示，而不是诊断 telemetry：

- `unholy/uh_arena_fx.acs:153,157,161,165,241`：wish 游戏事件。
- `unholy/uh_lifecycle.acs:64`：错误 gamemode 的管理员/玩家提示；可以同时补一条 `ERROR`，但不能只剩控制台日志。
- `unholy/uh_lifecycle.acs:109,113`：debug 开关反馈；应保持玩家反馈，必要时另发 INFO。
- `items/item_effects.acs:149`：胜利提示。
- 所有 `HUDMSG_LOG` 游戏广播：`sakiko_mujica.acs:68,119`、`uh_bossselect.acs:459`、`uh_display.acs:48,600,679`、`uh_dickhead_revival.acs:33`、`uh_bosscore.acs:163,291`。`HUDMSG_LOG` 的“LOG”意为 HUD 消息也进入控制台历史，不等于开发日志等级。
- `unholy/uh_display.acs:44` 是 boss instruction 的 console fallback，应保持原样，不加 `[INFO]` 破坏面向玩家的文案。

## 注释日志恢复评估

### 建议恢复

只有一条值得默认恢复：

| 文件与行 | 等级 | 理由 |
|---|---|---|
| `systems/shared/status_effects.acs:106` | `WARN` | `uh_FloorQuakeDamage` 的 `quakepower > 255` 是明确越界条件；比周围逐帧数值 dump 更有长期诊断价值。恢复时改写成精确消息并带实际值/上限。 |

另有两条条件性候选：

| 文件与行 | 等级 | 条件 |
|---|---|---|
| `v6b_overrides/_includes/common/8bdmmath.acs:208`、`colofunc.acs:17` | `WARN` | 两处都是 `RGBHex2Dec` 非 8 字符警告，但上游注释明确说明网络丢包可能随机触发。只有能证明本 mod 的调用参数在 server authoritative 路径稳定、且不会产生误报时才恢复；否则继续注释。两份派生实现必须同步。 |
| `classes/survivors/marksman_support.acs:8` | `WARN` 或 `DEBUG` | 只有“锁定槽确实溢出且这不是正常满槽状态”时才恢复；当前文案不足，应附玩家/TID/limit。 |

### 可按需恢复为 DEBUG，但不建议默认启用

以下均是开发时有用的状态探针。迁移成 `UH_Log(DEBUG, StrParam(...))` 后受 debug CVAR 控制，才适合复原：

- `systems/tools/player_state.acs:18,24,34,102`；`player_queries.acs:23-25`；`health.acs:24,104`；`motion_helpers.acs:62,84,111,138`；`pointer_helpers.acs:6`；`_imports/uh_acsutils.acs:242`。
- `classes/survivors/marksman_support.acs:4,33,48,53`、`shared_movement.acs:65,66,68,69,82,143`、`samurai.acs:5,40,41,47`。
- `systems/shared/status_effects.acs:2,26,104,113,185`、`shared_warp_and_cone.acs:5`。
- `v6b_overrides/corescripts/systems/colotrns.acs:268,269`、`jumpcanc.acs:87,102,114,311,312`。
- `unholy/uh_lifecycle.acs:271,531`、`uh_bossselect.acs:147`、`uh_bosscore.acs:208`、`uh_arena_fx.acs:95,100`、`uh_display.acs:437,534,695-699`、`uh_funclib.acs:162,924`。
- `items/item_effects.acs:109,120,122,124,132,136`。
- `classes/survivors/zangief.acs:12`。
- DECORATE 状态轨迹：`teamtranslation.txt:48`、`uh-BasePain.dec:83`、`BoxDE.dec:340`、`TruePower.dec:37`、`Quickster_W.dec:144`、`KickChamp_W.dec:741,744,747`、`TorontoCalifornia_W.dec:32,44`、`VoidWalker_W.dec:727`、`Joterra_W.dec:903`、`TheCommandoChamp_W.dec:78,95,102,111,157,171,179,193,264,289,295,324,347`。

其中 DECORATE 不能调用 ACS function，必须经一个返回值无关的 named-script/`CallACS` bridge 才能使用新函数。不要为了恢复短暂状态轨迹而给每 tic/每 projectile 增加跨 ACS 调用；优先保留注释，需要时临时启用。

### 不建议作为新 logging 恢复

- `FortuneCoin.dec:64,79`、`TreeHugger_W.dec:459`、`JesterGelato_W.dec:414` 是玩家提示/玩笑文案；需要时应使用玩家通知机制，不应标 DEBUG/INFO。
- `HiddenPower.dec:94-162` 的 18 条类型映射是静态分支标签，运行时打印只会制造噪声；用代码审查/测试验证映射。
- `Neru_W.dec:232,255,262,269,276,283,289,301,305,324,342,355,385` 是 perk/stack 玩家反馈。若产品设计需要反馈，应恢复为 HUD/玩家消息，而不是调试 logger。
- `projectile_and_xray.acs:28,35,37,64,88,90` 是循环/逐 tic 路径；即使 DEBUG 开启也容易刷屏。若将来复原，必须只在状态转移时记录且带 actor/TID，不能照原样恢复。
- `v6b_overrides/corescripts/utilities/footchec.acs:35,54` 与 `_includes/common/8bdmefct.acs:21` 是临时 `PrintBold` 数值探针，会污染玩家 HUD；保持注释。

## 后续 agent 的实施顺序

1. 在 `uh_acsutils` 增加等级常量与 `UH_Log`，先编译所有依赖它的库，确认命名色与函数签名通过 ACC。
2. 先迁移 ERROR/WARN，再迁移 INFO/DEBUG；每次删除消息内已有的 `ERROR`/`WARNING`/`Debug` 手写前缀。
3. 保持玩家 `PrintBold`、普通 `HudMessage` 与 `HUDMSG_LOG` 的行为，不做机械替换。
4. 为 DECORATE 的唯一活跃 `A_Log` 决定 bridge 或同格式 `A_Log`；不要在 DECORATE 中直接调用 ACS 函数。
5. 仅恢复 `status_effects.acs:106`；其余注释日志按上面的条件处理，不要批量取消注释。
6. 把全部 `DebugLog` 调用迁完后删除函数，执行 `rg` 零残留检查。
7. 编译 ACS；本报告是静态调查，不要求启动引擎。若要验证控制台颜色，才进行一次最小 MCP 启动，并同时查看控制台与磁盘 logfile（磁盘日志应保留文字等级、去掉颜色码）。

## 权威依据

- Zandronum `src/c_console.cpp:1020` 起：控制台 `PrintString` 处理输出；写 logfile 时剥除颜色 escape。
- Zandronum `src/v_text.h:46,55` 与 `wadsrc/static/textcolors.txt`：颜色 escape 与 `Red` 等命名色。
- MM8BDM v6b `TEXTCOLO.txt:94,114,124,194`：`Green`、`Gold`、`Red`、`LightBlue` 在目标基础包中存在。
- Zandronum ACC `parse.c:2276-2304`、`pcode.h`：ACS print/log 的格式化表达式由编译器生成 p-code；统一函数应接收已经由 `StrParam` 构造好的单个 `str`。
- MM8BDM v6b 的 `core` 源码也用颜色前缀区分错误/警告，但没有可直接复用的四级、跨库 logger；因此本 mod 自建 `UH_Log` 是合理边界。

---

## 执行结果（2026-09-10）

### 实现与落点

新增 `src/acs_source/_imports/uh_log.acs`（`#library "uh_log"`）实现
`UH_Log(int level, str message)` 与四个 `#libdefine` 常量，输出
`\c[Level][Unholy] [LEVEL] \c-<message>`；`DEBUG` 分支读取
`GetCvar("uh_sv_BossDebugText") != 1` 时直接返回，未知等级按 ERROR 并注明
invalid level。

**与报告建议的偏差（必要）**：函数没有放进 `uh_acsutils.acs`。实测把
`uh_acsutils` 引入需要日志的 v6b 派生库时，会与它们已有的
`MAX_PLAYERS`（`8bdmdefs.acs` 的 `#define`）以及 `ZDistance`、
`SetInventory`、`SetActorInventory` 等函数冲突（ACC 报
`Invalid identifier` / `Function already has a body`）。因此改为独立的最小库
`uh_log`，各目标库单独 `#import "uh_log.acs"`，不引入整套 math/utility。

### 迁移结果

- `UH_Log` 调用共 124 条：**DEBUG 69 / INFO 2 / WARN 31 / ERROR 22**，
  与报告清单逐条一致。
- 删除 `unholy/uh_funclib.acs` 的 `DebugLog` 定义；`rg '\bDebugLog\b' src` 为 0。
- `status_effects.acs` 的 `quakepower > 255` 恢复为 WARN，并带实际值/上限。
- DECORATE 的 `uh-BasePain.dec:14` 保留 `A_Log`，改为统一的
  `\c[Red][Unholy] [ERROR] \c-` 文本前缀（DECORATE 不能直接调用 ACS function）。
- 未迁移玩家可见输出：`PrintBold`（gamemode/debug 开关、wish）、`HUDMSG_LOG`、
  `uh_display.acs:44` 的 boss instruction console fallback。
- **跳过 `v6b_overrides/_imports/8bdt.acs:470,480`**：该 `core8bdt` 源并未编译进
  本 mod（`acs/` 无对应 `.o`，运行时解析基础包的 `CORE8BDT`），其函数体在
  `#import` 时被跳过，改动不会生效。

### 构建与验证

- 用 ACC 1.60 编译全部 39 个 `#library`（含新 `uh_log`），0 失败；
  `src/acs/*.o` 已更新，`out/build.pk3` 已就地更新 `acs/*.o` 并新增
  `acs/uh_log.o`，`tools/validate-build-pk3.sh` 通过。
- 引擎内验证（mm8bdm-v6b-smoke）：`set uh_sv_BossDebugText 1` 后 morph，
  日志出现 `[Unholy] [DEBUG] ` 前缀；关闭/无关路径出现
  `[Unholy] [WARN] `（`ConsoleCommandWithWarn`）。`get_startup_errors`
  无 DECORATE/ACS 编译错误。颜色转义在控制台存在、磁盘 logfile 保留文本等级。
