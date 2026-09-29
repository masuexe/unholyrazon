## 4.0.0-beta.260929
- 修复在线游戏中部分 Boss 的 Ready 重入问题
- 移除 TimeStopper 的调试用效果
- 修复 DecoyBot 变成恶魔眼武器不收回的问题
- 取消通用受伤状态的默认减速
- 调整文本版（非 UIX）队友信息的绘制层级，使其被 SBARINFO 状态栏覆盖
- 恢复 NegaBlackHoleBomb 各子弹变体的配色
- 更正台风眼的配色
- 修复砖块眼的配色对应关系
- 更正台风眼和蚊子眼的武器名
- Zangief（含 Shiny）现在可以抱摔队友；抱摔队友保留动作、位移和特效，不造成抓取或落地伤害，也不会移除队友的保护效果
- 恢复 KickChamp（含 Shiny）地面滑铲的击飞效果；踢中队友只击飞、不造成伤害
- 优化 LMS 事件 12（ChanceBox）的横幅文本
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
