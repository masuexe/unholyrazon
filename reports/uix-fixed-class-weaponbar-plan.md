# UIX v3bh 固定 class weaponbar 兼容计划

## 执行状态

代码已实现，运行验收阻塞；本计划按“游戏内与联机回归通过后删除”的条件保留。

后续槽位提示改动：按用户要求启用真实 slot 绑定提示，取代初版的“不显示标注”策略。注册行显式记录与 DECORATE `player.weaponslot` 一致的 slot；非 NET 只读 `uh_fb_slot` 返回元数据，绘制序号仍只用于布局。UH 与原版共用 `weaponBarSlotHint`，使用 `StrParam(k:slotBinds[slot])`、原版位置/缩放/对齐及 `UIX_CL_WEAPBARSHOWSLOTS`；当前装备金色，其余深灰。未持有武器不显示标签，非法 slot 不索引绑定表。为保持统一注册函数签名，Archivist 也补齐 slot 元数据，但未启用其 bar。

本次增量验证：native ACC 全量编译通过，输出 `/tmp/uh-slot-hints-k09Ef8`；24 行 slot 全部与 DECORATE 对照通过，`git diff --check` 通过。本次未重新打包或启动引擎，现有 `out/build.pk3` 仍是此前不带绑定提示的版本；改键、SHOWSLOTS 开关、颜色与观战显示仍待运行验收。

运行验证记录（槽位提示增量）：第一轮实机测试“图标显示但无数字”的原因是当时的 `out/build.pk3` 未包含新编译的 `UIXWEAP.o`（缺 `uh_fb_slot` 字节码），重新编译打包后解决。临时调试打印 `UHFB draw n=4 showSlots=1 slots=123400`（直连引擎，Arcanist）确认绘制路径与 1–4 槽位元数据正确，随后已移除打印并重打包；数字标签已由用户实机确认显示。MCP `launch_instance` 连续三次在同一 bridge 建立前 SIGSEGV（引擎日志仅到 `Gameinfo scan`），改为直接 shell 启动完成验证；bridge 本身的环境问题未进一步追查。

- `uh_uixfw_bar.acs` 提供非 NET、同步只读的 `uh_fb_count` / `uh_fb_string`；`uh_uixbar_api.acs` 定义共享协议。精确 class 匹配，区分不支持与 OPEN 未就绪，字符串通过 `StrParam` 返回动态字符串。
- `uixweap_fixedbar.acs` 每次从当前摄像机重新扫描持有和装备状态；复用 `uixweap.acs` 抽出的布局、背景、图标助手。四类均接入同一注册表，无弹药、槽位绑定标注、ROWMAX 截断或 wheel 状态写入。
- native Linux ACC 执行 `tools/compile-acs.sh /tmp/uh-fixedbar-pxqnCE` 全量成功；日志在该临时目录的 `compile.log`。`git diff --check` 通过。
- 静态比较确认设置/布局计算原样保留，原 `updateSlotData` 和 weapon wheel 实现未变；核对原版坐标公式等价及四类 4/4/6/6 注册行数。此检查不是游戏运行验证。
- 编译产物已复制到 `src/acs/`，重新打包 `out/build.pk3`；现有 PK3 验证器通过（16592 entries）。未修改参考树、LOADACS、DTADD 或 weapon actor。
- 尝试一次 `mm8bdm-v6b-uix` 最小客户端启动，以 Arcanist 开局、不打开 wheel。bridge 端口未建立，进程 SIGSEGV；日志仅到 `M_LoadDefaults` / `Gameinfo scan`。没有获得实际 HUD 结果，也不能据此证明崩溃与改动无关。停止重复启动，未修改引擎环境。
- **待验收**：四类实际图标/高亮，方向/镜像/缩放/layer/开关，少量持有及死亡重生，观战切换，MegaMan M2 回归，各类 wheel 操作隔离，以及无 UIX 加载与联机行为。

以下保留原始计划；其中“本轮仅写计划”的文字描述的是计划制定阶段，不是本次执行结果。

## 工程量与范围

评估为中等改动，先写计划，不直接修改游戏代码。UIX weaponbar 目前依赖 8BDT 索引、武器 slot 和弹药表，而固定武器轮使用 UH 独立注册表。保持同一份武器定义、复用 UIX 设置和绘制、避免污染原版轮盘，需要增加只读数据桥并调整 weaponbar 的数据入口，不只是补几行 DefineWeapon。

首期支持 Arcanist、ArcanistShiny、RedWarrior、YellowWizard。MegaManU 保持现状，作为回归基线。Archivist、Qwant、NegaMan 后续接入；killfeed 不在本次范围。

## 已确认的接口

- `src/acs_source/compat/mods/uix/uh_uixfw_db.acs` 已保存固定 class 的 actor、图标、标签、弹药及顺序，应成为唯一注册来源。
- `uixweap.acs` 的 `UIX_WeapBar(cam, cpn, cv)` 以摄像机 actor 为 activator，以 cpn 读取观看者设置，然后调用 `updateSlotData`，按 UIX slot 绘制。
- 该 `updateSlotData` 同时服务原版武器轮。不能把 UH 固定 class 的 bar 数据直接塞进其共享 slotVals，导致原版 wheel 路由与显示改变。
- `uh_uixfw` 已在 LOADACS，vendored `UIXWEAP.o` 由 UIX 加载，不需新增 LOADACS 条目。

不能把“仅 MegaMan 显示”推广为所有缺失显示均已排除其他原因；首期实现仍需检查 UIX_NoWeaponBar、开关和当前摄像机状态。

## 显示行为

- 沿用 UIX weaponbar 的开关、alpha、位置、缩放、方向、镜像及 HUD layer 设置，不另写常驻显示循环。
- 这些 class 的每个实际持有武器显示一个 icon，保持固定注册顺序，当前装备武器使用 UIX 当前武器突出显示效果。
- 不显示主/副弹药条，避免重复共享能量；正常游戏 HUD 不变。
- 布局采用每个武器一个显示槽位，顺序编号仅用于布局。不得将其作为新的 gameplay weapon slot。
- 不显示虚构的槽位按键提示。按后续需求，SHOWSLOTS 展示注册元数据中的真实 slot 绑定，绝不从布局序号推导 gameplay slot；不改变键位。
- 已核对真实槽位：Arcanist／ArcanistShiny 为 1～4，RedWarrior、YellowWizard 为 1～6。提示使用实际键位绑定，而非硬编码这些数字；当前装备金色，其余深灰，沿用 UIX 标签位置、缩放和对齐，不新增设置。
- 四个或六个图标无需组内堆叠或 overflow；ROWMAX 不用于截断这条单武器槽位显示。保留原版设置本身，不增加新开关。
- 玩家持有数量为 1～2 时仍可显示 bar，不能复用 wheel 的至少三件开启条件。
- 对观战摄像机显示被观看玩家的武器与高亮，设置采用观看者的 cpn；不能总读取 ConsolePlayer 的库存。

## 实施方式

### 1. 只读定义桥

在 `uh_uixfw` 内增加窄范围 named-script 访问器或只读 API：根据当前 activator 的精确 class 判断是否支持，并提供定义数量、每行 actor/icon 等。UIXWEAP 通过同步查询读取，不额外复制注册列表。

访问器不标记 NET，不接收客户端写入，不改变 wheel 快照、owner、route、选择状态或计时器。不要为了画 bar 调用 OpenWheel、SnapClear、CollectFixed、QwantTryCommit 等有状态方法。

注册 OPEN 初始化尚未完成时返回未就绪，不缓存为永久“不支持”。未知 class 返回原版路径；已知且暂未就绪的 class 暂不绘制 UH bar，下一次正常 HUD 调用重试。跨库字符串返回应遵循引擎已有动态字符串方式，并用 native ACC 验证。

### 2. weaponbar 独立数据入口

在现有 `UIX_WeapBar` 保留所有开关和禁用检查后，识别上述四种 class。已支持时读取定义、检查实际持有与 CheckWeapon，调用共享布局/图标绘制助手并结束；其他 class 继续原版流程。

UH 数据使用独立的小型局部/显示缓存，不占用原版 slotVals、carriedWeapons、lastUpdated。若缓存，与摄像机身份绑定；同一 tic 切换摄像机也不能读到上一个玩家的数据。简单扫描最多六行足够，首期不需要按 Timer 全局缓存。

### 3. 复用绘制而非复制整段 UIX

把 UIX 现有 cv 设置和布局计算整理为可共用助手，保留原版绘制坐标与固定点运算。UH 分支只负责数据和无弹药策略；复用 displayIcon、背景图标及当前武器偏移，不重写底层 HUD 绘制系统。

注意原版调用 SetActivator(-1) 后才绘制；UH 也必须在释放 activator 前完成持有检查和当前武器识别。跨库查询必须保持摄像机 activator，不留临时切换。

保持 UIX 镜像、方向、缩放的布局语义一致，但当前武器高亮不得旋转整个注册顺序。未持有武器不绘制，可保留原定义的显示槽位坐标以维持位置记忆；不因持有减少重新排序。

### 3a. 槽位绑定提示增量

复用已实现的真实 slot 元数据、非 NET 只读 `uh_fb_slot` 与共用 `weaponBarSlotHint`。此增量不重做已完成的图标 bar，不新增 DTADD 注册、alias、按键或 CVAR。

- 在释放摄像机 activator 前读取实际持有、当前装备及真实 slot；不能为了标签调用原版 `updateSlotData`。
- 标签位置由展示槽位的基础坐标加原版 `slotX/slotY` 计算，标签内容由真实 gameplay slot 的 `slotBinds` 格式化。两种 slot 职责分离，不把选中 icon 的偏移加到标签位置。
- 根据实际绑定表长度校验 slot；缺失或非法元数据仅省略标签，不隐藏 icon，也不访问越界。
- 不绘制未持有武器的标签，不因缺少武器重排其他位置；原版与固定 class 共用标签助手，保持 MegaMan 原版行为。

### 4. 保持原功能隔离

不新增上述武器的 DTADD gameplay 注册，不修改武器 actor 的槽位或弹药定义，不修改轮盘操作。若确需注册显示身份，须证明不影响原版 wheel；首选独立只读桥，避免这一额外副作用。

在 UIXWEAP 文件头更新 vendored 修改说明，注明固定 class bar 分支。新增实现片段仍位于 `compat/mods/uix/`；如调整 include，只更新现有编译入口需要的搜索路径，不新建构建工具。

## 最小实验与顺序

1. 先实现 Arcanist 单 class：四个 icon、正确顺序和当前高亮，无弹药条；轮盘关闭或从未打开也能显示。
2. 验证方向、镜像、位置、alpha、缩放及被观看玩家的数据读取。
3. 接入 ArcanistShiny、RedWarrior、YellowWizard，完全复用同一数据桥，不另抄注册表。
4. 全量 ACS 编译后，实际游戏内与联机回归；通过后删除本计划。

## 验收

- 四种 class 的 bar 独立于 wheel 是否打开，四/六个图标完整，无共享能量条，切武器高亮正确。
- 只持有一两件、失去武器、死亡、重生、换 class、未知装备武器不越界或残留错误高亮。
- 观战切换多个同 class/不同 class 玩家时不串数据；使用观看者设置。
- UIX 服务端开关、alpha=0、UIX_NoWeaponBar、方向/镜像/缩放/layer 均正常。
- SHOWSLOTS 开启时显示真实绑定提示，关闭时仅显示图标；重绑 `slot 1` 等命令后文字同步变化，默认键位下与原版数字提示风格一致。（已验证：默认键位下 Arcanist 显示 1–4 数字标签，金色高亮当前武器；改键同步与关闭开关仍待复验。）
- 当前武器标签金色，其余深灰；无效 slot 安全省略标签；观战时显示被观看玩家的槽位映射与观看者的键位提示。
- MegaManU 开局主武器、M2 获取/替换六件特武、弹药与颜色显示保持原状。
- 固定 wheel、Qwant wheel、NegaMan wheel、item wheel 不被 bar 调用修改状态。
- UIX 未加载不出现新增循环、缺失脚本调用或 HUD；保持既定加载顺序。
- 使用现有 `tools/compile-acs.sh` 全量编译至临时目录。本轮仅写计划，不编译、打包或启动引擎。

本计划依照 MM8BDM 和 Zandronum 技能及项目源码制定，技能核对促使数据入口与轮盘状态隔离；不修改只读参考树。
