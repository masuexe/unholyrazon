## 4.0.0-beta.260930
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
