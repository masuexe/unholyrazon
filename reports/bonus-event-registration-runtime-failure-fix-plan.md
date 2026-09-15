# Bonus Event 注册失败与无效字符串警告排查及修复方案

## 现象

进入 LMS 后，`uh_bonusdefs` 的 23 个内置 Bonus Event 全部报告注册失败，而且同一批错误出现两次：

```text
[Unholy ERROR] uh_bonusdefs: failed to register ffa
...
[Unholy ERROR] uh_bonusdefs: failed to register satan_seal_ffa
```

随后还出现：

```text
Warning: ACS function strlen called with invalid string argument.
```

## 已确认的主根因

动态 Bonus Event API 使用 cvar mailbox 在 `UHADD` 调用方和 `UHADDR` handler 之间传递参数：

- `DefineBonusEvent` 写入 `uh_be_*`；
- `SetBonusEventEX` 写入 `uh_bex_*`；
- 字符串 getter 使用 `uh_be_out_str` 返回结果。

这些名称目前都没有声明在 `src/CVARINFO.ipc` 中。

Zandronum 源码 `src/p_acs.cpp` 中的行为是：

- `SetCVar` / `SetCVarString` 只允许写入已注册、带 `CVAR_MOD` 且可写的 cvar；找不到 cvar 时返回 0，不会创建一个可用的字符串 mailbox。
- `GetCVar` / `GetCVarString` 找不到 cvar 时返回整数 0。

因此当前调用链实际变成：

```text
DefineBonusEvent(..., "ffa", ...)
  -> SetCVarString("uh_be_stem", "ffa") 失败
  -> ACS_NamedExecuteWithResult("uh_DefineBonusEvent_S")
  -> GetCVarString("uh_be_stem") 返回 0，而不是 "ffa"
  -> DefineBonusEventCore 检查 stem 失败
  -> 返回 UHBE_FAIL
  -> uh_bonusdefs 打印注册失败
```

所有事件共用同一组缺失的 mailbox，所以会整批失败，而不是某一条事件数据有误。

## 为什么错误打印两轮

`uh_bonusdefs.acs` 同时定义了：

```c
script "uh_define_vanilla_bonus" OPEN
script "uh_define_vanilla_bonus_cs" OPEN CLIENTSIDE
```

Zandronum 在单机环境会在同一进程中运行普通 OPEN 与 CLIENTSIDE OPEN；监听服务器也需要兼顾服务器表和本地客户端表。因此 `UH_RegisterVanillaBonusEvents()` 被调用两次，缺失 mailbox 的失败日志也完整重复两次。

这不是需要删除 CLIENTSIDE 注册脚本的证据。补齐 cvar 后，现有 `DefineBonusEventCore` 会允许相同 `(id, stem)` 更新，第二轮注册应当成功且不打印错误。纯客户端仍需要 CLIENTSIDE 注册来获得本地 HUD 元数据。

## 修复方案

### 1. 在 CVARINFO.ipc 注册全部 Bonus Event mailbox

在 `src/CVARINFO.ipc` 中新增独立的 `DefineBonusEvent IPC` 区块。不要只补 `uh_be_stem`；必须一次补齐 API 当前读写的所有名称。

```c
// DefineBonusEvent IPC
local noarchive int uh_be_id;
local noarchive string uh_be_stem;
local noarchive string uh_be_name;
local noarchive string uh_be_music;
local noarchive string uh_be_credit;
local noarchive string uh_be_sound;
local noarchive string uh_be_hud1;
local noarchive string uh_be_hud2;
local noarchive string uh_be_startcb;
local noarchive string uh_be_rebuildcb;
local noarchive string uh_be_endcb;
local noarchive int uh_be_arg1;
local noarchive int uh_be_arg2;
local noarchive int uh_be_arg3;
local noarchive int uh_be_flags;
local noarchive int uh_be_weight;
local noarchive int uh_be_minp;
local noarchive int uh_be_maxp;
local noarchive string uh_be_out_str;

// SetBonusEventEX IPC
local noarchive string uh_bex_base;
local noarchive string uh_bex_ex;
local noarchive int uh_bex_threshold;
```

类型必须与调用端一致：所有 ACS `str` 参数和返回槽使用 `string`，其余使用 `int`。继续使用 `local noarchive`，因为这些字段只是同一实例内立即消费的暂存参数，不是用户设置、服务器设置或持久化状态。

### 2. 不修改注册脚本数量和 LOADACS 顺序

保留：

- `uhdt` 在 `uhaddr` 之前；
- `uhaddr` 在 `uh_bonusdefs` 之前；
- 普通 `OPEN` 与 `OPEN CLIENTSIDE` 两个 definitions 入口。

当前日志已经证明 `uh_bonusdefs` 和 handler 能被找到；失败发生在参数进入 `DefineBonusEventCore` 之后。调整 LOADACS 或增加任意 `Delay` 不能修复缺失 cvar。

### 3. 加强注册失败诊断（推荐）

目前每个调用只报告笼统的 `failed to register <stem>`，无法区分空 stem、ID 冲突、范围错误或 mailbox 缺失。

可在 debug 构建或 `UH_LOG_DEBUG` 下增加一次 mailbox 自检：

```c
if (!SetCVarString("uh_be_stem", "ffa")) {
    UH_Log(UH_LOG_ERROR, "DefineBonusEvent IPC cvars are not registered");
}
```

更稳妥的长期做法是在注册函数中检查每个 `SetCVar*` 的返回值；任一写入失败时不要调用 handler，直接返回 `UHBE_FAIL` 并输出一次明确的 IPC 配置错误。日志应限流，避免 23 条事件重复打印同一根因。

## `strlen` 警告的判断

Zandronum 只有在 `StrLen` 收到不能由 ACS string table 解析的 cell 时才打印：

```text
Warning: ACS function strlen called with invalid string argument.
```

未声明的 `GetCVarString` 返回整数 0，因此缺失字符串 cvar具备制造这种无效值的条件。不过当前 Bonus Event 注册、校验与启动代码主要使用 `StrCmp`，没有直接对 `uh_be_*` 调用 `StrLen`；仅凭这段日志还不能把具体 `StrLen` 调用点唯一定位到 Bonus Event。

处理顺序应为：

1. 先补齐所有 `uh_be_*`、`uh_bex_*` 和 `uh_be_out_str` 声明。
2. 重新启动全新的进程/地图，避免旧实例的 cvar 和 ACS 状态干扰。
3. 确认 23 个注册错误全部消失。
4. 观察 `strlen` 警告是否仍出现。
5. 若仍出现，它是独立问题；按启动阶段在现有 `StrLen` 调用周围记录来源字符串和调用模块，不要通过把无效 cell 当作 `""` 静默掩盖。

优先检查所有形如 `StrLen(GetCVarString(...))` 的路径，以及从未初始化字符串数组、第三方 UI/HUD addon 或动态 getter 取得字符串后传入 `StrLen` 的路径。用户日志中该警告出现在 UI Extensions 和 Damage Display 启动信息附近，也应使用最小加载组合区分本 mod 与外部 HUD addon。

## 验证计划

### 静态检查

1. 从 `DefineBonusEvent`、`SetBonusEventEX`、所有 Bonus Event getter 和 `uhaddr.acs` 提取 `uh_be_*` / `uh_bex_*` 名称。
2. 与 `src/CVARINFO.ipc` 做全集对比，要求没有缺项、拼写差异或类型差异。
3. 保证没有把 mailbox 放入 `CVARINFO.user`、`CVARINFO.server` 或 archive cvar。
4. 运行 `git diff --check`。

### ACS 编译

使用原生 Linux ACC：

```bash
PATH=/home/user/appfiles/acc-1.60-linux64:$PATH \
  ./tools/compile-acs.sh /tmp/unholyrazon4-bonus-ipc-fix
```

要求最终输出 `ACS COMPILE OK`。注意 ACC 编译不会验证 CVARINFO 中是否声明了运行时动态字符串名称，所以“编译通过”不能替代下一步运行验证。

### 运行验证

使用项目的最小 v6b LMS profile，并保持 base game 与 misc fixes 的规定加载顺序：

1. 全新启动一局 LMS。
2. 确认不再出现任何 `uh_bonusdefs: failed to register ...`。
3. 在服务器侧运行 `rz_debug_BonusEventDBCheck`，要求返回 0，并看到 `BonusEventDBCheck: all checks passed`。
4. 检查 `ffa`、普通 Demoneye event、One-vs-All、Football、Boss FFA 和一个 EX relation 的 metadata/回调均能解析。
5. 在单机/监听服务器确认双重注册不产生错误或额外条目。
6. 连接一个纯客户端，确认客户端能读取事件名称、音乐和 HUD 文本。
7. 再检查 `strlen called with invalid string argument` 是否存在；若仍存在，用最小加载组合分别移除 UI Extensions、Damage Display 等 addon 来确定归属。

## 完成标准

- 所有 Bonus Event mailbox 都已在 `CVARINFO.ipc` 注册且类型正确。
- 两个 OPEN 注册入口均成功，23 个内置事件只形成各自一条有效数据库记录。
- `rz_debug_BonusEventDBCheck` 返回 0。
- 随机、强制和 EX Bonus Event 均能读取有效 metadata 并启动。
- 无 Bonus Event 注册失败日志。
- `strlen` 警告消失；若确认来自独立 addon，则另立报告并附最小复现，不与本修复混在一起。
