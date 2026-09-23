# UHDT CRUD 迁移盘点

本文件记录 `uhdt-crud-implementation-plan.md` 第一阶段的代码盘点与迁移结果。计数器均为分配上界；消费者通过有效性和启用性入口判断记录。最终操作契约见 `uhdt-identity-crud-contract.md`。

## 已完成的样板

Boss/Event 音乐共用表已在 `uhdt.acs` 实现复合键查找、同键更新、启用/禁用、逻辑删除、按键恢复和有效/启用行计数。行状态打包在 `uh_bossmusicoptional`；契约见 `uhdt-music-row-contract.md`。`uh_music.acs` 消费 `Pick*MusicRow` 返回的行号和元数据，因此后续操作继续保持行号稳定。

## 身份主表

- **Survivor：** 非负固定 ID 与 `-1-customIndex`；actor 大小写不敏感且唯一。原版有效位在 `uh_survvanilladefined`，自定义行目前只靠 `uh_survcustomcount`。新增墓碑状态后要改 `IsSurvivorDefined`、`SurvResolveSlot`、`FindSurvivorByActor` 和所有按 count 遍历的调用。展示字段是 name/mugshot；玩家展示还由 actor 键控的 presentation 表覆盖。删除不能令正在使用此 class 的玩家突然失去身份。
- **Demoneye：** 与 Survivor 同样的正/负 ID 分配。某些原版条目允许空 actor；自定义行必须有 actor。flags 单独存放，不能未经校验就把生命周期状态挤进公开 flags。`uh_playereyeid` 可持有 ID；眼睛变形池按 eye ID 关联。删除需要先处理这些引用。
- **Item：** 正/负 ID。`uh_itemdrop*` 以 box ID、item ID 和给予 actor 形成附属行，另有箱子音效、DTADD group、Eden D6 路径。`classes/survivors/eden/eden_runtime.acs` 直接遍历 `uh_itemvanilladefined`、`uh_itemcustomcount` 并读取 actor；逻辑删除时必须同步修正。被掉落表或活跃物品逻辑引用的条目不能静默删除。
- **LMS Event：** 固定非负 ID，`-1` 从 12 开始单调分配；stem 大小写不敏感。现有 `DefineLMSEventCore` 对同一 ID 重写且检查 stem 冲突。`uh_lmsdrop*` 以 event ID 关联。权重 0 已表示仅强制，不能拿它当删除状态；随机抽取、强制选择及附属 drop 读取都要认识新状态。
- **Bonus Event：** 固定非负 ID，`-1` 从 addon ID 段单调分配；同 `(id, stem)` 重写，stem 与 ID 不一致时报冲突。`uh_beex*` 保存基础事件与 EX 事件的 ID 关联；回合当前事件、回调和重建路径可持有 ID。删基础或 EX 事件须先检查关系及活动回合。
- **Boss：** 正/负 ID，actor 唯一。稀有度池 `uh_bosspoolids` 是独立派生索引；EX 父子、音乐、unmorph 清理、Boss Combo、玩家当前 boss ID、历史计数和活动回合均可引用 Boss ID。`unholy/uh_boss_selection_helpers.acs` 有直接 `idx < uh_bosscustomcount` 判断，必须改为有效性入口。修改稀有度要在同一次写入中维护池。

## 附属表及后续决策

Boss unmorph 清理、Survivor weapon/cleanup、Item drop/coin spend、copy weapon、LMS drop、Eye morph pool、Bonus EX、team presentation 都有自己的键和调用者。第一轮不应套用身份主表的删除逻辑；先完成身份主表并逐个把它们列为引用检查，再给有实际修改需求的附属表增加独立操作。

`uhdt.acs` 的 map 变量已接近 ACC 的 128 个上限。新增状态优先放进现有二维记录数组的额外字段，或合并现有变量后再分配；不能按每张表新增平行状态数组。所有状态位都要有独立于公开业务 flags 的明确定义。

## 迁移完成时要复查的直接访问

- `corescripts/api_handlers/uhaddr.acs` 的各 `Define*Core` 仍直接查看固定槽与自定义 count，用来拒绝墓碑 ID 复用；actor 唯一性通过包含墓碑的内部查找判断。
- `classes/survivors/eden/eden_runtime.acs`、`items/penny_and_d6.acs`、`items/death_drops.acs` 已改用 `IsItemDefined` / `GetItemActor`，不再把墓碑当作库存行。
- `unholy/uh_boss_selection_helpers.acs` 的历史索引已加 `IsBossDefined`，Combo 候选改用 `IsBossEnabled`；Boss 稀有度池在同一次写入中压缩或追加。
- `items/hat_runtime.acs` 和 `items/box_runtime.acs` 的掉落/coin spend 行作为 Item 删除引用阻断；箱子抽取通过 UHDT 启用状态过滤。
- 网络两端不能传自定义行号或 ACS 字符串池索引作为身份。注册期双端按稳定 actor/stem 调用同一操作；运行中即时同步需单独的消息协议和晚加入者重建。
