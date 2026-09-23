# UHDT 运行时数据库增删查改实施计划

## 目标与边界

完善 Unholy 自有的 `UHDT → UHADDR → UHADD` 数据库链，让已有定义表能明确地新增、查询、修改、禁用和删除记录。现有 `Define*`、`Add*`、`Find*`、`Get*` 的签名和成功路径保持兼容；新增操作采用按表定义的业务接口。MM8BDM v6b 的 `DefineWeapon` / `CORE8BDT` 属于原版数据库，本计划不替换它们。

这里的“删除”指在当前地图的 UHDT 实例中使一行失效；不是卸载 DECORATE actor、撤销已授予的 inventory，也不是持久化到下次启动。所有新写操作都需要明确服务器和客户端各自的生效范围。

## 现状依据

- `src/acs_source/_imports/uhdt.acs` 用固定容量数组存储 Boss、Survivor、Demoneye、Item、音乐、LMS/Bonus Event 等。Boss 的原版 ID 是非负固定槽，自定义 ID 为 `-1 - customIndex`；自定义表目前只凭 `customCount` 判断有效。`FindBossByActor` 和多个消费者遍历这个上界。
- `src/acs_source/corescripts/api_handlers/uhaddr.acs` 的 `UH_DefineBossCore` 拒绝重复 actor、已占用 ID 和超出容量的新增；`src/acs_source/_includes/mod_api/uhadd.acs` 经 cvar mailbox 和命名脚本暴露 addon 接口。
- `AddBossMusicCore` / `AddEventMusicCore` 已按复合键更新已有行，但音乐查询和随机抽取目前只检查 `row < uh_bossmusiccount`，没有行状态。`uh_music.acs` 消费抽出的行号及元数据。
- `DefineLMSEventCore` 允许同一 ID 重写，`FindLMSEventByStem` 检查 stem 冲突。可见现有表的“重复定义”语义并不统一，迁移时不能把它们一律改成 upsert。
- `src/acs_source/unholy/uh_boss_selection_helpers.acs` 的部分自定义 Boss 历史读写直接判断 `idx < uh_bosscustomcount`；若加入墓碑位，必须改为调用有效性判断。
- 内建定义和 addon 已使用普通 `OPEN` 与 `OPEN CLIENTSIDE` 在服务端和客户端分别注册。跨网络传递 ACS 字符串索引不构成可靠的字符串同步协议；运行中变更若要同步，必须单独设计字符串传输和晚加入者重建。

## 先定统一契约

1. **标识不漂移。** Boss 等已公开的整数 ID、音乐已返回的行号，在当前地图生命周期内不移动、不复用。计数器表示分配上界，不表示有效记录数。需要展示数量时分别提供有效记录数与启用记录数，避免把两者混为一谈。
2. **区分禁用和删除。** `Disable` 保留可查询的定义，只排除随机池/选择；`Remove` 使普通 `Is/Find/Get` 视其为不存在。内部保留墓碑与原键，用于诊断和同键恢复。删除后再次 `Add` 同一音乐键可原位恢复；主身份表的恢复必须由显式 `Restore` 或另行规定的接口完成，不能悄悄把旧 ID 指给新 actor。
3. **不改旧入口的重复策略。** Boss/Survivor/Demoneye 的 `Define` 继续拒绝重复；音乐 `Add` 继续按键更新；LMS/Bonus Event 的既有按 ID 重写行为保留。新增 `Update*`、`Disable*`、`Remove*` 表示新语义。
4. **写入先校验后提交。** 检查 ID、主键冲突、容量、字段约束及引用关系；失败时不改变主表、随机池或其他派生数据。返回值必须区分成功、未找到、冲突、被引用、容量不足等原因。现有返回 `-9999` 的接口继续维持原契约，新接口可用明确的状态常量。
5. **区分身份字段与普通字段。** Boss actor、事件 stem、音乐复合键属于身份。第一批更新接口只允许修改非身份字段；改身份需要独立操作，且先检查唯一性和所有引用。
6. **每张表声明生命周期。** 哪些字段仅在注册期可变，哪些可在回合间修改，哪些允许运行中改变，要写在该表 API 上。运行中更新不得让已开始的回合从同一 ID 读到前后不一致的规则。

## 第一阶段：盘点与契约落地

- 对 UHDT 每组表记录：主键、容量、ID 分配、重复定义行为、有效性判断、所有直接数组读写、派生索引、跨表引用、服务端/客户端消费者。优先盘点 Boss、Survivor、Demoneye、Item、音乐、LMS/Bonus Event；附属行（掉落、presentation、copy weapon 等）单列。
- 将调用者按“只读 getter”“直接读数组”“直接遍历计数”“缓存 ID/行号”分类。尤其检查 Boss 随机池、EX 父子、当前回合 `bossdataarr`、Boss 选取历史、音乐播放和 UI 展示。
- 为每张表写出允许的操作矩阵。不是每张表都要支持任意字段更新或立即物理删除；附属行可先支持禁用/移除，身份主表优先保证稳定 ID。
- 明确查询的两层含义：`IsDefined`/`Find`/`Get` 针对有效记录；`IsEnabled`/候选选择针对可参与玩法的记录。内部诊断可单独查询墓碑，不暴露为普通有效记录。

## 第二阶段：用音乐表实现完整样板

修改 `uhdt.acs` 的 Boss/Event Music 共用表：增加行状态（有效、启用），保留现有行号与 `uh_bossmusiccount` 作为分配上界。

建议新增内部操作：

```acs
IsMusicRowDefined(row)
IsMusicRowEnabled(row)
SetMusicRowEnabled(row, enabled)
RemoveMusicRow(row)
GetActiveMusicRowCount()
```

对 addon 的操作以现有复合键为主，提供 Boss 音乐的 actor 入口以及 Event 音乐的 `(kind, phase, lump)` 入口；不要让 addon 依赖随注册顺序变化的行号。`AddBossMusic` / `AddEventMusic` 继续更新同键有效行；同键墓碑可恢复原行并完整重写字段，内部须有可查墓碑的专用查找，普通 `Find` 仍跳过墓碑。同键更新已禁用行时保持禁用状态，只有显式 `Enable` 能重新参与抽取。禁用保留查询与元数据，删除使普通查询失败。

需要同步修改 `FindBossMusicRow`、所有 `Get*ByRow`、`PickBossMusicRow` 和 `PickEventMusicRow`：查找和 getter 跳过已删除行；随机抽取还跳过已禁用行。加权抽取的求和与落点两轮使用完全相同的过滤条件。确认正在播放的曲目已拥有需要的快照，或将删除限制到回合间，以免播放流程在选中行后又读到失效元数据。

在 `uhaddr.acs`、`uhadd.acs` 和 `src/CVARINFO.ipc` 添加对应的 handler、包装和 mailbox。所有新增 mailbox 使用现有 `local noarchive` 约定，逐项核对名称、字符串/整数类型和写入失败时的返回路径。

## 第三阶段：身份主表的增删查改

按依赖复杂度逐表推进，建议 Survivor/Demoneye → Item → LMS/Bonus Event → Boss。每张表完成后再推进下一张；不在一个改动中同时改所有存储布局。

- **新增：** 沿用 `Define*` 现有 ID 分配和唯一性规则；容量满时失败。自定义 ID 只递增分配上界，默认不回收已删除槽。
- **查询：** 所有 `Is/Find/Get` 先通过有效性判断。遍历 `customCount` 或固定容量的调用者检查有效位；保留原有无效 ID 的返回约定。确有需要时提供按稳定 actor/stem 查询与枚举有效 ID 的接口。
- **更新：** 从具体业务字段开始，如展示名称、说明、权重。Boss 稀有度变更必须同步随机池；EX 父子关系、Item 掉落和事件附属行变更必须维护引用完整性。将主表与派生索引的更新封装在同一内部入口，不允许 addon 直接写数组。
- **禁用：** 保留身份、历史和引用，随机选择/候选池跳过该行。明确管理员强制选择和已启动回合是否仍可使用该定义；建议禁用只影响未来选择，现行回合使用已提交的身份快照。
- **删除：** 先判断是否被活动回合、玩家身份、EX 关系、音乐、掉落、附属行或其他注册记录引用。第一版遇到引用返回“被引用”，由调用者先处理依赖；不隐式级联删除。无引用时标记墓碑、移出候选池，但保持 ID 和数组槽不变。已删除 ID 在本地图内不重分配给另一身份。

Boss 的随机池目前是按稀有度保存 ID 的列表。实施时集中提供“加入、移出、改稀有度、选取”操作；禁止只修改 `uh_bossvanillaint` / `uh_bosscustomint` 而留下旧池条目。Boss 历史读写等消费者改用 `IsBossDefined`，避免墓碑行仍被当作有效 Boss。

## 网络与注册时序

- 注册期双端执行的定义继续使用现有 `OPEN` / `OPEN CLIENTSIDE` 路径。主键必须在两端稳定；自动负 ID 和 presentation 行号不能作为跨进程身份传输。
- 第一批公开的变更操作仅承诺**注册期或下一回合生效**。服务端逻辑变更由服务端执行；影响 HUD/音乐元数据的变更还要在客户端执行相同的、按稳定键定位的操作。监听服务器双入口执行时必须幂等，防止重复写入。
- 若要支持管理员在运行中对所有客户端即时修改字符串字段，另设后续阶段：定义按稳定键的变更事件、使用引擎支持的字符串传输路径、为晚加入客户端重放当前状态，并处理操作顺序与重复投递。没有这套协议前，不把本地 cvar mailbox 或 ACS `str` 整数当作网络同步。

## 文件与交付顺序

1. 在本计划旁或 API 注释中完成表级操作矩阵、错误码和生命周期契约；列出直接访问数组的调用者。
2. 修改 `src/acs_source/_imports/uhdt.acs` 的音乐行状态、查询、加权抽取和增改删逻辑。
3. 修改 `src/acs_source/corescripts/api_handlers/uhaddr.acs`、`src/acs_source/_includes/mod_api/uhadd.acs`、`src/CVARINFO.ipc`，公开音乐表操作并更新 addon 用法。
4. 逐表迁移身份主表，每次同时修改该表的直接数组消费者与派生索引维护；保留旧公开函数签名。
5. 最后更新 `examples/` 中涉及注册的 addon 示例及 API 文档，展示同键更新、禁用、删除、查询结果和双端注册。

## 每阶段验收条件

- 新增、同键更新、重复拒绝、容量不足、越界查询都符合该表的既有或已声明语义；失败写入不留下半条记录。
- 禁用行仍可按身份查询，但不参与随机选择；删除行在普通 `Is/Find/Get` 中不可见，且不会被任意遍历重新选中。
- 删除或禁用不会改变其他 ID/行号；墓碑 ID 不指向新身份。更新稀有度、权重或附属关系后，主表与候选池结果一致。
- 普通 `OPEN` 与 `OPEN CLIENTSIDE` 重复注册不产生多行；专用客户端、监听服务器和晚加入客户端按该阶段承诺读取到一致的展示数据。
- 完成实现后按项目现有 ACS 编译、静态检查和最小 v6b 运行流程验证；只有涉及运行中网络变更的阶段才增加相应的双端场景。计划本身不需要启动游戏。
