# UIX v3bh / Unholy 物品轮盘兼容 — 执行与验证报告

执行对象：`reports/uix-unholy-item-wheel-compatibility-plan.md`
状态：**两项实验已落地；离线轮盘/使用与无 UIX 启动已通过。网络侧完成连接冒烟，未做完整重连+扣数对照。**

---

## 1. 改动清单

| 文件 | 改动 |
|------|------|
| `src/acs_source/compat/mods/uix/uh_uix.acs` | 新增 `uh_uix` 库：检测 UIX 后向 DTADD 注册 Rubber Band / Periwinkle Tank |
| `src/acs_source/compat/mods/rockforce/uh_modcheck.acs` | 由 `compat/rockforce/` **只搬家**；`#library`、脚本名、`uh_modcheck.o`、`LOADACS` 条目未改 |
| `src/LOADACS` | 在 `uh_modcheck` 后增加 `uh_uix` |
| `tools/compile-acs.sh` | RockForce 源路径改为 `compat/mods/rockforce/`；增加 `uh_uix.o` |
| `tools/mm8bdm-v6b-linux.launch.json` | 新增 `mm8bdm-v6b-uix`（Unholy→UIX）与 `mm8bdm-v6b-uix-first`（UIX→Unholy） |
| `tools/mm8bdm-v6b.launch.json` | 同上 |
| `out/build.pk3` | 重新打包（16584 条目，含 `acs/uh_uix.o`） |

未修改任何 UIX 源、`../references/`，也未改 Unholy 物品 actor。

### 1.1 相对计划草稿的实现调整

计划示例使用 `ActorExists`。Zandronum ACC / 引擎源中没有该内建；UIX 自己的 `actorExists` 也是 `SpawnForced` + `Thing_Remove`。本库用 `UH_UIX_ActorExists` 做同样的类存在检测。检测类仍是计划指定的 `UIX_ItemSelected_PU`（仅出现在 UIX v3bh，本 mod 与 v6b 无同名）。

计划示例函数名 `UH_UIX_RegisterExperimentalItems` 超过 ACC 31 字符标识符上限，改为 `UH_UIX_RegisterExperiment`。

`#include` 使用仓库内实际文件名 `dtadd.acs`（Linux ACC 对 include 路径区分大小写）。

两项 `DefineAssistItem` 的返回值会记入 `UH_Log`：成功为 INFO，`-1` 为 WARN。

聚焦启动配置带 `-lastmanstanding` 与 `sv_minplayers 1`，否则 Unholy 会刷出「必须 LMS」提示，且物品 `give` 在未开局时不稳定。默认 `mm8bdm-v6b-smoke` 未改。

---

## 2. 静态与编译

```
ACC=/home/user/appfiles/acc-1.60-linux64/acc bash tools/compile-acs.sh
=> ACS COMPILE OK
```

`uh_uix.o` 4755 bytes。`LOADACS` 含 `uh_uix`。PK3 含 `acs/uh_uix.o` 与原 `acs/uh_modcheck.o`。`validate-build-pk3.sh`：`status=ok`。

RockForce 源字节未改，只改了源路径与 compile 行。

---

## 3. 运行期

### 3.1 无 UIX（`mm8bdm-v6b-smoke`）

- `get_startup_errors`：无 compile/fatal。
- 引擎日志无 `uh_uix: registered` / `DefineAssistItem failed` / unknown script。
- `SpawnForced("UIX_ItemSelected_PU")` 在缺类时返回 0，不 `I_Error`（`p_acs.cpp` `DoSpawn` 对 `FindClass == NULL` 直接返回 0）。

### 3.2 有 UIX，两种包序

| 配置 | 包序 | 注册日志 |
|------|------|----------|
| `mm8bdm-v6b-uix` | Unholy → UIX | `uh_uix: registered Rubber Band at 0, Periwinkle Tank at 1` |
| `mm8bdm-v6b-uix-first` | UIX → Unholy | 同上 |

返回 0/1 是因为 `OPEN CLIENTSIDE` 早于 v6b `core_items` 的非 CLIENTSIDE `OPEN`；core 随后追加 18 行。`UIX_ItemWheelInit` 先 `delay(3)`，快照会看到完整表。两种包序都完成注册，**文档支持序仍是 Unholy 在 UIX 之前**（与 UIX 启动快照更一致的一侧）。

无 `Limit too low, need more item slots`。

### 3.3 离线轮盘与使用（`mm8bdm-v6b-uix`）

LuckyLass、HP 900 时 `give` 成功。

| 检查 | 结果 |
|------|------|
| 轮盘打开 | `pukename uixitem_activate` 后可见五组辐条；中心为 **Rubber Band**，数量 2，图标为 PANBOX 样式 |
| 另一组数量 2 | 与 Periwinkle Tank / Recovery 一致 |
| 选择不扣数 | select 后 Rubber Band 2、Tank 2 |
| Rubber Band 使用 | `use RubberBandItem`：2→1，并生成 `Rubberband` 投射物 |
| Periwinkle Tank 使用 | 单独持有时 `use PeriwinkleTankItem`：2→1，并获得 `PowerPeriwinkleStrength` 与 `PowerPeriwinkleDrain` |

两项 actor 的 `Pickup` 未指向 `UseX`（`Auto*` 才有）；`MaxAmount` 99。UIX 的 Take/Give 重排在本实验中未改变数量。

### 3.4 网络

`node tools/mcp/network-test.mjs --profile mm8bdm-v6b-uix`：**pass**（两名客户端认证并收到 snapshot）。未在该会话里重复「选择不改服务端数量 / 使用只消耗一份 / 重连」的完整清单。

---

## 4. 验收对照

| 标准 | 状态 |
|------|------|
| 无 UIX 时正常启动 | 通过 |
| UIX 在场时两项出现且分组/图标正确 | 通过（Attack 上的 Rubber Band 已截图确认；Tank 在另一辐条且数量 2） |
| 选择保持数量 | 通过 |
| 使用消耗 1 且效果 1 次 | 通过（Rubber Band 投射物；Tank 两项 power） |
| 离线与网络行为一致 | 部分：网络仅完成连接冒烟 |
| 无 DTADD 容量警告 | 通过 |
| 未改 UIX / references | 通过 |

---

## 5. 后续

扩展 allowlist 前继续手审 Take/Give 安全性，并检查 `DefineAssistItem` 返回值。武器栏是独立阶段。网络完整扣数/重连仍建议在真实 listen/dedicated 上手测一次。
