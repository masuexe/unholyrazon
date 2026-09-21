# 队友信息 Definition API 接入实施方案

## 结论

队友栏不应建立另一套独立的“角色、武器、头像”总表。建议把现有数据库作为主数据源：

- survivor：`DefineSurvivor`
- boss：`DefineBoss`
- Demoneye：`DefineDemoneye`
- 武器名、Ammo1、Ammo2：MM8BDM DTADD 的 `DefineWeapon` / buster definition

在此基础上新增一个很小的、按 player actor class 索引的 **presentation 覆盖表**，只保存队友栏与 scoreboard 真正特有的显示数据。普通角色由已有 `Define*` 表解析名称和身份；特殊 morph、同一角色的不同头像，以及现有 mugshot 字段无法直接表达的纹理，才使用覆盖表。

这比直接给三个已有 `Define*` 增加参数更稳妥：不会破坏已经按旧签名编译的 addon，也不会让已经有 14 个参数的 `DefineBoss` 继续膨胀。

## 当前硬编码边界

### 应移除的硬编码

`src/acs_source/unholy/uh_teaminfo.acs` 中：

- `UH_Ti_GetClassName` 对 `MegaManU`、`BusterExpert` 等名字的特判；
- `_U` 后缀裁剪作为正式显示名来源；
- 通过 `uhPortraitClass[]` / `uhPortraitTex[]` 的固定数组解析角色；
- LuckyLass、Eyelento morph 等 scoreboard 头像的零散特判。

`src/acs_source/hud/player_portraits.acs` 中：

- 197 行 class → texture 固定索引；
- 单独的 scoreboard override 表；
- 由 UIX `PBMug_*` 脚本反向生成这份表的维护流程。

这些数据目前能覆盖内建内容，但 addon 新增 player class 后，即使已调用 `DefineSurvivor` / `DefineBoss` / `DefineDemoneye`，队友栏和 scoreboard 仍不知道其显示名或头像。

### 已经是动态数据，不应重做

- HP、Max HP、BasicArmor、吸收率、Extra Life 都是按当前 player actor 实时读取，不是 class 白名单。
- 武器显示已经由 `UH_TOOLS` 中的 `weapon_display.acs` 查询 8BDT：`findWeaponByActor`、`getWeaponTag`、`getWeaponAmmoType`、`getWeaponAmmo2Type`。
- 服务端按 viewer 授权并用 `NamedExecuteClientScript` 下发快照的方式是正确的。
- 队友关系、bonus event 阵营和 scoreboard 可见性策略与本次数据注册解耦，不应借机改写。

因此，本次工作的核心是把 **class presentation** 接入定义 API，并让现有消费者统一调用同一个 resolver。

## 数据模型

### 1. 继续以三个角色注册表为权威身份表

角色的 actor、阵营类型和标准名称继续来自 UHDT：

```acs
FindSurvivorByActor / GetSurvivorName
FindBossByActor     / GetBossName
FindEyeByActor      / GetEyeHudName
```

解析顺序建议固定为 survivor → boss → eye。三个 actor 身份本来就应全局唯一；若同一 actor 被注册到多个角色表，应记录错误并采用第一个匹配，而不是随加载顺序随机覆盖。

不要依赖 `PlayerClass()` 等于 definition id。addon survivor 追加到 KEYCONF 后，这两个编号本来就可能不同。

### 2. 新增通用 presentation 覆盖表

在 `UHDT` 末尾新增固定容量表，建议先给 256 行：

```acs
str uh_tip_actor[UH_MAX_TEAM_PRESENTATION];
str uh_tip_name[UH_MAX_TEAM_PRESENTATION];
str uh_tip_portrait[UH_MAX_TEAM_PRESENTATION];
str uh_tip_scoreicon[UH_MAX_TEAM_PRESENTATION];
int uh_tip_flags[UH_MAX_TEAM_PRESENTATION];
int uh_tip_count;
```

字段语义：

- `actor`：DECORATE player actor class，大小写不敏感的唯一键；必填。
- `name`：队友栏第三行使用的短名称；空字符串表示回退到角色主表名称。
- `portrait`：Unholy 原生队友栏和 UIX Better Team Display 使用的纹理；空表示无头像。
- `scoreicon`：SCORINFO 使用的纹理；空表示回退到 `portrait`。
- `flags`：只保存稳定的显示语义，首版可保留为 0，不要预先塞入游戏逻辑。

覆盖表必须按 actor 去重。重复定义采用“替换已有行并返回原 row”的语义，方便后加载 addon 修正显示；空 actor、容量耗尽返回明确失败码并写一次日志。

### 3. 不把头像数组 row 当成网络协议

当前服务器发送 `uhtiportrait` 数组下标，只有服务器与客户端的固定数组完全相同才安全。动态 addon 出现后，隐式 row 会受双端注册顺序影响。

建议把同步身份改为 **角色种类 + definition id**：

- survivor：`role = PLS_SURVIVOR`，`id = FindSurvivorByActor(actor)`；
- boss：`role = PLS_BOSS`，`id = FindBossByActor(actor)`；
- eye：`role = PLS_EYE`，`id = FindEyeByActor(actor)`；
- 只存在于 presentation 覆盖表的特殊 morph：使用单独的 `UH_TI_ID_PRESENTATION` kind，并发送 presentation row。

前三类 id 已经是游戏逻辑身份，并且现有 addon recipe 已要求在普通 `OPEN` 和 `OPEN CLIENTSIDE` 中以相同顺序注册。对 presentation-only row 也必须应用同一双注册规则。同步包应包含 kind，不能只传一个可能与其它表碰撞的整数。

如要彻底消除 presentation row 的顺序依赖，可在后续版本把特殊 morph 绑定到其基础角色 id，并只同步基础 id；本阶段不需要引入字符串网络传输。不要每 7 tic 用 `NamedSendNetworkString` 发送 actor class，这会增加消息和时序复杂度。

## Public API 设计

### 主入口

在 `uhadd.acs` 增加：

```acs
#define UHTIP_OK          0
#define UHTIP_FAIL       -1
#define UHTIP_FULL       -2
#define UHTIP_BAD_ACTOR  -3

function int DefineTeamPresentation(
    str actor,
    str shortName,
    str portrait,
    str scoreIcon,
    int flags);

function int FindTeamPresentation(str actor);
function str GetTeamPresentationName(str actor);
function str GetTeamPresentationPortrait(str actor);
function str GetTeamPresentationScoreIcon(str actor);
```

`DefineTeamPresentation` 沿用 UHADD/DTADD 已验证的 cvar mailbox 模式：

1. `UHADD.acs` 写入 `uh_tip_*` local noarchive cvar；
2. 调用 `uh_DefineTeamPresentation_S`；
3. `UHADDR` 立即读取并写入 UHDT；
4. 所有 `SetCVar*` 结果使用位运算 `&` 累积，mailbox 缺失时不调用 handler，并只报告一次根因。

相应地更新：

- `src/CVARINFO.ipc`
- `src/acs_source/_imports/uhdt.acs`
- `src/acs_source/corescripts/api_handlers/uhaddr.acs`
- `src/acs_source/_includes/mod_api/uhadd.acs`

### 内部统一 resolver

增加以下内部查询，不允许 HUD 消费者自己扫描三个表：

```acs
function int UH_FindPlayerDefinition(str actor);
function str UH_PlayerDisplayName(str actor);
function str UH_PlayerPortrait(str actor);
function str UH_PlayerScoreIcon(str actor);
```

推荐解析规则：

1. 查 `DefineTeamPresentation(actor, ...)`；对应字段非空时直接使用。
2. 名称字段为空时，按 actor 查 survivor/boss/eye 主表。
3. eye 使用 `GetEyeHudName`，确保 `Demoneye` 后缀规则仍由 `DefineDemoneye` flags 决定。
4. 都未注册时，名称回退到 actor class；头像回退为空。
5. 非法/空 actor 返回空，不猜测头像。

主表名称含颜色码是合法结果。若希望队友栏使用不同于播报的短名称，应显式注册 `shortName`，不要在 resolver 中通用地剥离颜色码或 `_U` 后缀。

### 为什么不修改 `DefineSurvivor/Boss/Demoneye` 签名

- 已编译 addon 仍会按旧函数体和旧 mailbox 调用；直接加参数会造成源代码和二进制兼容问题。
- boss 定义已经很长，presentation 是独立职责。
- 特殊形态（例如 `EyelentoMajorDemoneye`）未必是新的 boss/survivor/eye definition，却仍需要显示数据。
- 通用 actor-keyed setter 可以覆盖三种阵营和临时 morph，不需要三套重复 API。

未来若做破坏性大版本，可以提供新的 convenience wrapper，例如 `DefineSurvivorEx`，内部先调用 `DefineSurvivor` 再调用 `DefineTeamPresentation`；首版没有必要。

## 武器与 Ammo 接入

### 正常路径

队友栏继续只查询 `UH_TOOLS`：

```text
ready weapon actor
  → findWeaponByActor / findBusterUpgradeByActor
  → tag + ammo1 type + ammo2 type
  → server读取实际 ammo 数值
  → 每 viewer 下发
```

addon 的普通武器必须通过 MM8BDM `DefineWeapon` 注册。这样队友栏、随机武器系统和其它 MM8BDM UI 共享同一元数据，而不是只对 Unholy 生效。

### 回退与覆盖

首版不要增加 `DefineTeamInfoWeapon`。未知武器保持不显示 weapon line，并根据现有 `subline` 规则显示 class name。这是安全且可预期的降级。

只有在实际发现某类 player weapon 无法合法进入 DTADD（例如注册会改变不应改变的随机池语义）时，才在 `UH_TOOLS` 增加一个独立 weapon-display override 表。这个表必须留在 `UH_TOOLS`；`unholy` 仍不得 import 8BDT，以避免 8BDT/UHDT 的大小写不敏感符号碰撞。

## 消费者改造

### 原生 TLMS 风格队友栏

- `UH_Ti_GetClassName` 改为调用 `UH_PlayerDisplayName`。
- 删除五个手工名称特判和 `_U` 裁剪。
- live actor 发生变化时，按已有 class cache 重新解析。
- dead/body-less 玩家使用同步的 definition identity 和客户端本地定义表回退。
- 保持现有 stat 授权、chasecam 自己行、dead row 和 HUD scale 逻辑不变。

### SCORINFO scoreboard

- `UH_ClientPortraitTex` 改为调用 `UH_PlayerScoreIcon`。
- 删除 `UH_ScoreIconOverrideTex` 固定表；差异直接由 presentation 的 `scoreIcon` 字段表达。
- 仍保留“live class 优先、死亡后保留最后一次有效纹理、late join 使用同步 identity”的三级缓存。
- 未注册头像时给 `UHPlayerIcon` 写空字符串，不能回退到 player color 方块或错误角色头像。

### UIX Better Team Display

目前 UIX 通过动态脚本名 `PBMug_<Class>` 查头像，ACS 不能在运行时创建新 named script，因此仅增加数据库还不能让 addon class 自动兼容 UIX。

应修改项目内的 UIX shadow：

1. 先调用 Unholy 的通用 named resolver，例如 `uh_GetTeamPortraitForTid`；
2. 有结果时直接使用；
3. 无结果时再调用 stock `PBMug_<Class>`，保持非 Unholy/旧 addon 兼容；
4. UIX 未加载时，这个改动不影响原生栏。

resolver 只接收 TID，由本地 client 读取 actor class 和本地 presentation 表。不要让 UIX 自己复制 UHDT 查找规则。

完成迁移后，`uh_uix_mugshots.acs` 中为 Unholy 内建角色生成的近 200 个 `PBMug_*` 脚本可在一个单独清理提交中删除；第一阶段先保留作为回退，便于回归比较。

## 内建数据迁移

### 注册位置

presentation 注册跟随现有 definition library：

- survivor 行放在 `uh_survdefs.acs`；
- boss 行放在 boss definition 注册流程；
- eye 行放在 `uh_eyedefs.acs`；
- 非标准 morph 行放到最接近其定义的注册库，不再集中进 `player_portraits.acs`。

普通 `OPEN` 与 `OPEN CLIENTSIDE` 必须调用完全相同的 presentation 注册函数。客户端分支不能使用 `UHInPlay()`，与现有角色定义 recipe 一致。

### 迁移策略

建议用现有 `player_portraits.acs` 生成第一版 `DefineTeamPresentation` 调用，避免人工抄写 197 行。生成后做三类校验：

- actor 在 survivor/boss/eye 主表中存在，或被明确标记为 presentation-only morph；
- portrait texture 非空且与当前 UIX 输出一致；
- scoreboard 差异显式进入 `scoreIcon`，目前至少包括 LuckyLass 和 Eyelento 特殊形态。

迁移完成并验证后删除固定数组，不要长期维护“定义表 + 固定 portrait 表”两个真相源。

## Addon 注册模板

```acs
#library "MYUHDEFS"
#include "zcommon.acs"
#import "uh_log.acs"
#include "UHADD.acs"

function void RegisterMySurvivors(void)
{
    DefineSurvivor(-1, "MySurvivor", "\cGMy Survivor", "MYBHWFACE");
    DefineTeamPresentation(
        "MySurvivor",
        "My Survivor",
        "MYTEAMFACE",
        "MYSCOREFACE",
        0);
}

script "myuh_defs" OPEN
{
    if (!UHInPlay()) terminate;
    RegisterMySurvivors();
}

script "myuh_defs_cs" OPEN CLIENTSIDE
{
    RegisterMySurvivors();
}
```

武器仍按 MM8BDM 标准调用 `DefineWeapon`。若 `scoreIcon` 与 `portrait` 相同，传空字符串即可。

文档还应明确：addon 必须在 Unholy 的 definitions 之后加载；服务端和每个客户端必须加载同一组 addon；重复 actor 大小写不敏感；客户端缺少纹理时只能显示为空，不能由服务端发送任意资源名来绕过资源一致性。

## 实施顺序

### 阶段 1：API 和 resolver，不改表现

1. 在 UHDT 添加 presentation 表和 core getters。
2. 在 UHADDR 添加 named handlers。
3. 在 UHADD 与 `CVARINFO.ipc` 添加 public API/mailbox。
4. 实现统一的 actor → name/portrait/scoreIcon resolver。
5. 由现有表生成内建 registration，使 resolver 输出与当前硬编码逐项一致。

验收标准：现有 197 个 actor 的三个输出（名字、team portrait、score icon）与改造前一致。

### 阶段 2：切换消费者

1. 原生队友栏切换名称 resolver。
2. scoreboard 切换 scoreIcon resolver 与 definition identity fallback。
3. UIX shadow 优先调用通用 resolver。
4. 保留旧 portrait/PBMug 数据作为临时 fallback，并加入 unknown actor 日志或 debug 命令。

验收标准：UIX 开/关、live/dead、morph、chasecam、late join 的显示无回归；一个测试 addon 无需修改 Unholy 源码即可显示新角色。

### 阶段 3：删除双重真相源

1. 删除 `UH_Ti_GetClassName` 手工特判。
2. 删除固定 `uhPortraitClass/uhPortraitTex` 与 scoreboard override 数组。
3. 确认 UIX fallback 覆盖非 Unholy 内容后，再决定是否删除内建 `PBMug_*` 脚本。
4. 更新 `uhadd.acs` 顶部 addon recipe 和项目 AGENTS 文档。

不要把阶段 1 到阶段 3 压成一次大改；保留一个版本的 fallback 会显著降低 scoreboard/UIX 同时迁移的定位难度。

## 验证矩阵

### 静态与编译验证

- ACC 编译全部受影响库，确认没有 8BDT/UHDT 标识符碰撞。
- 检查 `LOADACS` 顺序仍为 `UHDT → UHADDR → definitions → UH_TOOLS → unholy`。
- 校验所有 mailbox cvar 均存在，故意漏掉一个时应只报一次明确错误。
- 重复 actor、空 actor、满表、未知 actor、不同大小写各有测试。
- 自动比较迁移前固定 portrait 表与迁移后 resolver 的内建输出。

### 本地显示验证

- UIX 关闭：名称、血量、护甲、武器 tag、双 ammo、class fallback 正确。
- UIX 开启：只显示 UIX 一份队友信息，新 addon class 头像可解析。
- weapon 未注册：不打印 raw actor class，按 `subline` 规则回退 class name。
- live morph 后立即换头像/名称，死亡后保留最后有效显示。
- scoreboard 的 LuckyLass 与 Eyelento 特殊 score icon 不回归。

### 联机验证

至少使用 dedicated server + 两个 client：

- server/client registration row 和 definition id 一致；
- 普通 LMS survivor/boss/eye 权限不变；
- 1-vs-all、多-vs-多、FFA、全员 eye 的头像策略不变；
- living chasecam 观察队友时仍显示 console player 自己那一行；
- 中途加入与 spectator 只要求安全降级，不因缺少 presentation 扩大信息权限；
- 一端缺 addon 时显示为空或 actor fallback，不崩溃、不显示错误玩家头像。

## 非目标

本次不开放任意自定义 HUD 列或任意 stat callback。ACS 没有函数指针，而当前服务器到客户端的 stat 消息已经占满四个参数并采用位打包；把“任意 addon 数据”塞进同一包会显著增加同步与权限风险。

若以后确实需要 rage、charge、class meter 等自定义队友数据，应另设计：

- 独立、按需启用的 named-script provider；
- 独立的 per-viewer 授权消息；
- 明确的更新频率、范围和数值位宽；
- UIX 与原生 HUD 各自的渲染插槽。

它不应成为本次移除名称/头像硬编码的前置条件。

## 最终完成标准

完成后，新增一个标准 survivor/boss/eye 的最低成本应为：调用原有 `Define*`，再用一行 `DefineTeamPresentation` 提供显示纹理；其武器按 MM8BDM `DefineWeapon` 注册。无需编辑 `uh_teaminfo.acs`、`player_portraits.acs`、SCORINFO 或 UIX 的 class 白名单。

内建角色、addon 角色、特殊 morph 的显示都通过同一个 resolver，未知内容安全降级，服务器仍只向被授权 viewer 发送数据。
