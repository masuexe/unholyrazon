# UIX 固定武器数量等分轮实施方案

## 目标与首期范围

为武器清单固定的 Unholy class 增加独立武器轮：一个武器对应一个分区，分区数量等于该 class 定义的武器数量。

首期不支持运行中改变武器集合的 class，也不替换 UIX 原版按 DTADD slot 分类的武器轮。新轮使用独立按键和独立脚本，方便与原版行为并行测试。

启用规则：

| 已定义武器数 | 行为 |
|---:|---|
| 0–2 | 不创建、不打开轮盘 |
| 3–12 | 创建同数量的等分轮盘 |
| 13+ | 首期拒绝注册并记录警告 |

上限 12 来自 UIX v3bh `WHEELDT.acs` 的 `WHEEL_GROUPS_LIMIT 12`。首期不覆盖这一通用 UIX 数据库，也不为了更多分区修改 UIX 的选择和绘制算法。

## 采用的 UIX 机制

复用 UIX v3bh 已加载的通用轮盘库：

- `newWheel(name, groupCount, selection)`
- `addWheelItem(name, group)`
- `addWheelElement(...)`
- `startWheel(loopScript, selectScript)`
- `stopWheel()`
- `emptyWheel()` / `destroyWheel()` 的既有生命周期

UIX 按 `1.0 / groupCount` 均分圆周。构建时令第 `i` 把武器使用 group `i`，并且每组只添加一项，即可得到每把武器一个等角分区；不修改 `UIXWHEEL.acs` 的角度、鼠标或绘制逻辑。

## 模块布局

在现有 `acs_source/compat/mods/uix/` 下新增固定轮实现，作为独立 ACS library，并加入 `LOADACS`。建议职责分为：

1. 固定轮定义数据库：class actor、武器 actor、显示顺序和 UI 元数据。
2. UIX 适配运行时：探测 UIX、打开/关闭轮盘、添加显示元素、网络切换武器。
3. KEYCONF：新增独立的按下/松开 alias。

不修改只读的 `../references/for_8bdm-v6b/8bdm-uix-v3bh/`，也不直接覆盖 `UIXWEAP.o`。项目现有的 `UIXITEMS.o` 覆盖与本轮无关。

## 固定轮定义模型

定义以 class 为单位，而不是以 DTADD slot 为单位。概念 API 为：

```c
DefineFixedWeaponWheel(classActor);
AddFixedWeaponWheelWeapon(classActor, weaponActor, tag, icon, ammo1, ammo2);
```

实际命名可在实现时与现有 Unholy 注册 API 统一。每个 class 的添加顺序就是顺时针显示顺序，因此不再需要额外 `order` 字段。

首期数据字段：

- `classActor`：允许使用该固定轮的实际玩家 actor。
- `weaponActor`：最终传给 `SetWeapon` 的 actor 名。
- `tag`：中央显示名称或 LANGUAGE key。
- `icon`：轮盘图标。
- `ammo1`、`ammo2`：可为空；用于弹药条。

固定清单应该只定义该 class 正常情况下始终拥有的武器。临时武器、事件武器和以后会增减的武器不纳入首期。

同一 class 的武器数必须在 3–12 之间；重复 class、重复 weapon、空 actor/icon、超出上限均视为定义失败并记录日志。

## 为什么不直接遍历 DTADD

DTADD 是全局武器表，包含 MM8BDM、UIX 兼容项及其他模组注册项。只扫描 `MAX_WEAPONS_GLOBAL` 无法可靠证明某项属于当前固定 class，也无法表达固定的顺时针顺序。

首期直接使用 class 专属清单能保证：

- 不混入其他模组临时给予的武器。
- 不受 DTADD 注册顺序变化影响。
- 武器数与轮盘分区数严格一致。
- 以后可以逐个 class 接入，而不要求所有 class 同时改造。

UI 元数据可以先从当前 UIX 武器注册资料迁入固定轮定义。后续若多个系统都需要同一份 tag/icon/ammo，再把它们统一进更高层的武器数据库；首期不同时重构 `DefineCopyWep`。

## class 识别

打开轮盘时读取 `GetActorClass(0)`，在固定轮定义表中查找完全匹配的 `classActor`。

不要使用 `PlayerClass()` 数字作为持久身份：KEYCONF 的 class 顺序可能随追加 class 变化。Actor 名更清晰，也更适合未来为变体 class 注册单独清单。

若基础形态和 Shiny/变身形态拥有同一固定清单，首期显式各注册一行映射到同一个 wheel definition；不要靠删后缀等字符串猜测。

## 打开流程

新增独立 alias，例如概念上的：

```text
+uhfixedweapwheel → 客户端打开脚本
-uhfixedweapwheel → 客户端关闭脚本
```

打开脚本按以下顺序执行：

1. 验证 `ConsolePlayerNumber() == PlayerNumber()`。
2. 用 UIX actor 探测确认 UIX v3bh 已加载。
3. 若 `wheelName != -1`，直接退出，避免踩到道具轮或 UIX 原武器轮。
4. 用 `GetActorClass(0)` 查找固定轮定义。
5. 读取定义中的固定武器数；少于 3 时退出。
6. 验证这些 weapon actor 当前确实存在于玩家 inventory。固定轮首期要求全部存在；缺失任意一把时退出并仅在 debug 日志记录异常，不用较少数量临时重建。
7. 用 `CheckWeapon(actor)` 找到当前装备武器，换算成 wheel item index；找不到时默认 0。
8. 调用 `newWheel("uhfixedweaponwheel", weaponCount, currentIndex)`。
9. 按定义顺序逐项调用 `addWheelItem(weaponActor, i)`；第 `i` 项进入第 `i` 组。
10. 添加未选中、选中和中央显示元素。
11. 调用 `startWheel(loopScript, selectScript)`。

这里的关键约束是 `group == weapon ordinal` 且每组只有一项。

## 关闭与选择

关闭 alias 只调用 `stopWheel()`，并由 UIX 通用轮盘在结束时调用选择脚本。

选择脚本：

1. 从 `getWheelItemName(idx)` 取得注册时保存的 weapon actor。
2. 可继续给予 UIX 使用的 `UIX_WeaponSelected_PU`，保持声音/反馈一致。
3. 用 `NamedSendNetworkString` 把 actor 名发送到 `NET` 服务端脚本。
4. 服务端再次验证玩家持有该武器，并执行 `SetWeapon(actor)`。

不能只在 CLIENTSIDE 调用 `SetWeapon`；武器切换必须沿用 UIX 的客户端选择、服务端执行结构。

服务端验证不应信任客户端任意字符串。它需要确认 actor 属于调用者当前 class 的固定清单，并且调用者实际持有它。

## 显示内容

最小实验只绘制：

- 外圈未选中图标。
- 外圈选中放大图标。
- 中央图标。
- 中央武器名称。

选择和网络切换可靠后，再从 UIX `WeaponWheel_AddItem()` 移植弹药条元素。弹药条只更新数值，不重建分区：

- `CheckInventory(ammoActor)` 获取当前量。
- `GetAmmoCapacity(ammoActor)` 获取上限。
- settings script 每 tick 更新对应 element 的 bar amount/max。

固定武器集合在轮盘打开期间保持不变。

## 0–2 把武器的处理

首期严格按当前范围处理：没有 wheel。

- 0 或 1 把：打开和关闭脚本均无动作。
- 2 把：同样无动作，不擅自实现快速切换。

可以记录本次按下是否实际打开了轮盘，使松开脚本只在本轮拥有 `wheelName` 时调用 `stopWheel()`。不得关闭玩家正在使用的 UIX 道具轮或原武器轮。

两武器快速切换可作为独立后续功能，不与第一版等分轮绑定。

## 与未来可变武器轮的边界

首期数据库和绘制层分离：

- 数据提供层回答“当前轮有哪些武器、顺序是什么”。
- UIX 绘制层只接收线性武器清单。

首期数据提供层返回 class 的固定定义。未来支持可变数量 class 时，可以新增一个 inventory/DTADD 收集器，仍把结果交给同一个绘制层，而不重写轮盘元素、选择或网络脚本。

未来动态版本建议在每次打开时生成快照，但在轮盘打开期间不改变武器数。它不属于本次实现范围。

## 分阶段实施

### 阶段 1：最小实验

- 选择一个始终拥有 3–6 把武器的 class。
- 注册固定 class 和武器清单。
- 加入独立 KEYCONF alias。
- 只绘制图标和名称。
- 验证每把武器占一个等角分区并可切换。

### 阶段 2：完整固定轮

- 增加弹药条和当前武器默认选中。
- 增加 class/weapon/inventory 服务端校验。
- 加入第二个不同武器数量的固定 class，证明分区数不是硬编码。
- 加入失败日志，但避免每 tick 刷屏。

### 阶段 3：使用体验

- 决定是否保留独立按键。
- 若要接管 UIX 原 `+weapwheel`，再增加明确 CVAR 或 class 路由；不要在最小实验中直接覆盖 UIX 脚本。
- 评估 10–12 分区下的图标间距和屏幕比例。

## 验收清单

- 不加载 UIX 时不报错，按键无效果。
- 加载 UIX 时，固定 class 的 3、4、6 等不同武器数量产生对应分区数。
- 每个分区恰好一个武器，圆周等分，不受 DTADD slot 影响。
- 0–2 武器定义不打开 wheel。
- 非注册 class 不打开新 wheel，UIX 原轮不受影响。
- 当前装备武器是初始选中项。
- 松开按键后只切换到合法、实际持有的注册武器。
- 客户端选择和服务端实际武器一致。
- 道具轮或其他 UIX wheel 已打开时，新轮不会覆盖它。
- 死亡、观战、变身和地图切换后没有残留 `wheelName` 或错误选择。
- 4:3、16:9 下图标均无明显重叠；12 分区是首期压力测试上限。
- ACS 编译通过，并使用 MM8BDM → miscfixes → UIX → Unholy 的加载顺序测试。

## 明确不做

- 不支持打开轮盘期间增减武器。
- 不扫描任意第三方 DTADD 武器作为当前 class 的成员。
- 不覆盖 UIX 的通用 `UIXWHEEL.o`。
- 不修改 UIX 原版 weapon bar。
- 不为 1–2 把武器创建轮盘。
- 不在首期同时重构所有 copy weapon API。
