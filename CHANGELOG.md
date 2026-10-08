## 4.0.0-beta.261009

- 修复 Clownpiece 符卡名、倒计时和奖励状态在联机远端玩家及旁观者处不显示的问题：客户端绘制不再受 Boss 激活者限制，并防止旧阶段的清除、失败通知或计时脚本覆盖新阶段 HUD
- 调整 MegaMan Noise Crush 二阶段声波：碰到地板后立即检查回收，使近距离射地板也能回收充能并接三阶段
- 将 Oil Slider 油坑改为所有职业均可骑乘：自己和队友可直接上板，敌人碰到油坑后先结算伤害再上板；滑行独立于当前武器，重复踩油可补充时间，死亡或变身时解除滑行；将剩余滑行条移至 assist 显示
  - 滑行时按 M1 跳起下板的 v6b 行为，不耗弹；M2 可继续射油补充滑行时间

## 4.0.0-beta.261008

- 将以下敌人改为 coop 杂兵：
  - Biribaree
  - Blader
  - ScrewBomber
  - Metrenger
  - KillerBullet：先沿原朝向飞行，发现玩家后加速直线冲向目标；穿过玩家，撞墙或被击毁时爆炸
- 修复 Zangief（含 Shiny）死亡时出现两个尸体的问题
- 修复 DLC Centaurman 的 Option 在联机客户端提前消失、不可见及朝向不同步的问题；左右 Option 按玩家独立生成和补齐，多个 DLC Centaurman 不再互相占用名额；关闭 Option、减少数量或主人离场时正确回收，并修复两个 Option 同时清理时遗留一个的问题
- 修复 DLC Centaurman 的 Reload 不能造成隐身的问题
- 调整普通 Time Stopper 定身：目标再次受到护甲结算后的正伤害时提前解除，下一 tic 恢复移动；首次定身命中不触发解除，后续 Time Stopper 伤害不立即重新定身；全局时停分支保持原有规则
- 将 MegaMan Noise Crush 第三阶声波的单次爆炸基础伤害由 314 降为 50，与 Razon 3 一致；保留每日伤害倍率、现有爆炸频率和范围
- 修复 Sad Toadman 二阶段 MadFire、StormFlush 与 Toadgasso 大招期间无法转向的问题：改为只锁定移动（`uh_stopplayer`），恢复原版施放时可转向及 Toadgasso 冲刺方向随视角变化；施放期间禁用跳跃，与原版一致
- 修复联机时 Captain Blitzkrieg 大招能量条两端不同步的问题：在能量将满时按 R，服务器和客户端可能一边放了大、另一边没放，导致用完大后条仍显示已满，或条已清空但大没有放出；现在回能、扣能和是否放大都由服务器决定并同步给客户端（新增通用辅助 `classes/shared/server_power.acs`）
- 补全 ColdDragoon 黑漆效果的 `FISHBLACKPAINT_DYE = 19999` 全黑色表，并移除未使用的 ACS 配色常量 `POWERFLIGHT = 10680`
- `tools/compile-acs.sh` 现在会一并编译 `UHCOMBDB`，干净构建不再需要手动编译

## 4.0.0-beta.261007

- 为生还者失败画面补充对局用时，胜利与失败画面的用时统一四舍五入并显示小数点后两位（如 `Battle Time: 12.34s`），保留原有速杀奖励判定规则
- 新增 Keep on Fire（On Fire）入水烧开水效果：身体至少一半浸水后约半秒进入沸腾，普通水域共享温度并在热源离开后逐渐冷却，全局水域仅影响热源周围 128 单位且视线可达的水中玩家；每约半秒造成 `80 × 火焰层数` 的烫伤，队友伤害减半，多热源按队友伤害倍率取最强的一份并保留击杀归属；水中以烫伤替换原火焰范围伤害，保留自身烧血，加入气泡、水面蒸汽与声音
- 新增 trill-pingbutton-v5h 兼容覆盖：Unholy LMS 中所有玩家与旁观者均可看见各阵营的 ping，包含死亡标记和定位结果，支持死亡及第三人称视角，保留个人显示、静音和声音设置；定位目标接入 Unholy 队友关系，头像接入统一职业展示接口；需将 PingButton 加载在 Unholy 之前
- 将 TidalManiac（含 Shiny）的水雷 M1 合并到主武器的 Reload，保留原有耗能、动画和护盾分支；移除独立水雷武器及其初始装备、武器槽、变身发放和多武器注册，补充普通／Shiny 的 Reload 图标；Bot 改为直接发射水雷，特殊攻击使用地雷散射与 Torrent，不再切换武器
- 优化 TidalManiac 的武器 HUD 动画
- 补齐 Razon 3 的服主自定义阈值：连胜、连败、Hell Mark、Speciman 击杀、Gauntlet 宝藏兑换、Bad LMS 次数及 Bonus Event 回合间隔，支持在 Server Options → Game Rules → Round Thresholds 中直接输入 1～100 并保存配置；保留当前默认值，宝藏兑换只扣除设定数量并保留余数；配置说明见 [回合阈值](docs/round-thresholds.md)
- 将 Bonus Event 随机选择接入与 Boss 相同的低频优先机制：优先抽取出现次数最少的合格事件，同次数时按原权重随机；保留人数限制、上一场排除、强制指定及 EX 升级规则，仅在事件实际启动时计数，EX 计入对应基础事件的次数，记录跨回合与地图保留
- 优化玩家旁观时按 Enter 打开的选人与加入界面：支持通过 TextField 手动输入职业名加入游戏
- 补齐 Unbound 遗漏的自定义文本颜色定义：在 `TEXTCOLO` 中恢复 `w Ice`、`x Fire`、`y Sapphire` 及 `z Teal`，使 `\c[Teal]` 与 `\c[Sapphire]` 在界面和提示中正常渲染
- 修复 Nega Super Arm（含 Shiny）投掷后抓取时限条仍闪烁的问题
- Bonus Event 胜者确认自选 Boss 后，若在开战分配前旁观或掉线，保留所选 Boss 并强制交给另一名随机的在场存活玩家；胜者在倒计时内重新加入也不会取回选择
- 按用途重新划分 Qwant 招式：2 远程、3 连射、4 近战、5 强力、6 范围／控制、7 防御／辅助；UIX weaponbar 与 wheel 同步使用实际槽位，保留元素属性、弹药和开局抽选规则
- 解除 Qwant 开局招式数量的四招上限，支持全部注册招式及 addon；招式重学改为替换当前招式并排除所有已持有招式，持有全部招式时不消耗重学资源；Pharaoh Roulette、UIX 武器条和轮盘改为读取完整持有列表，轮盘支持完整招式列表和可滚动分组
- 新增 Qwant／NegaMan 开局复制武器数量的服务器设置，支持在 Server Options → Rules 中直接输入：Qwant 默认 4 招；NegaMan 默认 3 把，达到或超过注册武器池总数时发放全部复制武器；保留基础武器，抽选不重复，并同步适配 Qwant 空招式槽的招式重学及 UIX 武器轮盘；配置说明见 [开局复制武器数量](docs/copy-weapon-start-counts.md)
- 修复 MegaMan 的 GyroAttack 旋转辅助弹、FireStorm 火圈、ChillSpike 初始弹／落地首击、OilSlider 燃烧油池、PharaohShot 头顶蓄力球和 TenguBlade 冲刺／斩击绕过每日随机友伤名单的问题，将各自的辅助伤害类型映射到对应复制武器
- 补齐关闭随机复制武器友伤时对 `GyroChopper` 和 `WheelCutterSaw` 的保护；保留 NapalmBomb 核爆原有的友伤行为

## 4.0.0-beta.261006

- 将以下敌人改为 coop 杂兵：
  - SpaceMetall
  - FireTelly
- 将 MegaMan 的 3、4 阶蓄力从多发改为单发；清理 MegaMan 四档洛克炮的重复射击分支和遗留 NoWeaponsBusterOnlyFinalFlag 标记，移除单发改动后失效的相对跳转
- 修复 BreakDash M2 和 CopyVision 洛克炮仍发射原版 10 点伤害子弹的问题，统一改用 100 点伤害的 MegaShotU；同时修复 BlackHole、TimeStopper、SkullBarrier 和 FlashStopper 的机器人洛克炮分支
- 新增 MegaMan 每次 M2 获取复制武器数量的服务器设置 `rz_sv_mega_m2_weapon_count`，支持直接输入正整数，默认由 6 把减少为 3 把；不足 6 把时随机选择不同槽，达到 6 把后尽量均分到六槽，余数随机分配，槽内武器不足时由其他槽补足，数量达到或超过武器池总数时发放全部武器；再次 M2 替换整套复制武器，保留基础 Buster，并补全 Pharaoh Roulette 对每槽多把武器的识别
- 移植 Razon 3 的挂机惩罚，支持着火、GUHU、Super GUHU、Money Bait、Money Bomb 及随机模式；新增服务器菜单设置 `rz_sv_noafk_item`／`rz_sv_noafk_delay`，默认关闭、延迟 60 秒，支持 30～300 秒
- 挂机检测计入按钮、视角和三个移动轴输入，原地转动视角搜敌不会被判为挂机；仅对正式回合中的存活真人玩家计时，死亡、复活及换机体后清零，惩罚前 10 秒警告
- 模组挂机惩罚与引擎 `sv_afk2spec` 同时开启时，每张地图提示服主一次；使用模组惩罚替代强制观战时需设置 `sv_afk2spec 0`，配置说明见 [挂机惩罚](docs/afk-penalties.md)
- 禁止 coop 杂兵因误伤而互相攻击，在共用 GenericRobot 基类中加入 NOINFIGHTING；保留攻击玩家及原有伤害
- 将 Razon 3 的 TopFiend 移植为 coop 杂兵，包含普通版及 3BC 弹跳陀螺变种，补齐攻击精灵与伤害归属，并恢复杂兵箱的 TopFiend 随机生成
- 为洛克人的复制武器增加皮肤豁免：NeedleMan 皮肤使用 Needle Cannon 不会被强制观战，DustMan 皮肤使用 Dust Crusher 不会变成 YustMan
- 修复 Slugger 变成 Boss 后仍保留手枪及武器箱枪械的问题，将这些武器接入共用变身清理注册表
- 更正 EyelentoMajor 的手榴弹投掷动画
- 加强 RedBaron 导弹爆炸：主爆炸伤害由 35～50 提升至 120～150，五次次级爆炸伤害由 35～50 提升至 80～120；两类爆炸半径由 50 扩大至 100，次级爆炸的随机生成距离由 0～32 扩大至 0～200
- Napalm Bomb 的核爆概率 1/32 -> 1/128
- 现在被冰墙类子弹杀死时会播放特殊音效
- 修复 GUHU、Super GUHU、Fortune Coin、OnFire 最终自燃和 Damocles 在被其他玩家攻击后致死时回退到通用 hazard 死亡提示的问题；为其他可自伤的道具、角色爆炸及其变体补充对应 HazardTag，提示保留最近攻击者的击杀归属，定义放在各自的 DECORATE 文件中；通用 Normal／Item 伤害继续使用默认提示
- 将 Dickhead 复活爆炸改为专用 `DickheadRevive` 伤害类型并添加对应 HazardTag；沿用原 Telefrag 保护倍率和死亡效果，保留 Eden Holy Mantle 对该伤害的排除规则
- 更正 SniperArmorShotU_Exile 的爆炸颜色
- 更正 TropicalMWS_W 的 Reload 图标

## 4.0.0-beta.261005

- 常规 LMS 中 Boss 胜利时，在设置 gameover 的同时立即移除 Boss 友伤保护，使存活 Boss 可在回合结束后互相伤害
- 调整 Atomic Fire 弹药条：WeaponCharge 30／40 档使用 Unbound 双色闪动，50 档使用 v7a 彩虹动画，横／竖 HUD 同步；拆分弹药特效与蓄力进度层，修复特效被覆盖的问题
- 将 MegaMan 的 Homing Sniper 随机池分类更新为 v6b 原版槽 4，Centaur Flash 更新为槽 7，同步更新 UIX 的 DTADD 武器注册，统一随机池、UIX 显示、数字键选择与滚轮切换的槽位；保留两把武器的每日随机固定 ID
- 修复 BlackHoleWepU 弹药条变灰期间仍自动回蓝的问题；灰条结束后恢复回蓝，期间不累计回蓝计时
- 参考 CBM Mega Man，使用蓄力值和客户端计时驱动 MegaManU_W 弹药条与 base 皮肤头像的蓄力闪烁，关闭 chargebar 设置时保留原有显示
- 修复 Commando Bomb 的 M2 导弹仍使用 v6b 原版 20 点直击伤害的问题，将直击基准伤害修正为 200 并接入每日伤害倍率
- 为 Slugger Flame Shot 的子火焰补充油池点燃，并使用 SluggerFire 伤害类型触发火焰死亡效果
- 削弱 Slugger Flame Shot：每个火焰由三次伤害改为一次，伤害从 15～35 降至 15～25
- Slugger 空投落地后直接显示抽中的武器字母图标，拾取时发放对应武器；抽取时机从拾取改为落地
- 将 Typhoon Bonus 移入与普通 FFA 相同的无额外人数门槛随机池；其余高人数 Bonus 使用 Unbound v7b 的 12 人门槛
- 修复 Typhoon Bonus 启动时误将事件编号 16 作为 Demoneye 机体编号、导致转换失效的问题，改为机体编号 13，并为全员 Demoneye 事件加入启动参数校验
- 修复 C-Section 的 M1 武器 HUD 在联机中等待服务器跳转后才开始播放的问题，为其提供可本地预测的直接开火入口，保留 Bob’s Rotten Head 投掷分支和原有动画、射击时序
- 补齐 Razon 3 Eden 已启用道具池中的 Holy Mantle、Soy Milk、The Bible、Guppy’s Head 和 Free Lemonade，接入共享道具注册表、HUD 图标及主动道具充能；Shiny Eden 的天使道具改为从注册池抽取 Holy Mantle／Godhead
- 修复 Eden 达摩克利斯之剑在远程客户端因库存跳转不执行而提前删除、导致头顶剑及线条特效无法持续显示的问题
- 清理 Unbound／CBM 遗留且未使用的 `CopyNerfGiver_P`、`WeaknessBase_P`、`BasicPain_SlamHit` actor 和 DecoyBot 的旧 `P_CheckOld` 状态，移除对四个缺失 ACS 脚本的调用
- 修复 Sutoka 鞭子命中时调用已改名的 `uc_istracerenemy` 导致 Unknown Script 报错、无法进入偷取判定的问题；排查其他 actor 并修复雷电爪挂点的缺失脚本调用，补回 Wonder Stone 的出现提示及联机客户端广播；Eyelento Major 的抓取改为直接调用当前 tracer 检查，避免旧接口告警
- 将 Bonus Stage 音乐接入与 Boss 音乐共用的加权曲池，通过 `AddBonusEventMusic`／`AddBonusEventMusicByStem` 注册曲目；MLG、Sumo、Kamikaze 和 Business eyes 在原曲与 Unbound 旧版曲目间等概率随机播放，音频由独立音乐包提供
- 修复 Boss Combo 静态基线检查遗漏已有音乐及曲名调整导致的误报，保留冻结基线并逐字段列出预期差异
- 为 CrowNest 的四种鸟炮台启用重力，使其生成后自然落地
- 修复 GBeast 的 EraseCross 在联机客户端错误进入 Claws 动画、导致 HUD 抖动的问题
- 将 Slugger 武器箱改为动态注册数据库，统一管理武器、抽取权重、语音和图标，并由共用逻辑清理旧武器、发放及切枪；保留原有抽取比例
- 还原并优化 Slugger（含 Shiny）的 DrawBar 与武器弹药显示
- 重做 Slugger 的副攻击（M2）：从手动投掷木箱改为定点呼叫空投，一段时间后空投箱从天而降砸向地面，落地引发爆炸范围伤害并生成武器箱补给
- 将 Slugger Shotgun 的武器 HUD 替换为 Razon 3 的素材与开火／换弹动画
- 为 Slugger 的手枪、重机枪、火箭筒和霰弹枪加入自动近战：首次按下 M1 时，瞄准线前方 48 单位内有敌人则使用不耗弹的刺刀
- 为 Slugger Rocket Launcher 加入轻微跟踪
- 移植 Razon 3 的 Slugger Flame Shot、Enemy Chaser、Drop Shot 和 Two Machine Guns，接入武器箱、弹药 HUD、武器语音及共用刺刀动作；保留原版弹药量、伤害和抽取比例，Enemy Chaser 使用强跟踪并按 Unholy 阵营规则重新搜敌
- 修复 BirdNest（Crow Nest）速射弹／散射弹命中时缺少伤害归属 actor，导致 `core_damageactor` 报错且归属伤害未生效的问题
- 修复 Floovy 大招保命触发后，开火打断受伤状态可能残留永久无敌的问题
- 修复 Floovy 普通 M1 命中敌人后，受伤状态提前发放脱体保护导致弹丸跳过摄像机生成、无法切换到脱体视角的问题
- 调整 Floovy 大招自身保命触发后的回血：立即回满当前最大 HP，不再按被标记敌人的剩余 HP 回血；包括 Pit 等环境伤害触发时，反杀目标仍为被标记敌人，并保留其无敌、护盾及额外生命等保命效果

## 4.0.0-beta.261004.hotfix1

- 修复 GBeast／FBeast 死亡爆炸动画中的 0 tic 循环导致联机客户端直接退出的问题，并修正两者共用的死亡闪白色表编号
- 修复 GBeast 在 Beast Out 状态下再次按 M2 取消 ChargeCross 冲刺后残留无敌的问题
- 修复 KFCDragon756 进入二阶段后颜色被恢复为一阶段的问题，将二阶段色表保存为持久武器颜色，并在再次进入 Ready 时恢复二阶段颜色

## 4.0.0-beta.261004

- 修复 Rogue 的 M1 三段拳击被 Survivor 保护归零的问题
- 将 Rogue 的三段拳击判定从 Radius 5／Height 5 扩大至 Radius 24／Height 32，提高连击命中容错
- 将 Rogue 连击踢击的范围从 80 扩大至 160，保留原有伤害及 80 的全伤害范围
- 为 CXAirMan 增加 M2 隐身叠加期间的持续吹风：第 1～5 层持续吹飞前方 512 距离、90° 扇形内的敌人，不穿墙、不影响队友、不造成伤害；第 6 层完全隐身或解除隐身时停止
- 修复 CXAirMan 的 Reload 在传送目标位于墙角时可能传送到地图外的问题
- 修复 CXAirMan 在第 6 次 M2 完全隐身后使用 Reload 会重复叠加隐身属性、导致永久隐身的问题
- 调整 CXAirMan 的 Reload 音效：起手和传送后现形各播放一次 `weapon/airshooter`，消除起手特效造成的重复叠音
- 调整 CXAirMan 的现形时序：`CXAirManTeleportFX` 最后一帧播放结束时才解除隐身或恢复 Alpha，避免旧特效误清除重新开启的隐身状态
- 为 CXAirMan 增加与 Misery 相同的常驻浮空能力
- CXAirMan 的 M1 子弹现在可以被打掉
- 将 Misery 与 CXAirMan 的浮空逻辑封装为共用控制器，统一高度限制、体力消耗及飞行状态管理，保留各自库存标记、HUD 和死亡／解除变身时的清理，原有数值不变
- 为 Nega Super Arm（含 Shiny）增加 5 秒抓取时限，到时自动投掷
- 为 RNC Clashman 的 Reload 隐身增加 5 秒时限，到时自动解除并进入原有冷却
- 修复超过 32 人时队友信息同步可能触发 ACS 执行超限并导致服务器报错的问题
- 修复 MosquitoEye 将持有 Survivor 保护的敌人误判为队友，导致无法抓住并吸血的问题
- 移除 Survivor 保护中的 EdenBomb 免伤，使 Eden 炸弹（含 Troll Bomb／Mega Troll Bomb）可伤害自己、队友及敌人
- 将 TimeStopperUFlag 上限从 560 调整为 2240，保持每 tic 恢复 1 点，使充满时间恢复为 Unbound 原版的 64 秒
- 修复 FFA 小游戏将敌人误判为队友，导致 Zangief 抓取／摔投不造成伤害、KickChamp 滑踢给予敌人免伤的问题（含 Shiny）
- 将 KamikazeEye 长按 M1 爆炸接入 v7a 版爆炸后回血：每 2 tic 恢复 2 点生命，总计 250 点
- 修复 GhostEye 事件隐身与 M2 隐身叠加时，事件隐身到期会提前解除仍有弹药的 M2 隐身的问题
- 调整 Spark Shock 等带冷却的复制武器：冷却期间暂停自动回蓝，冷却结束后恢复，期间不累计回蓝计时
- 移植 Razon 3 的 Death Shitting 机制到 Bonus Stage
- 新增 Bonus Stage Death Shitting 服务器开关（`uh_sv_bonusdeathshitting`），默认开启，可在 Server Options → Events 中调整，修改立即影响后续死亡；普通 Boss 回合不触发
- 移植 Razon 3 的 Bonus Event 胜者自选 Boss 机制：下一局倒计时提供 3 个普通 Boss 和 1 个稀有 Boss，通过左右移动／主攻击／副攻击选择；确认后进入单 Boss 回合，胜者优先成为所选 Boss
- 重做 MegaMan 每日复制武器随机：服主可分别设置普通武器、小神装和大神装的倍率区间，小／大神装独立开关，并可设置两档神装及友伤武器每日随机数量的 min／max；两档神装不重复，友伤名单独立抽选，同一天相同配置下结果固定，配置修改即时生效
- 移除 MegaMan 原先 40–60 倍及 80–120 倍超稀有神装档；默认普通倍率为 0.75–1.25，小神装每天 2–4 把、2–3 倍，大神装每天 0–1 把、4–6 倍，友伤武器每天 6–10 把（数量指整个官方武器池，不保证单个玩家获得）
- 新增 MegaMan Daily Weapons 服务器设置菜单，数值支持直接输入；关闭每日伤害随机时相关设置置灰，友伤数量由独立友伤开关控制；配置说明见 [MegaMan 每日武器](docs/megaman-daily-weapons.md)
- 更新 Napalm Bomb 的核爆特效

## 4.0.0-beta.261003

- 补全 Neru 的弹匣、技能及怒气进度条和 Rage／Wrath 层数显示
- 修复 Neru 子弹调用缺失的 `neru_countinv_acs` 导致报错刷屏、无法读取射手 Rage／Wrath 层数的问题，保留原有伤害数值
- 修复 Zangief Shiny 空摔后半段将方向值误作被抓玩家 ID 的迁移错误
- 修复 Zangief 抓住队友后再次 M1 只放下、不扔出的问题；普通版和 Shiny 版均补上与敌人相同的水平推力，保留队友免伤
- 修复 Shiny／True Power 攻击链误用普通版定义的问题，恢复已有强化数值：
  - Kate 刺击
  - RageUnit 高怒气爆发
  - HandyMan 下落攻击
  - Trickster 分裂弹
  - Igniter 碎片及死亡攻击
  - GloryGuster 漩涡及死亡旋风
  - Tristana 爆炸装药
  - HeavyBomber 子弹
  - TidalManiac 波浪及死亡水柱
  - PartyBomber 冲撞及死亡爆炸
  - Quickster 死亡弹
  - DecoyBot 摔投及死亡攻击
  - GreenElf／KickChamp／SumoWrestler 的 Bot 攻击
- 修复 Electrician Shiny 残留弹继承普通爆炸链时伤害未强化的问题，在最终爆炸 actor 按射手机体判定，普通版保持 100，Shiny 为 150（含 DecoyBot Shiny 复制武器）
- 修复 Kate／TidalManiac Shiny 的 Bot 选择普通武器、YellowWizard Shiny 的 Bot 尝试切换不存在的备用武器，以及 Nega Shiny SearchSnake 跳跃后回到普通子弹链的问题
- 修复普通 Juggernaut 冲刺误用 Shiny 版爆炸的问题：普通版恢复 200 基础伤害，Shiny 版保留 300
- 移植 HarpStrumm 幸运值系统；幸运值改用玩家类专属变量，预防共享变量冲突问题
- 将 Razon 3 的特有道具接入对应箱子池中
- 将 1UP LMS 事件改为发放一个 Dickhead
- 将 LMS 惩罚的提示、图标和效果迁移到动态数据库，统一由 `DefineLMSEvent` 定义普通／稀有／惩罚信息，并按事件编号整理奖励与惩罚注册；新增 addon 接口与示例，用法见 [LMS Event API](docs/lms-event-api.md)
- 将 Deadly Firearms 的 assist 图标替换为 v7a 版本
- 修复 Cobe 变身后未装配武器、无法攻击的问题
- 调整 Cobe 武器条：使用 M1 掷出斧头后才填满，斧头返回或收回后清空，与 Unbound 原版一致
- 优化 Cobe 的武器条特效
- Cobe 攻击和嘲讽语音现在会随机播放四种语言的 dadadadada
- 修复在线 Boss 对决的名称与 VS 图标显示
- 修复 Clownpiece 符卡名称、奖励状态及倒计时在联机客户端不显示的问题，并修正阶段切换后的计时器重启和中途加入同步
- 补全以下机体的 Reload 图标定义
  - BlackDevilEye
  - ThomasTheTrain
  - Magnetismo
  - Elitist Sue
  - MakeAGoodZero 二阶段武器
  - TorontoCalifornia
- 修复 LMS 惩罚自动触发 Super GUHU 后，因玩家未持有普通道具而在倒计时结束时计算出零爆炸伤害的问题；自动触发至少按一份道具计算，保留正常道具的叠加伤害倍率
- 移除 X-Ray 剩两人时的 30 秒限制
- 移除 Clownpiece 的后面两个非符阶段
- 修复 BlueElephant 击杀没有跳脸的问题，补全相关音效
- 将 Nega 其余复制武器共用的 Mega 伤害类型改为专用类型（含 Shiny、Search Snake 和 Chill Shot 的继承类型），补齐队友保护及受伤／死亡映射，移除每日随机友伤
- 弹簧眼的存活时间 61 -> 600
- Misery 的移动速度 1.2 -> 1.0

## 4.0.0-beta.261002

- 优化 RedeadGuts_W_Pissed（复活暴怒阶段）的奔跑与爬墙 HUD 动画表现，按住 M1 时交替展示攀爬抓扒动作
- 修复 PlasmaSpark 满能量护盾在远端客户端提前消失的问题
- 修复 Scrotoman 开大下车后无敌的问题
- 修复 Scrotoman 开大没有切换开车贴图的问题
- 补全 Scrotoman 的开大音效
- 优化 Scrotoman M2：现在可以举盾冲刺，并优化 Sprite 和武器 HUD 动画
- 为 Nega Napalm Bomb、Needle Cannon 和 Ice Wave（含 Shiny）使用独立伤害类型，移除每日随机友伤
- 补全 Pharaohman4MI 的 Unknown 诅咒
- 修复 NegaMan_W 和 Shiny NegaMan 在横屏模式下 M2 蓝条缺失的问题
- 调整 Shiny NegaMan 的骷髅盾：未蓄力／中蓄力激活后再次按 M1 可立即中断；满蓄力释放期间不再允许 M1 中断，完整释放后切换至下一武器
- 修复两个 Astromancer 的 M1 护盾缺失持续接触伤害的问题
- 修复 Handyman（含 Shiny）M2 后下落时无法按 M1 向上推进的问题
- 补全 Shiny NegaMan 蓄力切换的所有武器 Tag 定义
- 优化 X-Ray 视觉体验：视线无遮挡且敌人完全可见时自动隐藏提示，避免遮挡准星与目标；透视信息改为基于敌方头顶 3D 坐标定位并启用半透明渲染，解决近距离直视遮挡模型容易马枪的问题
- 补全 Berserker 的死亡和受伤音效，以及 WarRockStelar 和 MeguhMang 的死亡音效
- 恢复 TimemanC 和 KFCDragon756 转阶段时的头像切换，统一更新 Boss 血条框、UIX 队友栏、计分板及横／竖 HUD 的 ScoreIcon；支持联机阶段同步、中途加入及死亡头像保留
- 新增阶段头像注册接口 `DefineTeamPhasePresentation`，供其他 Boss／addon 扩展；用法见 [Boss 阶段头像](docs/boss-phase-portraits.md)
- 更新 Misery 的皮肤（by Soundwave）
- 更新 Misery 的武器 HUD，优化攻击动画

## 4.0.0-beta.261001

- 修复 Redead Gutsman 二阶段未自动扣血的问题
- 将 Boss Combo 的阵容、人数限制、权重及音乐配置迁移到运行时注册表，新增 addon 注册与查询 API，支持固定阵容和候选池；用法见 [Boss Combo API](docs/boss-combo-api.md)
- 修复 Three Destrons 播放错误音乐的问题，改为沿用 Destron 的登场音乐
- 将 Final Speciman 和 Speciman DX 加入 Speciman Rush 候选池，从八种成员中选出五个 Boss
- 调整 Shadow Tricks Duel：假身份首次变身后即可移动、攻击，并显示 Boss VS 名称、头像和血量；真实身份沿用普通 Shadow 的稀有度权重及历史出场次数抽选，保留双方目标不同的限制
- Shadow 假 Boss 在揭露身份前死亡时取消换身，remorph 前再次检查存活状态，避免重新生成已死亡的 Boss
- 将 Misery 的多段空中跳跃改为常驻悬浮：离地达到 160 时关闭飞行，降至 152 后恢复；危险坑上按 CBM Alien 规则消耗悬浮耐力，耗尽后下落，离开危险坑后恢复
- KickChamp 的 Ammo 上限 200 -> 300
- 修复 Destron 击杀玩家时死亡音效缺失的问题
- 新增 Destron 的受伤音效
- 修复 BlackDevileye 的弹体异常的问题
- 补齐 classbase 缺失的冰系／火系伤害死亡映射，触发对应冰冻／燃烧死亡效果；保留已有特殊死亡定义，MakeAGoodZero 暂不调整；共用伤害类型的其他攻击也使用对应效果
- 补齐冰／火攻击的场景交互
- 恢复 Unbound 的 Boss／恶魔眼 True Power 效果：有怒气条时只补满怒气；无怒气条时增加最大血量并回血 2000，可重复使用
- 修复 Eden 在线游戏中道具图标不显示的问题
- 补充 Eden 泪弹的 +FORCEXYBILLBOARD 属性
- 移除 ShinNegaman 的 Reload 的调试功能
- 优化 ShinNegaman 的攻击 HUD 动画与音效表现
- 优化 ShinNegaman 的 Obituary 文案
- 为 ShinNegaman 的 Nega Astro Wave 与 Nega Flame Sword 补充 SpreadRune 兼容
- 恢复 Miu W1 M2（含 Shiny）的 Unbound 连续冲刺：停顿期间可再次按 M2 转向冲刺，普通状态满能量可连续三次；修复连续激活造成属性层数累积，并补齐无重力及切武器／死亡／Shiny 变身清理
- 优化 Miu 的部分 HUD
- Nega Super Arm（含 Shiny）现在可以抓取队友
- 修复变成 MosquitoDemoneye 瞬间执行特定操作会使游戏崩溃的问题
- 修复 DecoyBot 的警告刷屏
- 修复 Dawnbreaker 普通弹绕过友伤随机池、关闭随机友伤后仍能伤害队友的问题；普通弹与蓄力攻击统一按当日随机池判定友伤
- 补齐 Dawnbreaker 的 BlastRuneB／D／M 直接命中伤害，统一与 BlastRuneA 使用基础伤害 50 及每日伤害倍率

## 4.0.0-beta.260930
- 修复 Misery reload 后未满蓝期间客户端可连续 M2 的问题
- 修复 Misery 的 reload 联机时只出现传送特效的问题
- 修复准备阶段显示 “A powerful foe approaches!” 提示时未同步播放音效的问题
- 修复仅剩两名玩家时及 Lin 半血触发的 X-ray 在线游戏中不显示的问题
- 按 Unbound 原版逻辑修复 Balrog 抓人后的速度恢复：抓取成功时解除冲刺减速，投掷与摔地共用清理流程，避免摔人后残留速度效果导致持续减速
- 恢复 Balrog M2 摔地对幸存者的 root 效果（80 tic）：修复共用定身 watcher 误要求受击者为变身 Boss 而立即退出的问题，保留死亡、掉线及 Boss 解除变身时的清理
- 统一玩家指针有效性检查：`uh_PointerExists` 支持普通玩家／真实变身两种检查模式，保留旧接口兼容；Boss 效果解除变身后仍按原检查要求停止
- 修复 Trickster（含 Shiny）M2 隐身时第一人称武器未渐隐的问题；共用渐变使用独立 AlphaPower，并补全重叠取消、切武器、死亡及变身／解除变身时的清理，避免透明效果残留或影响其他技能；TricksterGiovanni 同步接入
- 修复 CaptainAssShiny、HandyManShiny、SmokeBanditShiny、TidalManiacShiny 死亡时跳转到旧状态标签，导致 `left without a state` 报错的问题
- 补齐 Shiny 机体缺少的 NOMORPHLIMITATIONS，统一变身后的移动、受伤音效及头像行为
- 修复 HomingSeeker 等机体使用 TruePower 后 HUD 仍显示普通头像的问题；Shiny 静态头像改由 presentation 绘制，保留磁极头像叠层
- 补全 Shiny 形态的头像登记，修复变身后计分板仍显示原头像及 UIX 队友栏头像为空的问题；保留 MegaManShiny 的皮肤回退和 EdenShiny 的继承头像
- 补全 PlainDevilDemoneye、RichDevilDemoneye、ProtoManBadGuy、WeakHorse 的队友栏／计分板头像登记
- 补全 TyphoonDemoneye、BrickDemoneye、MosquitoDemoneye 的 HUD 头像（ScoreIcon）
- 修复 Boss／LMS 音乐被客户端监听器重复请求播放、未加载音乐包时同一曲目提示两次 `Music "xxx" not found` 的问题；保留音乐模式切换及中途加入时的地图音乐覆盖
- 补全 Berserker、SoccerRock、Floovy、SakikoTogawa、MakeAGoodZero、BlueElephant 的 HUD 头像（ScoreIcon）
- 修复横版、竖版 HUD 在 Boss／恶魔眼及使用独立头像的幸存者头像背后仍绘制 Maestro 的问题；保留 MegaMan 的默认头像与皮肤回退
- 修复 DecoyBot（含 Shiny）在线游戏中攻击 HUD 卡在待机帧、无法播放攻击动画的问题
- 优化 DecoyBot 复制 CloseCombatUnit 的攻击动画
- 补全 ShinNegaman 的 ReloadIcon
- 优化 ShinNegaman 的 CopyAttack1（Nega Rolling Cutter）武器与弹道表现
- 修复 MeisterWahwee 一阶段 M2 跳转到不存在的状态而报错的问题
- 修复 Sampi 无法使用 Reload 技能的问题
- 更新 Sampi 的 Reload 图标
- 移植 Berserker 的 Diehard 技能，并改为血量降至 35% 及以下时自动触发持续回血（单条生命周期限触发一次）
- 调整 GBeast 的蓝耗：Heat、Elec 每次消耗整条蓝（100），Slash（W4）每次消耗半条蓝（50）
- GBeast、FBeast 的武器切换音统一改为 MMBN 光标音效
- GBeast 的 Erase 改为每次 M2 发射一颗、每颗消耗 10 蓝，按住 M2 可按原射速连射；暴怒阶段连续发射满 10 颗后追加结尾光束，松开 M2 或切换武器重置计数
- GBeast 的 Heat、Elec 在蓝未满时屏蔽 M2，修复按住 M2 导致无法回蓝的问题
- FBeast 的 Aqua 激活后松开再按 M2 可提前取消
- 调整 FBeast 的蓝耗：Tomahawk、Ground 每次消耗半条蓝（50），Tengu、Dust 每次消耗整条蓝（100）；蓝不足时屏蔽对应 M2，避免按住导致无法回蓝
- 补全 FBeast 的二段跳振翅音效，统一通过现有 `*airjump` 机制播放
- 重构 `core_weaponcolor`，分离声音播放与染色处理；`core_chargecolor` 直接复用染色函数

## 4.0.0-beta.260929
- 修复在线游戏中部分 Boss 的 Ready 重入问题
- 移除 TimeStopper 的调试用效果
- 修复 DecoyBot 变成恶魔眼武器不收回的问题
- 取消通用受伤状态的默认减速
- 恢复幸存者开局及重生时的 Unholy 道具友伤保护（ProtectUnholyItem），修复队友道具造成全额友伤的问题
- 调整文本版（非 UIX）队友信息的绘制层级，使其被 SBARINFO 状态栏覆盖
- 恢复 NegaBlackHoleBomb 各子弹变体的配色
- 更正台风眼的配色
- 修复砖块眼的配色对应关系
- 更正台风眼和蚊子眼的武器名
- Zangief（含 Shiny）现在可以抱摔队友；抱摔队友保留动作、位移和特效，不造成抓取或落地伤害，也不会移除队友的保护效果
- 恢复 KickChamp（含 Shiny）地面滑铲的击飞效果；踢中队友只击飞、不造成伤害
- 优化 LMS 事件 12（ChanceBox）的横幅文本
- Skullman4MI 普通及暴怒形态在 M2 持盾期间按 M1 丢盾时统一消耗 100 ammo；暴怒形态也需满弹药才能发动 M2，限制连续丢盾
- 修复并校对部分组合 Boss 及特殊对决事件的 BGM 与曲目元数据
- 血量更改：
  - BalladeGB 3000+400n -> 10+1n
  - Sampi 4000+350n -> 30000
  - Pharaohman4MI 2500+245n -> 3500+295n
  - TimemanC 2539+500n -> 4010+724n

## 4.0.0-beta.260928.hotfix1
- 修复 `Out of bounds memory access in ACS VM` 报错问题

## 4.0.0-beta.260928
- initial release
