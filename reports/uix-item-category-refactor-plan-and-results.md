# Unholy Item 的 DTADD 分类重构方案与校正结果

## 结论

把展示分类作为 Unholy Item 的核心元数据，直接保存 `DTADD_GRP_*` 常量；UIX 兼容层只读取该数据并调用 `DefineAssistItem`，不再维护第二份分类表。

本次按道具的**主要使用效果**检查了 88 个已注册道具。建议修改 17 项分类；最终共有 `ATTACK` 54 项、`GIFT` 9 项、`HEAL` 10 项、`WEAPON` 6 项、`PASSIVE` 4 项、`JUMP`/`DASH`/`FLIGHT` 各 1 项、`ESCAPE` 2 项。没有道具符合 `RELOAD` 或 `FULLRESTORE`。

## 分类规则

以下规则以 DTADD 文档给出的语义为准，并用“主要效果”解决同时具有多种副作用的道具：

- `JUMP`：直接提供垂直位移。
- `DASH`：直接提供水平位移。
- `FLIGHT`：飞行或极强的持续机动。
- `WEAPON`：为玩家附加持续、自动或反击型攻击能力，而不是一次性发射普通攻击。
- `GIFT`：主要产出另一个可拾取/可用道具；随机箱及掉宝容器也属于此类。
- `ATTACK`：一次性杀伤投射物、陷阱、攻击型召唤或全局杀伤效果。
- `ESCAPE`：立即脱离当前位置或直接结束当前战斗流程。
- `HEAL`：主要恢复生命；提高生命上限仍归于治疗。
- `RELOAD`：只恢复武器能量或弹药。
- `FULLRESTORE`：同时恢复生命与武器能量。
- `PASSIVE`：使用后留下非武器型的持续保护、复活等效果，或本身不可主动使用。

若一个道具既有收益又有代价，按玩家使用它所追求的主要收益分类。例如 Fortune Coin 的成功结果是治疗，即使失败会伤害玩家，仍归 `HEAL`。名称中出现 Tank 也不能自动推导为 `FULLRESTORE`。

## API 重构方案

### 1. 扩展唯一数据源

将公开定义改为：

```c
DefineUnholyItem(id, actor, name, icon, dtaddGroup, mugshot, stingSound)
```

其中 `icon` 和 `dtaddGroup` 与身份、名称一样写入 Unholy Item 数据表。现有 API 尚无外部模组调用者，因此可以直接做破坏性签名变更，不需要保留旧签名或增加映射层。

直接存储 `DTADD_GRP_*`，不再定义一组数值相同的 `UH_ITEM_GRP_*` 常量。这样调用点能直接表达 UIX/MM8BDM 的展示含义，也避免注册 UIX 时再映射一次。

### 2. 扩展数据表和访问接口

- 在现有每项记录中增加 `icon`、`dtaddGroup` 字段。
- 给内部代码提供按 ID 读取 actor、name、icon、group 的只读访问方式。
- 注册时校验 group 是否为已知 `DTADD_GRP_*`；非法值记录警告并拒绝该项，避免数组越界或静默放错轮盘。
- `PASSIVE` 是合法值，不能用 `-1` 代替。UIX v3bh 会把它映射到 `IWGRP_NULL`，所以这类项目不会显示在主动道具轮中。

### 3. 删除 UIX 的重复清单

将 `UH_UIX_RegA/B/C` 的 88 行硬编码注册替换为遍历 Unholy Item 数据表：

```c
for (int id = 0; id < GetUnholyItemCount(); id++) {
    DefineAssistItem(
        GetUnholyItemName(id),
        GetUnholyItemActor(id),
        GetUnholyItemIcon(id),
        1,
        GetUnholyItemDTADDGroup(id),
        false
    );
}
```

实际实现应继续沿用项目当前的表访问方式，不必为了上述伪代码新增大量逐字段 named script。UIX 层只保留：UIX 是否加载的探测、一次性注册、失败计数和日志。

### 4. 最小实验顺序

先只迁移两项，验证两条不同路径：

1. `SuperMysticTankItem`：`DTADD_GRP_HEAL`，验证普通可见分区。
2. `InvincibleCandyItem`：`DTADD_GRP_PASSIVE`，验证合法注册但不进入 UIX 主动轮。

实验通过后一次迁移剩余 86 项，并删除硬编码分类。测试加载顺序固定为 MM8BDM → miscfixes → UIX → Unholy。

### 5. 验收条件

- 无 UIX 时，Unholy 的箱子、掉落、死亡掉落和物品使用行为不变。
- 有 UIX 时，注册日志为 88 项且无 `DefineAssistItem` 失败。
- UIX 轮盘中可见项目总数应为 84；4 个 `PASSIVE` 项不显示。
- 每个可见项目仅出现一次，图标、名称与 actor 对应。
- `RELOAD` 和 `FULLRESTORE` 分区没有 Unholy 项是预期结果，不应为填满分区而误分类。

## 88 项校正结果

“变更”列以当前 `uh_uix.acs` 的硬编码分类为基准。未标记的项目保持现有分类。

| ID | Actor / 显示名 | 建议分类 | 变更 | 判定依据 |
|---:|---|---|---|---|
| 0 | `PandoraBoxItem` / Pandora Box | `GIFT` |  | 随机给予另一项道具 |
| 1 | `SuperMysticTankItem` / Super Mystic Tank | `HEAL` | `FULLRESTORE` → `HEAL` | 只通过 `uh_Health` 恢复/扩展生命，没有补充武器能量 |
| 2 | `ShinBanishItem` / Shin Banish | `ATTACK` | `ESCAPE` → `ATTACK` | 发射 missile/rail 攻击，不移动使用者 |
| 3 | `FlingingDEItem` / Flinging Demoneye | `ATTACK` |  | 攻击型 Demoneye 召唤 |
| 4 | `TornadoDEItem` / Tornado Demoneye | `ATTACK` |  | 攻击型 Demoneye 召唤 |
| 5 | `FlashingDEItem` / Flashing Demoneye | `ATTACK` |  | 攻击型 Demoneye 召唤 |
| 6 | `RushCoilDEItem` / Rush Coil Demoneye | `JUMP` |  | 提供垂直弹跳 |
| 7 | `BoxDEItem` / Box Demoneye | `ATTACK` |  | 攻击型召唤 |
| 8 | `KillerBoxDEItem` / Killer Box Demoneye | `ATTACK` |  | 攻击型召唤 |
| 9 | `MoneyBaitItem` / Money Bait | `ATTACK` |  | 发射诱饵/伤害投射物 |
| 10 | `StepAsideItem` / Step Aside | `ATTACK` |  | 发射击退型攻击 |
| 11 | `ThunderTankItem` / Thunder Tank | `ATTACK` |  | 发射雷击投射物；不是恢复类 Tank |
| 12 | `WaspBombItem` / Wasp Bomb | `ATTACK` |  | 发射炸弹 |
| 13 | `LoliBalloonItem` / Loli Balloon | `ATTACK` |  | 生成有伤害判定的障碍物，不给使用者机动能力 |
| 14 | `GothicBalloonItem` / Gothic Balloon | `ATTACK` |  | Loli Balloon 的攻击型变体 |
| 15 | `DarkmanToyItem` / Darkman Toy | `ATTACK` |  | 攻击型玩具召唤 |
| 16 | `DemoneyeToyItem` / Demoneye Toy | `ATTACK` |  | 攻击型 Demoneye 召唤 |
| 17 | `GUHUItem` / GUHU | `ATTACK` |  | 主动范围杀伤 |
| 18 | `RubberBandItem` / Rubber Band | `ATTACK` |  | 发射攻击投射物 |
| 19 | `OnFireItem` / On Fire | `WEAPON` | `ATTACK` → `WEAPON` | 给玩家附加持续的近身燃烧攻击能力 |
| 20 | `SolitaireCardItem` / Solitaire Card | `ATTACK` |  | 发射攻击投射物 |
| 21 | `BluntRocketItem` / Blunt Rocket | `ATTACK` |  | 发射火箭 |
| 22 | `SharpRocketItem` / Sharp Rocket | `ATTACK` |  | 发射火箭 |
| 23 | `AirStrikeItem` / Air Strike | `ATTACK` |  | 呼叫空袭 |
| 24 | `UnholyWaterItem` / Unholy Water | `ATTACK` |  | 发射攻击效果 |
| 25 | `ZtarItem` / Ztar | `ATTACK` |  | 向场上投放对目标生效的有害物 |
| 26 | `MaltShopItem` / Malt Shop | `GIFT` |  | 延迟后给予随机食物道具 |
| 27 | `HotdogFoodItem` / Hotdog | `HEAL` |  | 恢复生命 |
| 28 | `CakeFoodItem` / Cake | `HEAL` |  | 恢复生命 |
| 29 | `PancakeFoodItem` / Pancake | `HEAL` |  | 恢复生命 |
| 30 | `HamburgerFoodItem` / Hamburger | `HEAL` |  | 恢复生命 |
| 31 | `SundaeFoodItem` / Sundae | `HEAL` |  | 恢复生命 |
| 32 | `BrickMineItem` / Brick Mine | `ATTACK` |  | 布置攻击陷阱 |
| 33 | `UnholyBookItem` / Unholy Book | `ATTACK` |  | 主动攻击效果 |
| 34 | `ContrabandItem2Item` / Contraband Item 2 | `DASH` |  | 生成水平移动平台 |
| 35 | `WhackSpellItem` / Whack Spell | `ATTACK` |  | 发射攻击法术 |
| 36 | `ChanceBoxItem` / Chance Box | `GIFT` |  | 随机产生其他箱子/道具或奖励结果 |
| 37 | `MysticBoxItem` / Mystic Box | `GIFT` |  | 随机给予另一项道具 |
| 38 | `PeriwinkleTankItem` / Periwinkle Tank | `WEAPON` | `HEAL` → `WEAPON` | 给予伤害增益/吸取能力，不恢复生命 |
| 39 | `YouWillDieItem` / You Will Die | `ATTACK` |  | 发射杀伤效果 |
| 40 | `SuperGUHUItem` / Super GUHU | `ATTACK` |  | 主动大范围杀伤 |
| 41 | `TheFootBallItem` / The Football | `ATTACK` |  | 发射攻击投射物 |
| 42 | `HackyCoffeeItem` / Hacky Coffee | `ATTACK` |  | 发射攻击投射物 |
| 43 | `BEESItem` / BEES | `ATTACK` |  | 攻击型召唤/投射物 |
| 44 | `AssHatItem` / Ass Hat | `GIFT` |  | 随机给予另一项道具 |
| 45 | `GoldenBoxDEItem` / Golden Box Demoneye | `ATTACK` |  | 攻击型召唤 |
| 46 | `GoldenKillerBoxDEItem` / Golden Killer Box Demoneye | `ATTACK` |  | 攻击型召唤 |
| 47 | `WishingStarItem` / Wishing Star | `ATTACK` | `WEAPON` → `ATTACK` | 一次性全局杀伤事件，不增强当前武器 |
| 48 | `WishingStarXItem` / Wishing Star X | `ATTACK` | `WEAPON` → `ATTACK` | Wishing Star 的杀伤变体 |
| 49 | `WishingStarCItem` / Wishing Star C | `ATTACK` | `WEAPON` → `ATTACK` | Wishing Star 的杀伤变体 |
| 50 | `InvincibleCandyItem` / Invincible Candy | `PASSIVE` | `HEAL` → `PASSIVE` | 给予持续无敌效果，不恢复生命 |
| 51 | `MoneyBombItem` / Money Bomb | `ATTACK` |  | 炸弹攻击 |
| 52 | `ThumbtackItem` / Thumbtack | `ATTACK` |  | 布置攻击陷阱 |
| 53 | `TankOfWondersItem` / Tank of Wonders | `GIFT` |  | 随机给予另一项道具 |
| 54 | `GoldenWaspBombItem` / Golden Wasp Bomb | `WEAPON` | `ATTACK` → `WEAPON` | 给玩家一段时间的持续/自动 Wasp Bomb 火力 |
| 55 | `MountainDewItem` / Mountain Dew | `ATTACK` |  | 发射攻击投射物；自身副作用不改变主要用途 |
| 56 | `DLC_CoinItem` / DLC Coin | `GIFT` |  | 随机兑换另一项道具 |
| 57 | `RandomPonyItem` / Random Pony | `ATTACK` |  | 发射攻击投射物 |
| 58 | `DeadlyFireArmsItem` / Deadly Fire Arms | `WEAPON` |  | 附加持续辅助火力 |
| 59 | `I_WinItem` / I Win | `ESCAPE` | `ATTACK` → `ESCAPE` | 主动结束当前战斗流程；不是伤害攻击 |
| 60 | `UnholyInsuranceItem` / Unholy Insurance | `PASSIVE` | `HEAL` → `PASSIVE` | 登记额外生命/复活保护；治疗只发生在之后的复活流程 |
| 61 | `CarpetBomberItem` / Carpet Bomber | `ATTACK` |  | 攻击型空袭 |
| 62 | `HogWashItem` / Hog Wash | `ATTACK` |  | 发射攻击投射物 |
| 63 | `GauntletExitItem` / Gauntlet Exit | `ESCAPE` |  | 主动退出/传送脱离 |
| 64 | `TruePowerItem` / True Power | `WEAPON` |  | 变身并获得强化战斗能力 |
| 65 | `DarkPurplePotionItem` / Dark Purple Potion | `HEAL` |  | 恢复并可扩展生命上限 |
| 66 | `GelatoPizzaItem` / Gelato Pizza | `ATTACK` |  | 发射攻击物 |
| 67 | `MistressBoxTimeFist` / Mistress Time Fist | `ATTACK` |  | 发射拳击投射物 |
| 68 | `MistressBoxSouret` / Mistress Souret | `ATTACK` |  | 发射攻击投射物 |
| 69 | `MistressBoxRegen` / Mistress Regen | `HEAL` |  | 持续恢复生命 |
| 70 | `MistressBoxPotion` / Mistress Potion | `HEAL` |  | 一次性恢复/扩展生命 |
| 71 | `MistressBoxGUHU` / Mistress GUHU | `ATTACK` |  | 发射 GUHU 攻击 |
| 72 | `LoliPornPicItem` / Loli Porn Pic | `PASSIVE` | `GIFT` → `PASSIVE` | `UseX` 始终失败，没有主动效果；归入 UIX 隐藏组 |
| 73 | `DickHatItem` / Dick Hat | `GIFT` | `ATTACK` → `GIFT` | 投出的帽子最终给予随机道具 |
| 74 | `DickheadItem` / Dickhead | `PASSIVE` | `ATTACK` → `PASSIVE` | 放置延迟复活/额外生命保障，不直接攻击 |
| 75 | `ColdSummonItem` / Cold Summon | `ATTACK` |  | 攻击型召唤 |
| 76 | `SuperAwfulBoxDEItem` / Super Awful Box Demoneye | `ATTACK` |  | 攻击型召唤 |
| 77 | `WonderStoneItem` / Wonder Stone | `GIFT` | `ATTACK` → `GIFT` | 生成可击破的掉宝石体，主要产出其他道具 |
| 78 | `MolotovCocktailItem` / Molotov Cocktail | `ATTACK` |  | 火焰攻击 |
| 79 | `FortuneCoinItem` / Fortune Coin | `HEAL` | `GIFT` → `HEAL` | 成功结果恢复半数最大生命；失败伤害是风险而非礼物 |
| 80 | `PlasticChairItem` / Plastic Chair | `ATTACK` |  | 发射攻击物 |
| 81 | `CrowNestItem` / Crow Nest | `ATTACK` |  | 攻击型召唤 |
| 82 | `PitSpikeItem` / Pit Spike | `ATTACK` |  | 布置攻击陷阱 |
| 83 | `AwfulBoxDEItem` / Awful Box Demoneye | `ATTACK` |  | 攻击型召唤 |
| 84 | `UrineBottleItem` / Urine Bottle | `ATTACK` |  | 发射攻击物 |
| 85 | `AssCounterDeviceItem` / Ass Counter Device | `WEAPON` | `ATTACK` → `WEAPON` | 附加受击后自动反射子弹的持续辅助火力 |
| 86 | `ZakoBoxItem` / Zako Box | `ATTACK` |  | 攻击型召唤 |
| 87 | `ContrabandWireAdaptorItem` / Contraband Wire Adaptor | `FLIGHT` |  | 提供持续、极强的立体机动 |

## 需要接受的 UIX 行为

`Invincible Candy`、`Unholy Insurance`、`Loli Porn Pic`、`Dickhead` 被正确标为 `PASSIVE` 后，在 UIX v3bh 中会进入 `IWGRP_NULL`，因此不会出现在主动道具轮。这不是注册失败，而是 UIX 对 DTADD 分类的既有展示策略。

如果以后希望“主动使用、使用后产生被动效果”的道具仍能在轮盘中选取，应在 UIX 兼容层增加独立的“是否在轮盘显示”元数据，而不应为了可见性把它们伪装为 `HEAL` 或 `ATTACK`。该问题与本次 DTADD 语义校正分开处理。
