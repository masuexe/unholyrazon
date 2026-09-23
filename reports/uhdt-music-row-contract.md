# 音乐行契约（UHDT CRUD 第一张样板表）

身份主表（Survivor、Demoneye、Item、LMS/Bonus Event、Boss）仍使用现有 `Define*` 语义，本文件不改变它们。下面只约束 Boss/Event 共用音乐表。

## 身份与生命周期

- 主键：Boss 为 `(bossId, kind, phase, lump)`；Event 为 `(UHMUS_GLOBAL, kind, phase, lump)`。`StrCmp` 区分 lump 大小写。
- `uh_bossmusiccount` 是本地图分配上界。行号不移动、不改挂到别的键。删除只把该行标成墓碑。
- 有效位和启用位打包在 `uh_bossmusicoptional` 的 bit 1 与 bit 2（bit 0 仍是 optional）。UHDT 的 map 变量数量已到 ACC 上限，不能再加数组。
- 有效（`IsMusicRowDefined`）和启用（`IsMusicRowEnabled`）分开计数：`GetDefinedMusicRowCount` / `GetEnabledMusicRowCount`（UHADD：`GetDefinedMusicCount` / `GetEnabledMusicCount`）。
- 注册期或下一回合生效。`OPEN` 与 `OPEN CLIENTSIDE` 必须对同一键做同一调用。监听服务器两侧都会跑时，同键 `Add` 是幂等更新。
- 播放在选中后立刻拷走 lump 与曲目信息。胜负曲时长在同一次调用里读完，中间没有 `Delay`。删除或禁用只影响之后的抽取。

## 操作

| 操作 | 有效行 | 已禁用的有效行 | 墓碑 | 没有这把键 |
| --- | --- | --- | --- | --- |
| `Add*` | 改标题、专辑、作者、权重、optional；保持禁用状态 | 同左 | 原位重写字段并启用 | 容量够则追加并启用；否则 `UHMUS_FAIL`，表不变 |
| `Set*Enabled` / `Disable*` / `Enable*` | 只改启用位 | 同左 | `UHMUS_ERR_NOTFOUND` | `UHMUS_ERR_NOTFOUND` |
| `Remove*` | 变墓碑，普通查询失败 | 同左 | `UHMUS_ERR_NOTFOUND` | `UHMUS_ERR_NOTFOUND` |
| `Is*Defined` / `Find*` / `Get*ByRow` | 可见 | 可见 | 不可见 | 不可见 |
| `Pick*MusicRow` | 参与（optional 规则不变） | 不参与 | 不参与 | — |

`Add*` 的失败返回保持 `UHMUS_FAIL`（`-9999`）。新写操作返回 `UHMUS_OK`、`UHMUS_ERR_NOTFOUND`、`UHMUS_ERR_BADARG`。键不合法（空 lump、`*`、kind 与入口不符、phase < 0、Boss 入口用了全局 id）是 `UHMUS_ERR_BADARG`，不写表。mailbox 的 `SetCVar` / `SetCVarString` 失败返回 `UHMUS_FAIL`，不调用 handler。

`UHMUS_ERR_CONFLICT`、`UHMUS_ERR_REFERENCED`、`UHMUS_ERR_CAPACITY` 留给后续身份表。音乐容量不足继续走 `Add*` 的 `UHMUS_FAIL`。

加权抽取的求和与落点使用同一个 `UH_MusicRowMatchesPick`。

## 直接数组访问

`uh_bossmusic*` 只在 `src/acs_source/_imports/uhdt.acs` 读写。播放与 LMS 选曲走 `PickBossMusicRow` / `PickEventMusicRow` 和 `GetBossMusic*ByRow`：`unholy/uh_music.acs`、`unholy/uh_bossselect.acs`。Addon 用复合键，不用行号。

## Addon 入口

Boss：`SetBossMusicEnabled`、`DisableBossMusic`、`EnableBossMusic`、`RemoveBossMusic`、`IsBossMusicDefined`、`IsBossMusicEnabled`，以及对应的 `*ByActor`。

Event：`SetEventMusicEnabled`、`DisableEventMusic`、`EnableEventMusic`、`RemoveEventMusic`、`IsEventMusicDefined`、`IsEventMusicEnabled`。LMS 另有 `SetLMSMusicEnabledByStem` 与 `RemoveLMSMusicByStem`（phase = 事件 id）。
