# Qwant 固定槽位、实时刷新武器轮实施计划

## 工程量评估

本次属于中等偏大的兼容功能，不是给固定武器注册表增加一行即可完成。按用户要求，本轮只制定计划，不修改游戏代码。

工作集中在四处：稳定槽位的客户端同步、Qwant 显示元数据解析、轮盘内容实时重建、服务端槽位选择校验。可以复用现有 UIX 轮盘绘制和 UH 启停入口，不需要实现新的几何布局，也不需要动态增减分区。预计涉及约 4～6 个源码文件，以及一轮专门的联机验证；同步和刷新时序是主要风险。

## 已确认的源码事实

- `actors/classes/survivors/Qwant.dec`：普通 Qwant 持有 `Qwant_W`，通过 `Qwant_WeaponStart_P` 初始化招式。
- `classes/shared/copy_weapons/copy_weapon_runtime.acs`：`uh_QwantStartMoves` 随机选择四个不重复招式，写入 `user_PKMN_MoveMem[0..3]`。因此固定的是数量与槽位，不是每局的具体招式。
- 同文件的 `uh_QwantMoveRelearn`：确定当前招式所属槽位，替换该槽位的索引，给予新武器并移除旧武器；没有主动增减槽位。
- `classes/shared/copy_weapons/weapon_roulette.acs` 已按四个 MoveMem 槽位解析招式，可以参考其服务端解析模式。
- `compat/mods/uix/uh_uixfw_run.acs` 目前只收集固定 actor 快照，打开后只刷新弹药，任意快照武器消失会取消轮盘。Qwant 不能直接沿用这条规则。
- UIX `uixweap.acs` 的 `updateSlotData` 检测持有变化并重建当前武器轮；`WHEELDT.startWheel` 同步调用激活脚本。这是复用刷新方式的参考，不是复用原版武器分组。
- Zandronum `src/p_acs.cpp` 的 `SetUserVariable`、`ACSF_SetUserArray` 路径只修改本地 actor 存储，没有在该调用路径发送同步命令。不能直接假定客户端轮盘可以可靠读取服务端的 MoveMem，实施需建立明确的同步来源。

以上路径省略了项目内的 `src/acs_source/` 前缀；UIX 和引擎参考源码均位于只读的 `../references/`。

## 用户可见行为

- 仅支持普通 `Qwant`，不把继承自它的 `QwantShiny` 自动纳入；后者有独立招式机制。
- 固定五个 group：`Qwant_W`、招式槽位 0、1、2、3。一个当前武器独占一个 group，不按宝可梦属性合并。
- 顺序绑定 MoveMem 槽位，不按属性、注册顺序或当前持有列表重新排序。
- M2 替换时保留五个扇区以及当前指向的位置，原槽位内容更新为新招式；不关闭并重新打开轮盘。
- 图标、名称、弹药类型、容量、颜色一起更新。即使两个招式使用相同属性图标，也仍独占扇区。
- 初始化未就绪时不开轮盘，不回退到原版分类轮。死亡、观战、换 class 则取消。
- 网络不同步期间不允许把旧槽位内容当成新武器来选；不承诺客户端能早于服务端状态到达显示新招式。

## 实施步骤

### 1. 建立权威槽位快照

在 Qwant 初始化与重学招式完成之后，发布四个槽位的招式索引与一次更新的版本号。发布点必须在 Give/Take 和 MoveMem 更新全部完成之后，不能在替换中途通知客户端。

同步桥放入现有 UIX 兼容目录。使用项目已验证的服务端到客户端 ACS 通信模式；实施前核对引擎和已有调用，确认定向、activator、参数与 CLIENTSIDE 语义。数据接收只能由服务端触发，不提供可被客户端任意提交的槽位更新 NET 入口。

客户端用完整快照提交：四个索引同一批次生效，并保留最后一个完整版本。四个索引可通过两个调用传递，但必须带批次标识并等全部到齐，不能显示混合版本。若使用压缩编码，必须写明索引上限并验证，不靠隐含位宽。

轮盘打开时补拉当前快照，以覆盖初始化、重生、迟加入和重学时轮盘未打开的情况。请求只读且只返回请求者自己的 Qwant 数据。重生/换 class 清空旧快照；响应需校验当前玩家生命周期，不能让旧生命的延迟响应覆盖新生命。

第一步先验证初始化和连续 M2 后，客户端槽位与服务端 MoveMem 完全一致，再进入显示工作。

### 2. 增加 Qwant 槽位解析与显示适配

在 `compat/mods/uix/` 新增 Qwant 实现片段，由 `uh_uixfw.acs` 在合适的依赖顺序 include，不新增 LOADACS 库。

使用 UHDT 的 `GetCopyWepActorByKindIndex(UHCOPY_QWANT, index)` 解析 actor，并验证索引、注册 kind、四招式不重复及实际持有情况；等待 UHDT 注册完成后才能解析。避免重新维护一份全部招式 actor 表。

显示数据优先复用已有定义：

- 注册于 8BDT 的 actor，使用 `findWeaponByActor` 及 `getWeaponTag/Icon/AmmoType/Ammo2Type` 等访问器。
- 核对未注册招式是否需要借助临时 actor 读取 Tag、Inventory.Icon 和武器弹药；不得把缺失的表索引当成有效索引。
- Qwant 的主弹药条需按现有 HUD 规则解析 `<actor>_QwantBar`，参考 `hud/font_helpers.acs` 的 `ResolveQwantFillAmmo` 和 `hud/bar_types.acs` 的属性色表。不能把 `_QwantBar` 的属性 ID 当成普通 Cyan/Blue 色号。
- 保留自定义填充弹药与容量回退规则；`MoveRelearnAmmo` 条使用现有 Qwant HUD 配色。
- 临时元数据 actor 及时移除；静态显示元数据按 actor 缓存，不每 tic 反复 Spawn。

只有遇到无法复用的元数据才增加窄范围访问器，不趁此重构整个 HUD/DTADD 系统。

### 3. 接入固定布局的实时刷新

给 `UHFW_OpenUnified` 增加精确 Qwant 路由。固定 class 路由和 MegaMan 原版 fallback 保持现状。

将 Qwant 槽位映射接入五项显示数组，但不调用原来的固定 actor 丢失取消检查。每次轮盘 tick：

1. 检查玩家有效且仍为普通 Qwant。
2. 尝试提交已完整接收、且库存已经匹配的新槽位快照。
3. 若版本/actor 发生变化，更新五项显示数据并重建轮盘内容；只调用内容清空与添加，不重新调用 `newWheel/startWheel`。
4. 若内容未变化，仅刷新弹药数值；颜色和条结构变化不得只走原来的数值 patch。

重建时保持 item 总数、group 总数和 item/group 顺序为 5；UIX 激活脚本有局部 selected 状态，应按其源码保持选择位置，而不是重新按当前装备武器定位。

库存同步与快照消息可能先后到达：待提交快照不完整或新 actor 尚未持有时，短暂保留旧显示，禁用不匹配槽位的选择；设置有限等待，超时取消并记录日志，不无限保留不可用的轮盘。正常 M2 替换不因旧 actor 消失立即取消。

### 4. 按槽位执行选择

Qwant 使用独立的服务端选择路径，不将所有可能招式硬塞入 `AddFixedWeaponWheelWeapon`，也不绕过原有固定 class 的 actor 白名单。

客户端提交槽位编号及其显示的招式索引。服务端重新读取自己的 MoveMem，验证精确 class、存活、槽位范围、显示索引仍匹配以及当前持有，再 SetWeapon。槽位 0 单独解析 `Qwant_W`，其余槽位对应 MoveMem 0..3。

当松键与 M2 替换交错、请求已过时时拒绝切换，不把过时选择静默解释为新招式。轮盘关闭回调运行前再尝试刷新已收到的完整快照；不要依赖已被 UIX 清理的显示数组名字来确定 actor。

## 最小实验与验证顺序

1. **同步实验**：先不画轮盘，验证四槽初始化、一次替换、连续替换、重生后快照；特别验证真实服务端与客户端分离运行。
2. **五扇区实验**：显示 `Qwant_W` 与四招式，先验证静态切换；至少覆盖同属性的两个独立招式。
3. **轮盘内 M2**：只替换一个槽位，确认位置和指向不变，actor/名称/颜色/两条弹药信息全部刷新。
4. **时序验证**：M2 后立即松键、快速反复开关、连按 M2、延迟网络、初始化尚未就绪、死亡/观战/换 class；不能误选旧武器或误关 item wheel。
5. **回归**：现有五个固定 class、MegaMan 原版轮、QwantShiny 不受影响；UIX 未加载时不启动轮盘或产生缺失脚本调用。
6. **编译**：使用现有 `tools/compile-acs.sh` 全量编译到临时目录，不新建构建工具。游戏内与联机测试在实施后的验证阶段另行开展。

## 范围与完成条件

不实施 NegaMan、不按属性分组、不增加布局开关、不引入可变分区、不修改 Qwant 战斗与随机招式规则。

完成条件：普通 Qwant 稳定显示五个一武器一 group 的扇区，M2 在同一扇区实时替换显示，服务端只接受当前有效槽位选择，实际联机同步通过，并且原有固定轮和 MegaMan fallback 回归通过。
