# Bonus Event 注册失败修复 — 执行与验证报告

执行对象：`reports/bonus-event-registration-runtime-failure-fix-plan.md`
状态：**已实施并通过运行期验证**

---

## 1. 改动清单

| 文件 | 改动 |
|------|------|
| `src/CVARINFO.ipc` | 新增 `DefineBonusEvent IPC`（19 个 `uh_be_*`）、`SetBonusEventEX IPC`（3 个 `uh_bex_*`）；另补 `uh_db_unmorphpre` / `uh_db_unmorphpost`（SetBossUnmorphCleanup IPC）与 `DefineUnholyGuardFactor IPC`（`uh_gf_actor` / `uh_gf_factor`） |
| `src/acs_source/_includes/mod_api/uhadd.acs` | 新增 `UH_ReportIPCFailure()` 与 `uh_add_ipcfail_reported` 限流标志；`DefineBonusEvent` / `SetBonusEventEX` / `SetBossUnmorphCleanupById` / `DefineUnholyGuardFactor` 改为逐项检查 `SetCVar*` 返回值，任一失败则不调用 handler，直接返回失败并输出一次根因 |
| `src/acs_source/_includes/mod_api/uhadd.acs` | 9 个 addon recipe 注释块补 `#import "uh_log.acs"`（见 §2.2） |
| `out/build.pk3` | 重新编译并打包（16583 个条目，`validate-build-pk3.sh` status=ok） |

`src/LOADACS`、注册脚本数量、`OPEN` / `OPEN CLIENTSIDE` 双入口均未改动。

### 1.1 计划外的同源缺陷（已一并修复）

计划第 2 节静态检查要求「全集对比，没有缺项」。实际执行时该检查暴露出**另外两组同一根因的未注册 mailbox**：

- `uh_db_unmorphpre` / `uh_db_unmorphpost` —— `SetBossUnmorphCleanupById()` 使用，被 `boss_unmorph_cleanups.acs` 调用 19 次。此前每次调用都把无效字符串 cell 写入 UHDT，**所有 boss 的 unmorph cleanup 脚本实际都未注册**。
- `uh_gf_actor` / `uh_gf_factor` —— `DefineUnholyGuardFactor()` 使用（对外 API，本 mod 内部未调用）。`uh_DefineUnholyGuardFactor_S` 会对该值执行 `StrLen(actor)`，是计划第 121 节 `strlen called with invalid string argument` 警告的直接候选路径。

两者与 Bonus Event 属完全相同的缺陷类，已按同一契约修复。

### 1.2 addon recipe 文档缺陷（已修复）

`uhadd.acs` 的函数体调用 `UH_Log()`（9 处），但 9 个 recipe 注释块只教用户写
`#include "zcommon.acs"` + `#include "UHADD.acs"`。实测按 recipe 编写会**编译失败**：

```
src/acs_source/_includes/mod_api/uhadd.acs:712: uh_log_error : Identifier has not been declared.
```

补上 `#import "uh_log.acs"` 后编译通过。已为 9 个 recipe 块统一补上该行。

引擎机制（`p_acs.cpp`）：每个编译产物内嵌 `LOAD` chunk 记录其 `#import` 的库名，
`FBehavior` 加载时按名字在 `ns_acslibrary` 命名空间查找并**自动加载**该库。
所以 `#import "uh_log.acs"` 不需要 `LOADACS` 条目，只要 `acs/uh_log.o` 在 pk3 内即可，
第三方 addon 也能借此加载本 mod 的 `uh_log`。

---

## 2. 静态验证

```
declared: 169   referenced: 136
unregistered mod-owned names: NONE          <- 全部已注册
uh_be_      19/19 declared
uh_bex_      3/3 declared
uh_db_unmorph 2/2 declared
uh_gf_       2/2 declared
duplicates: NONE                            <- 引擎遇到重名会 hard-error
collisions with v6b CVARINFO: NONE
```

类型全部与调用端一致（`SetCVarString`/`GetCVarString` ↔ `string`，其余 `int`）。
`git diff --check` 通过。所有条目保持 `local noarchive`，未进入 `user` / `server` / archive cvar。

未注册名单中剩余 9 个名字全部属于引擎或 v6b 基础包（`sv_MaxClients`、`vid_*`、`mm8bdm_bossstate`、`mm8bdm_intensestate`、`uh_sv_timerend`），均为只读 `GetCVar` 用法，不属于本次缺陷类。

### 引擎语义核对（源码）

- `p_acs.cpp` `SetCVar()`：`cvar == NULL || !(flags & CVAR_MOD)` → `return 0`。未注册名字**静默失败**。
- `p_acs.cpp` `GetCVar()`：`cvar == NULL` → `return 0`。因此 handler 的 `GetCVarString()` 拿到整数 0 而非字符串。
- `d_main.cpp ParseCVarInfo()`：`cvarflags = CVAR_MOD|CVAR_ARCHIVE`，`local` 仅绕过 server/user 强制要求 → `local noarchive` 可被 ACS 写入。

---

## 3. ACS 编译

编译器通过 `PATH` 或 `ACC` 环境变量提供。

```
bash tools/compile-acs.sh
=> ACS COMPILE OK
```

---

## 4. 运行期验证（实机）

无 MCP 时的可用验证通道已查明，记录如下（对后续调试有复用价值）：

- `zandronum-server -stdout` **看不到任何 ACS 输出**。根因在 `c_console.cpp` `PrintString`：
  `if (Args && Args->CheckParm("-host")) { if (printlevel != PRINT_LOW) { ... SERVERCONSOLE_Print(...); } return length; }`
  该分支在 `fputs(copy, stdout)` 之前提前返回，因此 `-host` 下控制台不再走 stdout。
- 可靠通道是 **`+logfile <name>`**（实际文件名会带 `sv_logfilenametimestamp` 时间戳后缀，形如 `<name>__YYYY_MM_DD-HH_MM_SS.log`）。`PrintString` 在 `-host` 提前返回**之前**就写入了 `Logfile`，且逐行 `fflush`。
- ACS `Log()` 走 `PCD_ENDLOG` → `Printf("%s\n", ...)` → `PrintString`，因此 `logfile` 能拿到。
- 客户端必须真正进入地图（`SDL_VIDEODRIVER=offscreen` + `vid_renderer 0` 可用，约 40s 到图）；`-host` 本地游戏能进图但控制台被抑制，故一律以 `+logfile` 读取。

**重要限制（4 次 `-host` 运行实测）**：`-host` / `zandronum-server` 下 **ACS 输出在 stdout 与 `+logfile` 中均不可见**。其中一次运行刻意关掉 `-lastmanstanding`，使 `ub_StartUpSettings` 必然打印 `PrintBold` 并 `UH_Log(WARN, "Respawn protection is disabled.")`，结果 `+logfile` 里除引擎自带的地图横幅外仍然什么都没有。引擎源码层面 `PrintString` 的 `Logfile` 写入确实在 `-host` 提前返回之前，因此实际被吞掉的位置尚未定位；但结论稳定：**服务端模式下无法观测 ACS 日志**。

### 4.1 A/B 对照方法

用 `git worktree add --detach /tmp/uh-old HEAD` 取修复前源码，独立编译打包为 `/tmp/uh-old-build.pk3`，与修复后的 `out/build.pk3` 用完全相同的命令行加载，再叠加一个**只读探针 pk3**（`/tmp/uhprobe.pk3`，`LOADACS: uhprobe`，在 `build.pk3` 之后加载，`Delay(140)` 后经公开 API 读取数据库）。

探针本身不修改任何状态，仅调用 `UH_IsBonusEventDefined` / `UH_FindBonusEventByStem` / `UH_GetBonusEvent*`。

### 4.2 结果

| 探针项 | 修复前 | 修复后 |
|--------|--------|--------|
| `defined bonus events` | **1**（id 0，垃圾行） | **23** |
| `FindByStem(ffa)` | 0（伪命中） | **0**（`UHEVENT_FFA`，正确） |
| `FindByStem(demoneye_parade)` | 0（伪命中） | **11** |
| `FindByStem(football_ffa)` | 0（伪命中） | **13** |
| `FindByStem(boss_ffa)` | 0（伪命中） | **51** |
| `FindByStem(truepower_ffa)` | 0（伪命中） | **100** |
| `FindByStem(satan_seal_ffa)` | 0（伪命中） | **151** |
| `name(13)` | `MechaDragon`（无效 cell） | `Free for All` |
| `stem(13)` | `MechaDragon` | `football_ffa` |
| `music(13)` | `MechaDragon` | `FOOTBALL` |
| `startcb(13)` | `MechaDragon` | `ub_FreeForAll` |
| `hud1(13)` | `MechaDragon` | ``（空，与注册值一致） |
| `flags(13)` / `weight(13)` | 0 / 0 | **1 / 1**（`UHBE_FLAG_FFA`） |
| `startcb(11)` / `rebuildcb(11)` | `MechaDragon` | `ub_OneVsAllEvent` / `uh_RebuildOneVsAllEvent` |
| `name(151)` / `startcb(0)` | `MechaDragon` | `Free for All` / `ub_FreeForAll` |

修复后的 23 条记录与 `uh_bonusdefs.acs` 中的注册字面量逐项吻合（`\cs` 等颜色码由 logfile 的 `V_RemoveColorCodes` 剥离）。

### 4.3 关于「注册失败」日志

修复前**没有**出现计划所描述的 23 条 `failed to register`。原因是无效 cell 在 ACS 字符串表里的解析结果不确定：

- 本机运行中 `GetCVarString("uh_be_stem")` 返回的整数 0 被解析为字符串表索引 0（恰好是非空串），于是 `StrCmp(stem, "") != 0`，`DefineBonusEventCore` 继续执行；`uh_be_id` 同样未注册 → 读到 0，23 次调用全部折叠到 **id 0** 这一条垃圾记录上，因此不返回 `UHBE_FAIL`、也不打印错误。
- 计划作者环境中该 cell 解析为空串，`StrCmp(stem, "") == 0` → 每次返回 `UHBE_FAIL` → 打印 23 条错误。

**两者是同一根因的两种表现**，都说明数据库不可用。修复后两种表现都消失。

### 4.4 `strlen` 警告：四种组合均未复现

`p_acs.cpp` 中该警告的实现值得注意：

```cpp
static bool StrlenInvalidPrintedAlready = false;
if (!StrlenInvalidPrintedAlready)
{
    Printf(PRINT_BOLD, "Warning: ACS function strlen called with invalid string argument.\n");
    StrlenInvalidPrintedAlready = true;
}
```

即**每个进程最多打印一次**，且走 `PRINT_BOLD`（非 `-host` 客户端下会进 stdout 与 `+logfile`）。

用计划提到的完整 addon 组合（`mm8bdm-v6b` + `miscfixes` + `trill-damagedisplay-v7h2` +
`underworld_radio_unbound_v7b` + `razon_soundtest` + `8bdm-uix-v3bh` + `8bdm-hitvoxel-0` + `hudex`）
做了两组对照，两组都成功进入 `MM2DW1`：

| 组合 | 结果 |
|------|------|
| 完整 addon + 本 mod | 进入地图，出现 `UI Extensions enabled.` / `Damage display enabled.`，**无 `strlen` 警告** |
| 完整 addon，移除本 mod | 同上，**无 `strlen` 警告** |

加上此前的修复前/修复后单 mod 运行，共 **4 种组合均未复现**该警告。

静态审计也支持这个结论：mod 内所有 `StrLen` 调用点中，只有两处会拿到 `GetCVarString` 的结果，
且两者都在 `CVARINFO.*` 中正确声明：

- `unholy/uh_bosscore.acs:352` → `uh_dsw_out_str`（`CVARINFO.ipc`）
- `unholy/uh_display.acs:894` → `_uh_servmusiccredits`（`CVARINFO.internal`）

唯一能对无效 cell 调用 `StrLen` 的路径是 `hud/guard_factors.acs:11`（`StrLen(GetCVarString("uh_gf_actor"))`），
其入口 `DefineUnholyGuardFactor` 本 mod 内部没有调用者；扫描全部 addon 的 ACS 产物也确认
**没有任何 addon 引用 `uh_gf_actor` 或 `DefineUnholyGuardFactor`**。本次修复已让该路径不再可能产生无效 cell，
但无法把它认定为原警告的来源。

**结论**：本环境（4 种组合）不可复现，但**用户实测确认该警告在修复后仍然打印**。
因此它不是修复前 mailbox 缺失的副作用，而是一个独立问题。

→ 后续诊断已确认该 warning 来自外部 `8bdm-v6b-miscfixes` 的 `WEPHIDE.acs`：
`validString()` 使用不具备短路语义的 `&&`，导致 `StrLen(0)`。它不是本项目
Bonus Event 修复引入的问题；应在 miscfixes 的 `WEPHIDE.o` 中修复，而不是在本项目
批量修改 `StrLen` 调用。

它每进程只打印一次，事后重跑很容易错过。
**不要**通过把无效 cell 当 `""` 静默掩盖。

### 4.5 对 `rz_debug_BonusEventDBCheck` 的等价覆盖

该脚本本身不可达：首行 `if (GetCVar("lastmanstanding") == 0) terminate;`，而 `lastmanstanding`
是 `CVAR_SERVERINFO` 引擎 cvar，只在 `-host` 服务端为真，服务端模式又观测不到 ACS 输出（§4.1）。

因此按其四组检查逐项复刻为探针，改为**经公开 API** 执行（顺带把 CVARINFO mailbox 也跑了一遍），
在非 `-host` 客户端运行，结果 `TOTAL FAILS=0`：

| 检查组 | 探针输出 | 判定 |
|--------|----------|------|
| 1a. 23 个内置 id 全部已定义 | `defined bonus events=23` | ✅ |
| 1b. stem 双向解析 + name/music 非空（23 项逐项） | `group1 fails so far=0` | ✅ |
| 1c. start 回调名能解析为真实脚本 | `start callbacks resolved=23` | ✅ |
| 2. EX 关系 | `ffa->100`、`parade->111`、`clone->112`、`football->113`、`mlg->-9999`，阈值 `3/3/3/3/0` | ✅ |
| 3. 池资格 | `tier3 reachable=1`；120 次低人数抽取全部 `weight>=1 且 minPlayers<=4` | ✅ |
| 4. 幂等与冲突拒绝 | 同 id 异 stem `-9999`；同 stem 异 id `-9999`；`id -1` 已知 stem 复用 → `0`；同 `(id,stem)` 重注册 → `0`；无泄漏行；数量仍为 23 | ✅ |

`ffa` 行在全部变更后仍为 `name=Free for All / stem=ffa / music=DIXIEMUS / startcb=ub_FreeForAll / flags=1 / weight=1`。

构建探针时的两点注意事项（已写入项目记忆）：

- `uhdt.acs` 与 `uhadd.acs` **不能放进同一个库**：两者有 88 个同名宏（`#define` vs `#libdefine`），
  一起用会报 `Invalid identifier`。因此拆成两个探针库（`uhprobeb` 只用 uhdt，`uhprobea` 只用 uhadd）。
- `PickBonusEvent` 每次调用要扫两遍全表，400 次连打会触发 **`Runaway script ... terminated`**；
  循环内需 `Delay` 让出指令预算。
- `UHEVENT_FFA = 0`、`UHEVENT_FOOTBALL = 13` —— 写断言时不要凭「Football 是 13」把 `ffa` 也写成 13。

---

## 5. 完成标准对照

| 标准 | 状态 |
|------|------|
| 所有 Bonus Event mailbox 已在 `CVARINFO.ipc` 注册且类型正确 | ✅ 19 + 3，类型全对 |
| 两个 OPEN 注册入口均成功，23 个内置事件各形成一条有效记录 | ✅ `defined bonus events=23` |
| `rz_debug_BonusEventDBCheck` 返回 0 | ⚠️ 脚本本身不可达（见下），但其**四组检查全部由探针等价覆盖并通过，`TOTAL FAILS=0`**（见 §4.5） |
| 随机 / 强制 / EX Bonus Event 均能读取有效 metadata | ✅ 6 个 stem 解析正确，metadata 与回调名全部正确 |
| 无 Bonus Event 注册失败日志 | ✅ |
| 单机 / 监听服务器下双重注册不产生错误或额外条目 | ✅ 探针运行在单机（本地）游戏，`OPEN` 与 `OPEN CLIENTSIDE` 两个入口都会执行 → 共 46 次 `DefineBonusEvent`，结果仍是 **23** 条，无重复、无错误 |
| 纯客户端能读取事件名称 / 音乐 / HUD 文本 | ⚠️ 部分覆盖：探针在客户端 VM 上经 CLIENTSIDE 注册后的本地表读取成功，但单机游戏里服务端与客户端共用同一 ACS VM，未做「真实客户端连服务器」的分离验证 |
| `strlen` 警告消失 | ⚠️ **外部问题**。已定位到 miscfixes-v5/v6 的 `WEPHIDE.validString()`；本项目不是根因，修复应在 miscfixes 中完成 |

---

## 6. 后续建议

1. `strlen` 警告不属于本项目；若继续维护 miscfixes，应将 `WEPHIDE.acs` 的
   `validString()` 改为显式 `if (in == 0) return false;` 后重编发布。该 warning
   每进程只打印一次，验证时必须换新进程。
2. 连接一个纯客户端，确认其能读取事件名称 / 音乐 / HUD 文本（单机游戏里服务端与客户端共用
   同一 ACS VM，本次未做分离验证）。
3. 可选：跑一次 `puke rz_debug_BonusEventDBCheck`。其四组检查已由探针等价覆盖并通过（§4.5），
   此步只是用项目自带脚本再确认一次。
4. `uhadd.acs` 的 recipe 已补 `#import "uh_log.acs"`（本次修复）。若还有其他对外 include
   （`uhdt.acs`、`uh_acsutils.acs` 等）存在同类文档缺口，应按同一方式核对。
5. 同类风险应常态化拦截：**对未在 `CVARINFO.*` 声明的名字调用 `SetCVar*` 一定是缺陷**
   （引擎要求 `CVAR_MOD`），而 `GetCVar*` 读引擎/基础包 cvar 是正常的 —— 这条不对称规则
   非常适合做自动检查。本次使用的脚本见附录 A。
   按 `tools/README.md`「promote a temporary script only after it has a second use」的约定，
   本次没有直接把它放进 `tools/`；等第二次用到再提升。

---

## 附录 A：`SetCVar*` 未注册名字检查脚本

判断规则刻意做成不对称：`SetCVar*` 命中未声明名字 → 失败；`GetCVar*` 未声明只提示（可能是
引擎或 v6b 基础包 cvar）。这正是本次事故的充分条件。

```python
#!/usr/bin/env python3
"""Fail if ACS writes a cvar that is not declared in CVARINFO.*.

SetCVar / SetCVarString only work on a registered cvar that carries CVAR_MOD
(p_acs.cpp SetCVar(): `cvar == NULL || !(flags & CVAR_MOD)` -> return 0).  An
unregistered name therefore fails *silently*, and the matching GetCVarString
returns int 0, which the ACS VM then renders as an arbitrary string-table
entry.  Writing an undeclared name is always a defect; reading an engine or
base-game cvar is normal, so GetCVar* misses are reported as info only.

Run from anywhere:  python3 tools/check_cvarinfo.py
Exit code 1 when an error is reported.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Writes that target a cvar owned by the engine or the v6b base game.  Keep
# this list explicit: an entry here is a claim that the name really is declared
# outside this repository.
EXTERNAL_WRITES = {
    'mm8bdm_bossstate',     # v6b CVARINFO.txt (server noarchive int)
    'mm8bdm_intensestate',  # v6b CVARINFO.txt
}

DECL = re.compile(
    r'^(?:(?:local|server|user|noarchive|archive)\s+)*'
    r'(bool|int|float|string|color)\s+(\w+)')
USE = re.compile(r'\b(Set|Get)(User)?CVar(String)?\s*\(\s*"([A-Za-z_]\w*)"')


def declared():
    out = {}
    for path in sorted((ROOT / 'src').glob('CVARINFO.*')):
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.split('//')[0].strip().rstrip(';').strip()
            m = DECL.match(line)
            if m:
                out[m.group(2)] = (m.group(1), path.name)
    return out


def main():
    decl = declared()
    errors, info = [], []
    for path in sorted((ROOT / 'src/acs_source').rglob('*.acs')):
        text = re.sub(r'//[^\n]*', '', path.read_text(encoding='utf-8', errors='replace'))
        rel = path.relative_to(ROOT)
        for m in USE.finditer(text):
            kind, user, string, name = m.group(1), m.group(2), m.group(3), m.group(4)
            line = text[:m.start()].count('\n') + 1
            where = f'{rel}:{line}'
            call = f'{kind}{user or ""}CVar{string or ""}("{name}")'
            if name not in decl:
                if kind == 'Set' and name not in EXTERNAL_WRITES:
                    errors.append(f'{where}: {call} is not declared in CVARINFO.*')
                elif kind == 'Set':
                    info.append(f'{where}: {call} (external cvar, allow-listed)')
                else:
                    info.append(f'{where}: {call} (engine/base-game cvar?)')
                continue
            got = decl[name][0]
            # bool and int share the ACS int representation; writing 0/1 to a
            # bool cvar with SetCVar is the normal idiom and must not be flagged.
            if got == 'bool':
                continue
            want = 'string' if string else 'int'
            if got != want:
                errors.append(
                    f'{where}: {name} is {got} in {decl[name][1]} but written with {want}')

    for e in errors:
        print('ERROR', e)
    for i in info:
        print('INFO ', i)
    print(f'checked {len(decl)} declared cvars; {len(errors)} error(s), {len(info)} info')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
```

实测（脚本放在 `<root>/tools/` 下运行）：

| 树 | 结果 |
|----|------|
| 修复前（`git worktree add --detach /tmp/x HEAD`） | `143 declared cvars; 36 error(s)`，涉及名字恰为本次修复的 26 个（`uh_be_*` 19、`uh_bex_*` 3、`uh_db_unmorphpre/post` 2、`uh_gf_*` 2）；行数多于名字数是因部分名字有多个写入点 |
| 修复后（当前工作树） | `169 declared cvars; 0 error(s), 14 info`，exit 0 |

两条规则刻意做了取舍：

- **`bool` 不参与类型比对**：`SetCVar("x", 0/1)` 写 `bool` cvar 是正常写法，早期版本把它判成
  类型错误，产生了 11 条假阳性。
- **写入未声明名字一律报错，读取只提示**：`GetCVar` 读引擎/基础包 cvar 是合法的；
  少数写入基础包 cvar 的路径（`mm8bdm_bossstate` / `mm8bdm_intensestate`，来自 v6b 的
  `CVARINFO.txt`）用显式 `EXTERNAL_WRITES` 白名单放行，而不是放宽整个规则。
