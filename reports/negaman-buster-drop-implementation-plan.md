# Negaman：Nega Buster 特武掉落实施方案

## 目标与建议规则

本报告仅制定方案，不修改游戏代码。参考本机 `../wads/uh-ub_razonpatch_3.11.1.pk3`，实现以下行为：

1. Nega Buster 对敌人造成有效伤害时，按蓄力档位随机掉落一件实体 Nega 特武。
2. 该次伤害实际杀死敌人时，确保该次伤害总计掉落一件；命中 RNG 已经掉落的，不再额外掉第二件。
3. 需要选择掉落武器时，从 **Buster 弹体的 `target`（发射者）尚未拥有的 Nega 特武**中随机选择。只有全部拥有时，才从整个有效池随机选择。

“缺少特武”按武器 actor 的库存数量判断，弹药耗尽但仍持有武器不算缺少。优先规则只改变武器选择，不提高普通命中的掉落概率；击杀保底也使用相同选择规则。地上尚未拾取的武器不计为已拥有。

| Buster 档位 | 普通命中掉落概率 | 击杀掉落 |
| --- | --- | --- |
| `NegaChargeShot1` | 16/256 = 6.25% | 一件 |
| `NegaChargeShot2` | 32/256 = 12.5% | 一件 |
| `NegaChargeShot3` | 64/256 = 25% | 一件 |

推荐默认范围是普通 `NegaMan` 发射的三档 Buster，包括二档 RIPPER 的实际伤害次数、三档直接伤害及爆炸伤害。一次弹体可以伤害多个敌人，各自独立判定；同一受害者的致死伤害只保底一次。滑踢、Nega 特武、环境伤害不触发。Shiny 和 ShinNegaman 不自动获得新机制，需按发射者身份明确排除；这是范围建议，并非用户已经要求排除它们。

敌人范围以本项目 LMS 的敌对玩家为首期目标，依据当前模式和队伍关系判断；FFA 中其他玩家属于敌人，同队和自伤不触发。若需要合作模式怪物也掉落，必须另行覆盖其伤害事件启用及死亡入口，不能宣称只改玩家 ClassBase 就支持所有可攻击 actor。

## 已核对的源代码

### razon3 的参考行为

只读检查 `../wads/uh-ub_razonpatch_3.11.1.pk3` 内：

- `actors/ClassBase.txt:14–25`：`Pain.NegaBuster/2/3` 分别 `A_Jump(16/32/64, "NegaDrop")`，成功后给予受击者 `NegaWepDropper`。
- `actors/Wep/Negaman/NegaMan_W.txt:158–214`：二、三档分别使用 `NegaBuster2`、`NegaBuster3` 伤害类型。
- `actors/Wep/Negaman/NegaWepList.txt:282–305`：实体 `NegaWepGiver` 的拾取限制；各具体 giver 使用武器图形、有限存活时间。
- 同文件 `822–861`：`NegaWepDropper` 等概率选择 34 个硬编码 giver，从受击者位置抛出，水平速度 1–3、向上速度 4–8、随机方向。

旧版没有本次要求的击杀保底、发射者缺武器优先。其列表不能直接移植：v4 的注册池不同，而且旧 `NegaTimeStopperWepGiver` 错误检查并给予 Thunder Beam（`332–333`），必须避免继承此类错误映射。

### v4 现状

- [NegaMan_W.dec](../src/actors/classes/survivors/NegaMan_W.dec)：三档均继承 `DamageType "NegaBuster"`；二档 RIPPER，三档 Death 中 `A_Explode`。Shiny 弹体又继承普通弹体，因此仅凭伤害类型无法区分普通/Shiny。
- [ClassBase_UH20_HitEffects.dec](../src/actors/player/classbase/root/ClassBase_UH20_HitEffects.dec:11)：当前命中分支统一概率 16/256；成功后在受击者上下文执行 `uh_GiveRandomCopyweps(2)`。
- [copy_weapon_runtime.acs](../src/acs_source/classes/shared/copy_weapons/copy_weapon_runtime.acs:200)：参数 2 调用 `GiveNegaStartCopyWeps()`，直接给予当前 activator 三把随机武器。它是开局发武器逻辑，不能继续充当掉落接口。
- [copy_weapon_registration.acs](../src/acs_source/classes/shared/copy_weapons/copy_weapon_registration.acs:152)：当前注册 26 把普通 Nega 特武，按世代分组。
- [baseweaponedit.txt](../src/actors/inventory/baseweaponedit.txt:96)：`BaseNegaManWep` 限制 `Inventory.RestrictedTo "NegaMan"`；现有具体武器已经有地图 Spawn 图形。
- [ClassBase_UH00.dec](../src/actors/player/classbase/root/ClassBase_UH00.dec:1)：普通痛率 256，但 `+USEDAMAGEEVENTSCRIPT` 被注释。其他类可覆盖痛率/痛状态，因此 Pain 并不等于所有有效命中。
- [uh_copyweps.acs](../src/acs_source/classes/shared/copy_weapons/uh_copyweps.acs)：已有动态池 API、EVENT 使用模式和运行时聚合器，可在现有库增加实现片段。

### Zandronum 的关键约束

已查询只读引擎源 `../references/zandronum/zandronum-stable-branch-default/src/`：

- `p_interaction.cpp:1700–1750`：实际死亡调用 `Die` 后直接返回，不经过 Pain；不能在 Pain 内判断血量来补击杀。
- `p_interaction.cpp:1775–1830, 1870`：Pain 受 NOPAIN、PAINLESS、痛率等条件影响，受击者的普通 `target` 更新还可能发生在 Pain 后，不能把它当作当前弹体的发射者。
- `p_interaction.cpp:493–500, 869–903`：死亡时通常将受害者 `target` 设为 source，并按实际死亡伤害类型寻找专用 Death；专用死亡状态后必须接回原死亡流程。
- `gamemode.cpp:1316–1348`、`actorptrselect.cpp:40–41`：伤害 EVENT 有专用 `AAPTR_DAMAGE_TARGET/SOURCE/INFLICTOR`，这些指针只能在对应脚本上下文取用。EVENT 的初始 activator 不是直接可当成玩家的受击者。
- `p_interaction.cpp:1527–1586`：`GAMEEVENT_ACTOR_DAMAGED` 是伤害处理中的同步可修改事件，仍在扣血/部分生存处理之前。不能仅用 `dmg >= health` 推断实际死亡。

## 推荐实现：命中事件 + 实际死亡补足

### 1. 保留伤害类型，识别弹体档位

保留三档的 `DamageType "NegaBuster"`，避免增加 `NegaBuster2/3` 后遗漏弱点、保护和队伍免伤中的伤害因子。事件中使用 damage inflictor 的 actor 类型识别三档（先三档、再二档、再一档，注意继承关系），再检查其 `target` 是否为普通 NegaMan。

三档爆炸的 inflictor 仍需在实施时沿 `A_Explode` 和半径伤害调用链核实；如果改成独立爆炸 actor，要显式传递发射者与档位。禁止用 `GetWeapon()` 判档，发射者可能在命中前换武器。

### 2. 在共享库捕获有效命中

在 `classes/shared/copy_weapons/` 新增 `negaman_buster_drops.acs`，由 `uh_copyweps.acs` include；不新增 library，不改 LOADACS。

新增 `EVENT` 脚本，仅处理 `GAMEEVENT_ACTOR_DAMAGED`。正确切换 activator 后，依次检查受害者、正伤害、敌对关系、inflictor 与发射者身份。同步记录本次受害者的命中序号、发射者身份、是否已成功生成掉落物；随后掷档位对应概率，成功则选择并生成一件。

每次新的伤害事件都必须使旧的“本次 Nega 命中”记录失效，包括其他武器造成的伤害，避免后续死亡读取陈旧数据。记录应属于受害者的本次生命；使用 ClassBase 的 UH 用户变量/明确的生命序号，不只按 player number 保存永久全局标记。不要借用受害者 `target/master/tracer`，以免破坏原有机制。

选择时切到 **inflictor 的 target** 检查库存，保存所选 actor，再恢复受害者/掉落位置上下文。不要把 `AAPTR_DAMAGE_SOURCE` 和弹体 `target` 默认为永远相同；source 可作为归属核对，不取代用户指定的 target。

在 UH 玩家根启用 `+USEDAMAGEEVENTSCRIPT`，并检查各后代是否设置 `-USEDAMAGEEVENTSCRIPT` 或 `+NODAMAGEEVENTSCRIPT`。该启用也会激活已有暴击/队伍友伤等 EVENT，因此实施前必须审计现有所有伤害 EVENT 的返回值、过滤和执行顺序。

**事件顺序是实施前的必要核验项：**事件还能修改/取消伤害，掉落不得发生在其他处理最终将伤害清零之前。须查询引擎 EVENT 调度，证明本库处理能在有关伤害修改之后执行，或将采样与实际生成分开，待既有修改接口确认后生成。不能凭 include 顺序假定跨库执行顺序，更不能为了掉落改写全局伤害返回值。若无法保证这一点，应改用 Pain + Death 的保守实现，并明确其对 NOPAIN/自定义痛状态的覆盖限制。

### 3. 死亡状态补足，致死命中总计一件

在 UH40 的死亡效果层增加 `Death.NegaBuster`，通过同步 `ACS_NamedExecuteWithResult` 调用保底接口，再接回原普通死亡入口。若后代覆盖该标签，或使用独立 DeathType/特殊死亡入口，要同步覆盖，特别检查 Boss 的死亡和复活路径。

保底接口验证当前生命/最近命中记录，检查是否已经成功生成：已生成则仅标记完成；尚未生成则无概率门槛，使用同一缺武器优先算法生成一件，并标记完成。必须在生成成功后才置“已掉落”，不能将 RNG 成功等同于生成成功。重复进入死亡入口不再掉落。

如此无需在 EVENT 预判死亡：致死事件先走普通命中 RNG，实际死亡时再补足，最终仍是一件。Buddha、救命道具等让玩家存活时，只保留普通命中概率。受害者其他伤害后才死亡时，不能沿用上一发 Buster 的保底资格。

### 4. 从动态武器池中选缺少的武器

使用现有 `CountCopyWepByKind(UHCOPY_NEGA)` 和 `GetCopyWepActorByKindIndex(UHCOPY_NEGA, i)`。两次有界扫描即可，不使用反复重掷直到抽到缺武器的循环：

```text
pool = 注册表中有效、可生成对应掉落物的普通 Nega 武器
missingCount = pool 中发射者 CheckInventory(weapon) == 0 的数量
若 missingCount > 0：随机选择第 0..missingCount-1 个缺少的武器
否则：随机选择 pool 中一件武器
```

按武器而非世代均匀抽取：同世代的另一把武器未持有，仍属于缺少。池查询应避免重复 actor 加权。空池须记录错误并退出，禁止无界重掷；正常启用本机制的前提是至少有一个有效掉落映射。全拥有仍需能掉落，不能因 missingCount 为零取消击杀保底。

### 5. 实体拾取物

推荐采用一个 UH 通用 `CustomInventory` 掉落 actor，携带确定的普通 Nega 注册索引，在 Pickup 调用共享接口给予对应现有武器。武器在生成时选定，拾取时不重掷；索引只在本地图注册表稳定后使用，不跨地图保存。

复用当前武器 Spawn 图形，使用合理碰撞半径和重力，从受害者位置上抛；外观资料作为 UH 掉落映射维护，不能重新复制一份独立 RNG 武器清单。扩展注册武器需提供掉落外观或通用后备图形，确保扩展武器不会因缺图失去击杀保底资格。

建议有限寿命参考旧版约 20 秒后闪烁消失；禁止地图物品重生，避免 LMS 中一件变成无限来源。物品是服务器 gameplay actor，不加 `+CLIENTSIDEONLY`。生成应绕开受害者碰撞造成的失败，保留位置可达性，检查生成函数返回结果。

推荐允许任意普通 Negaman 拾取，选择优先依据始终是原发射者；不额外加入独占归属。非 Negaman 拾取失败且物品保留。新武器拾取成功后移除物品；重复武器按既有武器拾取规则补弹，库存/弹药已满则失败并保留。通用 giver 必须以实际武器是否成功接受为准，不能无条件消耗物品。Shiny 拾取权限单独过滤，避免仅靠继承误放行。

直接 Spawn 现有武器也可作为较小实现，但须先证明它们统一满足单次拾取、重生、寿命、重复武器和联网行为；不能以存在 Spawn 图形代替这些核验。

## 改动清单与执行顺序

| 文件/范围 | 计划改动 |
| --- | --- |
| `src/acs_source/classes/shared/copy_weapons/negaman_buster_drops.acs`（新增） | EVENT 采样、敌我/档位检查、有界抽取、实体生成与拾取、击杀补足 |
| `src/acs_source/classes/shared/copy_weapons/uh_copyweps.acs` | 纳入新实现片段，保留原库名 |
| `src/actors/player/classbase/root/ClassBase_UH00.dec` | 启用并审计伤害 EVENT；声明 UH 专用本次命中/生命记录 |
| `src/actors/player/classbase/root/ClassBase_UH20_HitEffects.dec` | 移除旧 `NegaBusterGive` 发三把武器逻辑；Pain 保留原痛反馈，不重复 RNG |
| `src/actors/player/classbase/root/ClassBase_UH40_DeathEffects.dec` | 专用 Death 保底入口，接回现有死亡流程 |
| `src/actors/classes/survivors/negaman_copyweps/` | 通用实体掉落物、图形映射及必要 include |
| 相关玩家后代、Boss Death/Pain 覆盖 | 核对事件启用、死亡保底入口和重入 |

先完成 EVENT 顺序与爆炸归属的源代码核验，再落实掉落 actor 和动态池，最后接命中/死亡入口并删除旧命中给予行为。保留 `NegaManCopywepGive_P`、`uh_NegaManStartMoves` 和开局三把随机特武；本次要求没有指定取消开局武器。

## 验收与验证

- 三档分别验证 RNG 通过/失败；普通命中至多一件，致死命中无论 RNG 结果总计一件。
- 发射者只有一把未拥有时，每次成功掉落必为该武器；缺少同世代另一把时也能选中；全拥有时照常掉一件。
- 受击者持有的武器不影响选择；双 Negaman 同时攻击时，各自按各自弹体 target 判断。
- RIPPER 多次实际伤害、多目标爆炸、三档直接伤害后爆炸、多人同 tic 击杀：每次伤害独立，致死次数不重复保底。
- 无敌、伤害因子零、同队、自伤、其他武器补刀、NOPAIN、Boss 自定义死亡和复活后再死亡均检查。
- 发射者换武器、死亡或断线时不崩溃；优先使用事件时的有效 target 库存，之后 target 失效时使用已选结果或全池后备，不错误查询复用的玩家槽位。
- 非 Negaman、Shiny、重复武器、弹药全满拾取以及掉落寿命/重生检查；所有 26 把和新增注册武器映射正确。
- 联机服务器生成/选择一次，客户端不自行 RNG；核对实体数量、拾取消失和库存/弹药同步。

实施时先静态核对并使用本项目配置的原生 ACC 编译相关现有库，输出至 `src/acs/`；按项目约定打包 `src/` 为 `out/build.pk3`。本报告阶段没有编译、打包或启动引擎。若后续获准运行验证，使用技能规定的 Zandronum 版本和最小 v6b 配置，保持 IWAD → v6b → mandatory miscfixes → 本 mod 的顺序。
