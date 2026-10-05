# Eden：Razon 3 道具补齐

参照 `../references/for_8bdm-v6a/uh-ub_razonpatch_3.11.1/acs_source/RAZONLIB.acs` 的实际启用池和 `actors/Wep/Eden/` 中的实现。本次加入五件；Ladder（60）按要求暂不加入。

| ID | 道具 | 池／消耗 | 效果 |
|---|---|---|---|
| 313 | Holy Mantle | Shiny 天使主道具，品质 4 | 挡下一次伤害，120 tic 后恢复；不阻止 Damocles、Telefrag 或放弃生命的伤害 |
| 330 | Soy Milk | 普通主道具，品质 2 | 泪弹 HUD 射速乘 5（遵守现有上限 300），伤害除 5；按旧版在 Ipecac 后、Godhead 前应用 |
| 33 | The Bible | 主动道具，300 充能 | 飞行 180 tic；Assist 显示圣经图标、递减条与向上取整的剩余秒数，结束后隐藏（遵守 Assist 显示／数字设置） |
| 145 | Guppy’s Head | 主动道具，150 充能 | 每次召唤两只蓝苍蝇，近战伤害为主人当前 Eden 伤害的两倍 |
| 578 | Free Lemonade | 主动道具，300 充能 | 喷射 48 tic，液滴伤害 131，地面残留伤害 130、最长 500 tic |

Car Battery 重复执行主动效果且只支付一次充能：圣经刷新同一飞行计时，不叠加属性层；苍蝇和喷射各执行两次。Endless Ammo Rune 仍按共用代码减半充能消耗。

Holy Mantle 不使用旧版已缺失的 `RogueDXShieldWasHit` 或共享 Buddha 状态，直接在伤害 EVENT 中取消该次伤害；Eden 的其他受击道具先检查披风，避免脚本排序影响结果。盾及破盾特效由服务器生成并同步，远程客户端默认保持动画。圣经用 `core_flyplayer` 只添加／撤销自己的飞行层；死亡、失去道具和转换机体会结束控制器，转换后的旧计时器由代次编号失效。苍蝇搜敌检查原生队伍和 `uh_AreGameplayTeammates`，主人死亡、离线或失去 Guppy’s Head 后消失。液体喷射在主人失效时停止，已产生的地面残留按原版计时结束。

旧目录中还有 Technology（68）、Guillotine（206）、Ludovico Technique（329）、Spirit Sword（579）和 Dead Sea Scrolls（124）。它们未进入上述实际启用池；其中一些只有占位 flag 或未接通的 actor。本次不将这些未完成项目注册为可抽取道具。

图标、披风、苍蝇和液体贴图，以及所用音效均复用仓库已有素材。验证范围：原生 ACC 编译、DECORATE include／actor／命名脚本及素材引用检查、PK3 完整性检查；本次未进行引擎实机或双客户端联机验证。
