# UHDT 身份表 CRUD 契约

本次实现沿用 `UHDT → UHADDR → UHADD`，不引入通用 SQL 或替换 MM8BDM `DefineWeapon`。`Define*` 的返回值和已有重复定义策略保留；新写操作统一返回 `UHDB_OK`、`UHDB_ERR_NOTFOUND`、`UHDB_ERR_CONFLICT`、`UHDB_ERR_REFERENCED`、`UHDB_ERR_CAPACITY`、`UHDB_ERR_BADARG`。接口声明在 `src/acs_source/_includes/mod_api/uhadd.acs`。

## 行状态与 ID

- 活跃：`IsDefined` 为真，`IsEnabled` 为真，可进入随机选择。
- 禁用：`IsDefined` 为真，`IsEnabled` 为假，保留 Get/Find 与现有引用，不进入随机选择。强制指定的 Boss 仍可使用禁用定义。
- 删除：`IsDefined`、普通 Find/Get 均视为不存在；原键、ID 和槽位留作墓碑，本地图内不复用。身份表的旧 `Define*` 不隐式恢复墓碑。
- `GetDefined*Count` 与 `GetEnabled*Count` 分别统计有效行和启用行；自定义 ID 的分配上界不因删除降低。

## 表级操作

| 表 | 身份键 | 非身份更新 | 删除前的引用检查 |
| --- | --- | --- | --- |
| Boss | actor，固定正 ID / 自动负 ID | 展示字段、稀有度、HP | 当前玩家 Boss、活动回合、Combo、EX 子项、已定义音乐、unmorph 行 |
| Survivor | actor，固定正 ID / 自动负 ID | 名称、mugshot | 当前玩家 actor |
| Demoneye | actor，固定正 ID / 自动负 ID | 名称、前缀、mugshot | 当前玩家 eye ID / actor、变形池行 |
| Item | actor，固定正 ID / 自动负 ID | 名称、icon、mugshot、音效 | 掉落行、coin spend、待发物品、玩家现有库存 |
| LMS Event | stem，固定或自动正 ID | 消息、图标、flags、权重 | 掉落行 |
| Bonus Event | stem，固定或自动正 ID | 除 stem 外的注册字段 | EX 关系、当前活动事件 |
| Boss/Event Music | `(bossId 或 GLOBAL, kind, phase, lump)` | Add 同键更新元数据 | 按键删除；同键 Add 恢复原行 |

Boss 稀有度变更、禁用和删除会同步压缩或扩充对应随机池，保持池数量与可抽取 ID 一致。音乐和事件的加权抽取在求和与落点两轮使用相同的启用过滤。Item 箱、Eden D6 等抽取路径跳过禁用行；库存结算仍处理已禁用的现有物品。

## 调用与时序

推荐 addon 用 actor/stem 包装（例如 `SetBossEnabledByActor`、`RemoveLMSEventByStem`），因为自动分配的数字 ID 取决于注册顺序。注册期的服务端 `OPEN` 与客户端 `OPEN CLIENTSIDE` 分别执行相同的稳定键操作；这不是网络广播。跨进程传 ACS `str` 整数或自定义行号没有定义的含义。

第一版更新限定在注册期或下一回合的准备阶段。运行中更新展示字符串若要即时同步给所有客户端和晚加入者，仍需要独立的可靠消息与重放协议。删除是逻辑删除，不会卸载 DECORATE actor、撤销已给予的库存或清除物理世界中已有的对象。Presentation 行按 actor 独立存储，删除身份行不会自动删除该展示行。

示例：

```acs
int id = UH_FindBossByActor("MyBoss");
if (id != UHBOSS_FAIL) {
    int status = SetBossEnabledByActor("MyBoss", 0);
    if (status == UHDB_OK && !IsBossEnabled(id)) {
        // 已保留定义，并从随机池移出。
    }
    SetBossEnabledByActor("MyBoss", 1);
}
```

若 `RemoveBossByActor` 返回 `UHDB_ERR_REFERENCED`，先移除该 Boss 的音乐和其他附属关系，再在未被当前回合引用时重试；原版 Combo 成员属于固定引用，不应删除。
