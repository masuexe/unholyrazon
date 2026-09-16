# UIX 统一等分武器轮实施方案（固定 class + MegaManU）

## 决策

本方案取代原“仅固定武器 class、独立正式按键”的方案。

所有已接入的 Unholy class（包括 MegaManU）使用相同的武器轮规则：一个可选武器对应一个等角分区。玩家使用同一个按键、相同的选择方式和弹药展示，不需要按 class 学习两套轮盘。

class 的区别仅存在于内部候选武器收集器：

| 类型 | 候选来源 | 打开时的处理 |
|---|---|---|
| 固定武器 class | 显式注册的 class 武器清单 | 按清单顺序收集实际持有的武器 |
| MegaManU | 基础武器 + UHDT 中 kind 为 UHCOPY_MEGA 的记录 | 只收集实际持有的武器 |
| 后续可变武器 class | 以后新增的专属收集器 | 输出同一种线性快照 |

不改变 MegaMan 的随机发武器、复制、伤害或弹药恢复规则。DTADD slot、UHCOPY slot 仍可用于玩法逻辑，但不再决定轮盘分区。

## 玩家规则

- 总可选武器数为 0–2 时不打开轮盘，也不添加两武器快速切换。
- 3–12 把时，分区数等于本次快照中的武器数，每组恰好一项。
- 所有 class 使用同一个正式武器轮按键。
- 当前装备武器默认选中；没有有效默认项时使用第一项。
- 外圈图标、选中放大、中央名称及弹药条统一。
- 同一个 class 的相同武器集合保持相同顺序；不按获取时间或随机数排序。
- 打开后不实时改变武器集合，只更新弹药。下一次打开才重新收集。

“布局规则一致”不等于“每个 class 图标数量相同”；数量由可选武器决定，但交互规则不能切回另一套 slot 分类轮。

## UIX 的真实限制与首期容量

UIX v3bh 的 WHEELDT.acs 将 WHEEL_GROUPS_LIMIT 定为 12。UIXWHEEL.acs 的分区背景也只有 2–12 分区，并且仅在 groupCount < 13 时绘制。

因此首期不能直接对 13 把以上调用 newWheel，不能仅增大本项目的编译头文件常量：实际共享数组仍由 UIX 已加载的 WHEELDT.o 提供。

MegaMan 的百余个 DefineCopyWep 记录是候选池，不是玩家当前持有量。常规发放代码按六类选择复制武器，但这不能证明事件、addon 或其他发放路径绝不会使持有量超过 12。

实施时必须审计这些路径并记录正常最大持有量，基础武器也计入。处理约束：

1. 常规支持范围先限定为总数 3–12。
2. 超过 12 时安全拒绝打开并给出可理解的提示；不能越界、截掉武器或自动退回 MegaMan 旧分类轮。
3. 若审计发现正常游戏可超过 12，这就是正式上线的阻塞验收项，必须先补齐统一分页或扩容方案。
4. 分页/扩容若需要，必须是所有 class 共用的规则，不得成为 MegaMan 专属第二种交互。

首期不修改通用 UIXWHEEL 或 WHEELDT；也不通过限制玩家获得武器来迁就 UI 容量。

## 模块结构

在 acs_source/compat/mods/uix/ 中新增统一武器轮 library（概念名 uh_uix_weapwheel），并加入 LOADACS。结构分为：

1. class 路由与候选清单定义。
2. 固定清单/MegaMan 候选收集器。
3. 统一线性快照、显示、输入和生命周期。
4. 服务端 actor/class/inventory 校验。
5. UIX 原武器轮按键的入口适配。

不修改 ../references/ 中的只读 UIX 源码。新轮复用 UIX 的通用 WHEELDT API 和 UIXWHEEL 渲染。

## 固定 class 数据

保留原方案的 classActor、weaponActor、tag、icon、ammo1、ammo2 定义模型，按添加顺序作为顺时针顺序。

与原方案的差异：不再要求所有固定清单项必须同时持有才允许打开。固定清单是候选允许列表，打开时按 CheckInventory 收集实际持有项，这与 MegaMan 的玩家规则保持一致。

缺失项目可记录 debug 诊断，但不能因此回退到不同布局。空 actor/icon、重复定义、非法引用应在注册阶段报错。

用 GetActorClass(0) 查找实际 class actor，比较使用 StrICmp。形态、Shiny 或其他变体要显式映射到对应定义/收集器，不猜测 actor 后缀，不把所有 MegaMan 派生 class 自动当成 MegaManU。

## MegaMan 收集器

候选身份以 UHDT 的 DefineCopyWep 数据为准：

- 遍历 GetCopyWepCount()。
- 使用 GetCopyWepKind(row) == UHCOPY_MEGA 过滤。
- 使用 GetCopyWepActor(row) 取得 actor。
- 用 CheckInventory(actor) 收集实际持有项。
- 明确加入 MegaManU_W 基础武器，它不是复制武器记录。
- 去重 actor；不能把 base MM8BDM 武器与 Unholy 替代 actor 同时当成一项。
- 不直接扫描全部 DTADD 表并收集任意第三方武器。

显示元数据首期复用现有 uh_uix_megaweps.acs 的 DefineWeapon 注册结果：以 actor 在 DTADD 中查找对应记录，读取 tag/icon/ammo1/ammo2。初始化必须先完成现有注册；未找到元数据不能凭空生成默认图标或把武器静默丢弃。

顺序建议基础武器在前，复制武器按 UHDT 记录顺序。现有记录按玩法 slot 聚集，但每把仍有独立等分区，不绘制类型扇区。未来若要改变 UI 排序，使用单独的展示顺序字段，不能重新排列 UHDT 记录：Mega dmg id 与登记顺序有关。

暂保留 DefineWeapon 注册，因为 UIX weapon bar 仍依赖它。不能在轮盘切换后直接删除 uh_uix_megaweps.acs。后续再统一武器 UI 元数据，避免同时扩大本次 API 重构范围。

## 统一构建与显示

每次按下武器轮按键：

1. 检查本地控制台玩家、存活/非观战状态、UIX 是否加载、数据是否就绪。
2. 如果已有任何 UIX wheel，退出，不抢占道具轮。
3. 用 class 路由选取候选收集器。
4. 生成统一线性快照：actor、tag、icon、ammo1、ammo2、显示顺序。
5. 检查数量 0–2 / 3–12 / 13+。
6. 查找当前装备武器在快照中的 index。
7. newWheel("uhweaponwheel", weaponCount, currentIndex)。
8. 第 i 项调用 addWheelItem(actor, i)，每组仅一把武器。
9. 添加通用未选中/选中/中央元素并 startWheel。

不使用 UIXWEAP 的 slotVals[slot][index] 作为新轮主结构，不修改 UIX 的角度或鼠标算法。

UIX 通用轮盘结束时会先 destroyWheel，再调用选择 callback。因此 callback 不依赖已经被清理的 wheel 内容取得 actor：保存独立快照，按 callback index 读取并完成校验，随后清理快照。

弹药条沿用 UIX 样式；settings callback 只更新 amount/max，不重建分区。当前武器被移除、死亡、变身或观战时设置取消原因并关闭，不能自动选择旧快照中的项目。

## 同一个正式按键

测试阶段可以保留临时独立 alias 便于 A/B 检查，但正式版接管 UIX 的 +weapwheel / -weapwheel，使已有玩家绑定仍然有效。

建议在 Unholy KEYCONF 中重定义这两个 alias，指向唯一的 UH start/end 网关，不直接覆盖 UIXWEAP.o，也不定义同名 ACS script 去依赖覆盖顺序。

- 所有已接入 class 包括 MegaManU 都路由到统一新轮。
- 未接入 class 的原 UIX 轮仅可作为开发迁移期间的兼容措施；正式统一发布前完成目标 class 清单审计，不能声称已统一却让部分正常多武器 Unholy class 长期退回旧布局。
- 不增加“按 class 默认不同”的展示开关。
- 网关记录本次按键实际启动的轮类型和 owner/token；松开只结束它，不能关闭其他 wheel。
- 无 UIX 时不调用其轮盘库、不报错。
- 保持 MM8BDM → miscfixes → UIX → Unholy 的已支持加载顺序。

## 网络切换

客户端选择 callback 按快照 index 取 weapon actor，使用 UIX 的 NamedSendNetworkString 模式发送到 UH NET 服务端脚本。

服务端重新校验：

- 调用者仍存活且处于允许的 class/形态。
- weapon actor 属于该 class 的候选允许列表；MegaMan 项为基础武器或当前注册的 UHCOPY_MEGA actor。
- 玩家实际持有该武器。
- 验证通过后才 SetWeapon。

服务端不需要信任客户端快照，也不接受任意字符串直接切换。失败、取消或无效 index 均不切换武器。

## 实施与验收顺序

### 阶段 1：共享核心最小实验

选择一个 3–6 武器固定 class，实现候选定义、一维快照、图标/名称和网络切换。验证 0–2 不开轮及每把独占一个分区。

### 阶段 2：同批接入 MegaManU

实现 UHCOPY_MEGA 收集器和基础武器入口，复用同一个 renderer。验证随机发放后的 actor 与图标一致、当前装备默认选中、武器数变化在下一次打开反映。

审计正常最大持有量，测试 12 和 13+ 容量边界，不能以单次常规发放数量代替全路径证明。

### 阶段 3：正式入口和弹药

增加通用双弹药条、取消状态、服务端校验、原 UIX 按键网关。保留 weapon bar 所需的 DefineWeapon 注册。

测试单机与服务器/客户端，确保切换结果一致，原道具轮与 weapon bar 不受损。

### 阶段 4：统一发布门槛

- 所有本次发布目标多武器 class 均使用统一入口与等分规则。
- 固定 class 与 MegaMan 的相同武器数量表现一致。
- 0–2 不开轮，3–12 每项独占分区。
- 无重复 actor、空白图标或错误弹药类型。
- 顺序稳定，不随获取顺序改变。
- 增减武器只影响下一次打开，不突然旋转正在使用的分区。
- 死亡、变身、观战及地图切换安全取消，不误选。
- 4:3/16:9 下 3、6、12 分区可用。
- 13+ 若为正常可达状态，统一容量方案完成后才发布。
- 无 UIX 不报错；已有 +weapwheel 绑定能启动新轮。
- ACS 编译、PK3 验证通过；运行测试使用已支持加载顺序。

## 来源与不做事项

依据本地 UIX v3bh 的 acs_source/UIXWEAP.acs、UIXWHEEL.acs、uix_imports/WHEELDT.acs、KEYCONF，以及本项目 UHDT / copy_weapon_runtime.acs 的现有 API 与发放逻辑制定。

本轮不改玩法分类、伤害 id、随机发放或复制规则；不修改只读参考树；不实现打开期间实时重排；不把统一轮盘变成所有第三方 DTADD 武器的自动收集器。
