# Unholy LMS 队友信息与 TAB 头像权限实施计划

## 目标

为 Unholy 的普通 `lastmanstanding` 模式增加类似 TLMS 的队友信息显示，同时兼容 UIX v3bh Better Team Display，并通过 Zandronum `SCORINFO` 直接扩展 built-in scoreboard 的玩家头像列。

本功能只改变客户端信息展示，不改变引擎 Team、伤害关系、LMS 胜负、出生、计分或角色选择。Unholy 继续使用普通 LMS；Survivor、Boss、Demoneye 的关系仍由 Unholy 回合状态决定。

## 已确认的底层限制

1. Zandronum 原生 TLMS 队友信息只在 cooperative/team game 中工作，并用引擎 `IsTeammate` 判断关系。Unholy 使用普通 LMS，不能直接复用。
2. Zandronum 默认 `SCORINFO` 的 `PlayerIcon` 列带有 `NOENEMIES`。该 flag 同样只认引擎 Team，所以普通 LMS 中通常只显示本人的 `Player.ScoreIcon`。
3. 删除 `PlayerIcon` 的 `NOENEMIES` 会无条件泄露所有角色，无法表达 Unholy 的按观看者权限。
4. SCORINFO 本身不能读取 Inventory、ACS 数组或调用自定义关系函数；它只能绘制列数据并应用固定 flag。
5. Zandronum 支持 `GAMEINFO AddCustomData`、ACS `SetCustomPlayerValue` 和 SCORINFO 自定义 Texture 列。CLIENTSIDE ACS 写入的值只影响当前客户端，适合实现“同一行对不同观看者显示不同头像”。
6. UIX v3bh 的 `UIXTEAM` 直接按 `PLAYERINFO_TEAM` 筛选。普通 LMS 的逻辑阵营不能被它识别；需要覆盖其 `UIXTEAM.o`，沿用本项目已有的 UIX shadow 兼容方式。
7. 客户端不能把 `unholy` library 的服务端运行时数组视作权威副本。显示所需的阵营、事件和目标状态必须显式同步或放在同步 Inventory 中。

## 统一语义模型

### 原始生命状态

继续使用现有状态：

- `PLS_DEAD`
- `PLS_SURVIVOR`
- `PLS_BOSS`
- `PLS_EYE`

它们仍由 `playerlifestatusarr` 管理。显示代码不直接把“状态相同”等价为“互为队友”。

### 客户端同步状态

新增一个面向显示的客户端快照，至少包含：

```c
int uhClientLifeStatus[MAX_PLAYERS];
bool uhClientOneVsAll;
int uhClientOneVsAllTarget; // player number；无目标时为 -1
```

同步必须覆盖：

- 初次进入与晚加入客户端的完整快照；
- 回合初始化和 Boss 分配完成；
- Survivor/Boss/Eye 状态变化；
- Demoneye morph；
- 死亡、断线与复活；
- Dickhead revival；
- bonus event 开始、结束和中止；
- `UH_SetBonusEventTarget` 改变 1-vs-all 目标。

不能只依赖活体 Actor 上的 Inventory：死亡玩家可能已无可读 body，但 scoreboard 仍保留该玩家行。推荐以服务端状态更新时广播 CLIENTSIDE 脚本参数、客户端数组缓存为主；同步 Inventory 可作为活体 HUD 的快速路径，但不是 scoreboard 的唯一真相。

### 1-vs-all 的权威定义

1-vs-all 必须由当前 bonus event 的 `UHBE_FLAG_ONEVSALL` 判定，单人目标来自 `bossdataarr[0][BOSSDATA_TID]` / `UH_GetBonusEventTarget`。

不能依赖目标的 `PLS_BOSS`：`uh_DemoneyeMorph` 会把其状态改成 `PLS_EYE`。客户端应同步冻结后的目标 player number。

## 队友信息关系

新增单一语义函数，供 Unholy HUD 和 UIX 适配层共同遵循：

```c
bool UH_AreDisplayTeammates(viewer, subject)
```

规则：

1. `viewer == subject` 不算队友项，默认不在队友栏重复显示自己。
2. 活跃的 1-vs-all event：
   - 单人目标只属于单人方，通常没有队友可显示；
   - 其余玩家属于多人方，彼此显示；
   - 依据目标身份划分，不依据当前 Morph 或 `PLS_EYE`。
3. 普通常规 LMS：
   - Survivor 之间互相显示；
   - 多 Boss 之间互相显示；
   - 任一方是 Eye 时返回 false。Eye 在常规 LMS 中可以互伤，不能组成显示队伍；
   - 死亡/无效/未完成分配的 subject 不作为活队友，是否保留死亡行由 HUD 用户选项控制。
4. `UHBE_FLAG_ALL_EYE` 或 `UHBE_FLAG_EYE_TEAM` 本身不授权队友显示；只有 `UHBE_FLAG_ONEVSALL` 触发上述特殊分队。这样不会把仍可互伤的 all-eye 场景错误显示成同队。
5. 纯 FFA event 不显示队友，除非它同时明确带有 `UHBE_FLAG_ONEVSALL`；实现中优先处理明确的 ONEVSALL，再拒绝其余 FFA。

## Unholy 原生队友栏

### 模块位置

建议新增：

```text
src/acs_source/unholy/uh_teaminfo.acs
```

作为 `unholy` 单一 library 的 fragment 从 `unholy/unholy.acs` include；不要拆出新的 round-core library。

### 生命周期

通过 MM8BDM v6b `DefineAssistDisplay` 注册客户端绘制入口，让 `core_Assist_Display` 提供当前 camera TID。观看其他玩家时，viewer 使用被观察玩家，而不是无条件使用 ConsolePlayer。

绘制前检查：

- 本地 Unholy 队友栏 CVAR 已开启；
- 当前处于有效回合和有效玩家 camera；
- 当前事件允许队友显示；
- UIX Better Team Display 没有正在接管显示。

### 第一版信息

- 玩家名；
- 当前/最大 HP；
- Armor；
- 当前武器与主弹药（信息可安全取得时）；
- 死亡状态；
- 可选角色头像；
- 默认不重复显示 viewer 自己。

建议用户 CVAR：

```text
uh_cl_teaminfo
uh_cl_teaminfo_names
uh_cl_teaminfo_health
uh_cl_teaminfo_weapon
uh_cl_teaminfo_dead
uh_cl_teaminfo_mugshot
uh_cl_teaminfo_scale
uh_cl_teaminfo_x
uh_cl_teaminfo_y
uh_cl_teaminfo_alpha
```

同时尊重 `cl_drawcoopinfo` 和 `sv_nocoopinfo` 的用户/服务器意图。HudMessage ID 使用专属范围或 v6b Assist Display ID API，不能撞现有 Boss HUD、事件 HUD 与 UIX layer。

## UIX Better Team Display 兼容

### 覆盖策略

将 UIX v3bh 的 `UIXTEAM.acs` vendoring 到：

```text
src/acs_source/compat/mods/uix/uixteam.acs
```

保留：

```c
#library "UIXTEAM"
```

编译输出为：

```text
src/acs/UIXTEAM.o
```

不要把它加入本项目 `LOADACS`；UIX 原有 LOADACS 负责加载同名 library，本项目在 UIX 后加载时以同名 lump shadow 原版。这与现有 `UIXWEAP.o` / `UIXITEMS.o` 兼容策略一致。

### 最小修改面

保留 UIX 的绘图、CVAR、布局、Mugshot、HP bar、武器、死亡动画、状态图标和 layer 实现，只替换：

1. 玩家过滤：Unholy LMS 下改用客户端版 `UH_AreDisplayTeammates`；非 Unholy 模式保持 UIX 原始 `PLAYERINFO_TEAM` 行为。
2. overflow/wrap-hide 人数统计：Unholy LMS 下遍历玩家计算可见队友数，不能调用 `GetTeamProperty`。
3. 自己隐藏与观察 camera：保持 UIX 原有行为，但 viewer 阵营来自当前 camera 的同步状态。
4. 死亡玩家：允许 UIX 原有 dead-row 选项继续控制；关系判断使用死亡前/当前缓存的 Unholy 阵营。

### 双重显示抑制

当以下条件同时成立时，Unholy 原生队友栏让位给 UIX：

```text
UIX_SV_TEAMINFO
UIX_CL_Enable
UIX_CL_TEAMINFO
```

未加载 UIX 时这些 CVAR 为 0，因此不需要硬依赖 UIX library。若 UIX 已加载但用户关闭 Better Team Display，则回退到 Unholy 原生队友栏。

### 加载顺序

正式支持顺序：

```text
megagame.wad
mm8bdm-v6b.pk3
8bdm-v6b-miscfixes-v6.pk3
8bdm-uix-v3bh.pk3       # 可选
out/build.pk3
```

文档中明确 UIX 必须位于 Unholy 之前；否则 `UIXTEAM.o` shadow 不能保证生效。

## Built-in scoreboard 的 SCORINFO 头像列

### 头像权限矩阵

常规 LMS：

| viewer | 自己 | Boss | 其他 Survivor | 其他 Eye |
|---|---:|---:|---:|---:|
| Survivor | 显示 | 显示 | 显示 | 隐藏 |
| Boss | 显示 | 显示 | 隐藏 | 隐藏 |
| Eye | 显示 | 显示 | 隐藏 | 隐藏 |

1-vs-all event：角色已经冻结，所有有效玩家互相显示全部头像，不区分单人方与多人方。

Boss 公开规则优先于“是否队友”：任何有效 viewer 都能看见所有 Boss 头像。

### GAMEINFO 自定义数据

新增或扩展项目 GAMEINFO，定义客户端纹理数据（最终语法在实现时以目标 Zandronum parser 静态验证）：

```text
AddCustomData "UHPlayerIcon", Texture, ""
```

不能与原生列名 `PlayerIcon` 冲突，因此使用独立名字 `UHPlayerIcon`。

### SCORINFO 列

新增 `src/SCORINFO`，基于 Zandronum 默认 PlayerIcon 列定义：

```text
Column "UHPlayerIcon"
{
    AddFlag NOSPECTATORS
    AddFlag DONTSHOWHEADER
    AddFlag ALWAYSUSESHORTESTWIDTH
    AddFlag DISABLEIFEMPTY

    Alignment = Center
    ClipRectHeight = -2
}
```

刻意不添加 `NOENEMIES`。在 scoreboard 的 `ColumnOrder` 中，用 `UHPlayerIcon` 替换 `PlayerIcon`；其他内建列、排序、滚动、队伍/观战分组和样式保持 v6b/Zandronum 默认行为。

实现时必须从目标引擎 `wadsrc/static/scorinfo.txt` 复制完整 scoreboard 定义或用后加载 override 能可靠表达的最小块；不能猜测列顺序，也不能丢失 UIX/其他 addon 已覆盖的 scoreboard 设置。需要记录最终采用的是“完整定义所有权”还是“最小 override”，以及与其他 SCORINFO addon 的最后加载者冲突规则。

### 客户端列数据刷新

新增：

```text
src/acs_source/hud/scoreboard_icons.acs
```

CLIENTSIDE 逻辑在 `BT_SHOWSCORES` 按下时刷新每个玩家的 `UHPlayerIcon`：

```c
SetCustomPlayerValue("UHPlayerIcon", subject, textureName);
SetCustomPlayerValue("UHPlayerIcon", subject, "");
ResetCustomDataToDefault("UHPlayerIcon", subject);
```

权限函数单独定义：

```c
bool UH_CanSeeScoreIcon(viewer, subject)
```

判定顺序：

1. 无效/断线 subject：清空；
2. 1-vs-all：所有有效玩家显示；
3. viewer 自己：显示；
4. subject 是 Boss：显示；
5. viewer 是 Survivor 且 subject 是 Survivor：显示；
6. viewer 是 Boss 且 subject 是 Boss：显示；
7. 其余隐藏。普通 Eye 因此只通过第 3、4 条看到自己和 Boss。

刷新只需在 scoreboard 打开时每 tic或在脏标记变化时更新；关闭时可保留缓存，因为该自定义数据只被 scoreboard 列消费。地图加载、玩家断线、角色重新分配和回合重置必须清空或覆盖全部 64 个槽，避免旧纹理残留。

### 观察与死亡语义

- 活跃玩家：viewer 为当前 camera 对应玩家，和 Assist Display 保持一致。
- 真观战者：首期建议显示所有头像，方便管理员/观众；若要防止场外串通，则改为只显示 Boss，并提供服务器 CVAR。实现前必须固定这一产品规则。
- 死亡玩家进入 dead spectator 后：使用客户端缓存的本回合身份，不依赖尸体 Actor。
- result sequence/intermission：可显示所有已确定头像，或恢复默认 scoreboard。首期建议全部公开，因为战斗已经结束。

## 公共头像数据库

ACS 无法直接读取目标 Actor 的 DECORATE `Player.ScoreIcon` 字符串。新增公共客户端查询层：

```text
src/acs_source/hud/player_portraits.acs
```

概念接口：

```c
str UH_GetPlayerScoreIcon(int player);
str UH_GetPlayerUIXMugshot(int player);
```

以当前 actor class（以及必要的形态/flag）查询。复用现有：

- `actors/compat/uix/UH_UIX_SurvivorMugshots.dec`
- `actors/compat/uix/UH_UIX_BossEyeMugshots.dec`
- `acs_source/compat/mods/uix/uh_uix_mugshots.acs`

若 ScoreIcon 与 UIX Mugshot 资源名不同，数据行分别保存两个字段；不能假定两者同名。该数据库成为以下三处唯一映射来源：

1. SCORINFO `UHPlayerIcon`；
2. Unholy 原生队友栏头像；
3. UIX Better Team Display。

缺失映射时记录一次 debug 诊断并返回空纹理，不能用错误角色头像兜底。实现完成后静态审计所有已注册 Survivor、Boss、Eye actor 都有有效行；形态变体需显式登记或明确继承规则。

## 预计文件改动

新增：

```text
src/GAMEINFO                         # 若项目尚无，则创建目标引擎支持的定义
src/SCORINFO
src/acs_source/unholy/uh_teaminfo.acs
src/acs_source/hud/scoreboard_icons.acs
src/acs_source/hud/player_portraits.acs
src/acs_source/compat/mods/uix/uixteam.acs
src/acs/UIXTEAM.o                   # 编译产物，gitignored；构建时生成
```

修改：

```text
src/acs_source/unholy/unholy.acs
src/acs_source/unholy/uh_round_helpers.acs
src/acs_source/unholy/uh_access.acs
src/acs_source/unholy/uh_events.acs
src/acs_source/unholy/uh_bosscore.acs
src/acs_source/unholy/uh_dickhead_revival.acs
src/acs_source/hud/uh_bars.acs      # 若由该 library 承载 scoreboard client loop
src/CVARINFO.user
src/CVARINFO.server                 # 仅在增加 spectator/server 策略时
src/MENUDEF                         # 暴露队友栏选项
```

最终应尽量把状态同步集中在 `PlayerLifeStatusArr_UpdateFunc` 和 bonus-event 生命周期入口，避免在每个角色脚本中零散维护。

## 实施阶段

### D1：语义和同步基础

1. 增加客户端状态缓存和 full snapshot 请求/响应。
2. 所有 `playerlifestatusarr` 写入收敛到更新 helper；审计仍直接赋值的路径。
3. 同步 1-vs-all active/target；结束时可靠清空。
4. 实现并单元式检查 `UH_AreDisplayTeammates`、`UH_CanSeeScoreIcon` 权限矩阵。

验收：两客户端对同一 subject 能得到不同的可见性结论；晚加入客户端得到完整正确状态。

### D2：SCORINFO built-in scoreboard

1. 添加 GAMEINFO custom texture data。
2. 添加 SCORINFO `UHPlayerIcon` 并替换 ColumnOrder。
3. 建立公共头像数据库。
4. 添加 CLIENTSIDE TAB 刷新与断线/换图清理。

验收：仍为 Zandronum built-in scoreboard；名字、Ping、排序、滚动不变；头像满足权限矩阵。

### D3：Unholy 原生队友栏

1. 注册 Assist Display。
2. 实现文本、HP、Armor、武器、死亡和头像显示。
3. 添加用户 CVAR/MENUDEF。
4. 验证 camera、死亡和复活切换。

验收：无 UIX 时提供稳定队友栏；普通 Eye 不出现队友；1-vs-all 多人方互相显示。

### D4：UIX shadow 兼容

1. vendor UIXTEAM v3bh 源码并保留来源注释。
2. 只替换关系过滤和人数统计。
3. 编译成 `UIXTEAM.o`，不改 LOADACS。
4. 实现 UIX 开启时抑制 Unholy 原生队友栏。

验收：UIX 所有原选项继续工作；没有双重显示；非 Unholy 模式行为不回归。

### D5：回归、文档和打包

1. 静态编译全部受影响 ACS library。
2. 打包 `src/` 到 `out/build.pk3`。
3. 只有静态检查无法证明的 scoreboard/UIX/联网行为才进行 focused runtime test。
4. 更新 UIX 加载顺序和选项说明。

## 测试矩阵

### 无 UIX

- 2+ Survivor：彼此队友栏可见，TAB 彼此头像可见。
- Survivor 看 Boss：不进队友栏，但 TAB Boss 头像可见。
- Boss 看 Survivor：Survivor 不进队友栏，TAB Survivor 头像隐藏。
- 多 Boss：Boss 彼此队友栏和 TAB 头像可见。
- 普通 Eye：无 Eye 队友栏；TAB 仅自己和所有 Boss 头像可见。
- Survivor 看 Eye：Eye 不进队友栏且 TAB 头像隐藏。
- 死亡、复活、Dickhead revival 后关系及时更新。
- 晚加入、断线、换图没有旧头像残留。

### 1-vs-all

- 单人目标不显示多人方为队友。
- 多人方互相显示队友。
- 无论目标是否 Morph 为 Eye，目标身份不丢失。
- TAB 对所有有效玩家公开头像。
- event 结束/中止后立即恢复常规权限。

### 其他 bonus event

- `ALL_EYE`/`EYE_TEAM` 但非 ONEVSALL：不自动建立 Eye 队友栏。
- FFA：无队友栏，TAB 使用常规角色权限或事件明确规定的公开策略。
- Versus Boss：对战双方不能因同为 Boss 被错误当队友；TAB 仍因 Boss 公开规则显示双方头像。

### UIX

- UIX disabled：Unholy 原生队友栏工作。
- UIX enabled、Team Info disabled：回退 Unholy 原生队友栏。
- UIX enabled、Team Info enabled：只显示 UIX 队友栏。
- UIX 的 mugshot/HP/weapon/dead/layout/alpha/wrap 选项保持有效。
- 大量玩家下 wrap-hide 依据逻辑可见队友数，不依据引擎 Team 人数。
- 非 Unholy DM/TLMS/coop 保持 UIX v3bh 原行为。

### Built-in scoreboard

- 不同分辨率、HUD scale、横纵状态栏；
- 玩家数足以触发 scoreboard 缩放/滚动；
- 活跃、死亡、真观战和观察 camera；
- 头像为空时列宽稳定，不破坏名字列；
- UIX 同时加载时 SCORINFO 最后加载者行为有文档说明；
- intermission/result sequence 不泄露下一回合未确定角色。

## 风险与护栏

1. **SCORINFO 所有权冲突**：多个 addon 可覆盖同一 scoreboard/列。实现时记录兼容顺序，避免静默丢列。
2. **客户端自定义数据污染**：每次 full snapshot、断线和换图都覆盖/清空全部槽；不能只更新当前存活玩家。
3. **死亡 Actor 不存在**：权限状态必须来自客户端缓存；头像可缓存最后一个有效角色纹理供死亡行使用。
4. **Morph 时序**：1-vs-all target 必须先同步目标身份，再允许 Demoneye morph 覆盖生命状态。
5. **字符串表增长**：头像纹理名来自有限静态表，不在每 tic 用动态 `StrParam` 生成新字符串。
6. **UIX 版本漂移**：vendored 文件注明基准 v3bh；升级 UIX 时对照上游 UIXTEAM 差异，不能盲目覆盖。
7. **隐私规则分叉**：队友栏与 TAB 头像分别调用专用函数，但共享同一客户端状态；禁止复制散落的条件链。
8. **不伪造引擎 Team**：不能为迎合 UIX/SCORINFO 调用 `Player_SetTeam`，否则会改变伤害、胜负和引擎行为。

## 完成标准

- Unholy 普通 LMS 获得可配置的 TLMS 风格队友信息。
- 普通 Eye 不被视为显示队友；1-vs-all 多人方正确互认。
- UIX v3bh Better Team Display 使用相同逻辑且不双重绘制。
- TAB 仍是 Zandronum built-in scoreboard，由 SCORINFO 自定义 Texture 列控制头像。
- Boss 头像局内始终公开；Survivor、Eye 和 1-vs-all 权限符合矩阵。
- 两客户端、晚加入、死亡/复活、事件开始/结束和换图均无状态泄漏或残留。
- 不修改任何 `../references/` 内容，不引入 ZScript，不改变 Unholy 的游戏规则。
