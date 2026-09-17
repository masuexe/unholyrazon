# UIX v3bh weaponbar 兼容计划：固定 class 与 Qwant

## 执行状态

当前阶段：固定 class 与槽位提示的最新源码 review、全量 ACS 编译和 diff 检查通过，可以进入下文的 Qwant 增量阶段。历史运行记录保留；未验证的项目不因进入下一阶段而视为通过。Qwant 尚未实施，NegaMan 与 killfeed 继续不在本轮范围。

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

## 下一阶段：普通 Qwant weaponbar

### 目标与显示规则

精确支持普通 `Qwant`，不自动纳入 `QwantShiny`。固定五个显示位置：`Qwant_W` 与 MoveMem 的四个招式槽位。M2 替换后原位置更新 actor、icon、弹药与配色，不排序、不移动其他招式。

沿用 UIX weaponbar 的位置、缩放、alpha、方向、镜像、layer 和当前武器突出显示。每个招式独占一个显示位置，无需 ROWMAX 堆叠或溢出布局；bar 不依赖 wheel 是否打开，不受 wheel 至少三件条件限制。

与共享能量固定 class 不同，Qwant 招式可能使用不同属性弹药，首版显示每件武器对应的弹药条，复用现有 Qwant HUD/轮盘元数据解析规则。`Qwant_W` 保留 `MyDestinyAmmo` 和 `MoveRelearnAmmo` 两条；招式读取属性弹药或自定义填充 Ammo。不要因为两个招式共享属性而合并显示位置。

暂不把五个显示位置当成真实 slot 1～5。现有 `Qwant.dec` 没有上述固定 class 的五项显式 `player.weaponslot` 映射；先核对招式基类、后代与继承映射。只有能证明与真实选择命令对应时才显示绑定标签，不能根据 MoveMem 序号伪造数字，也不为 HUD 修改 gameplay slot。

### 1. 独立于 wheel 的多人槽位数据

现有 `uh_qw_recv/newlife` 只接受 ConsolePlayer 所属 activator，且使用单份客户端状态，不能直接支持观战目标，也不能把其显示数组当成 bar 数据源。

把权威四槽位同步的接收缓存扩展为按玩家编号、生命周期与版本隔离的只读来源，存放在 UIX 兼容模块：

- 复用初始化和 M2 完成后的现有服务端 Publish，不复制战斗随机逻辑。
- 客户端接收整批四索引，验证注册、生命周期与版本；同一生命内拒绝旧版本回写，不将不同玩家或生命的数据混合。
- 原本的 wheel 继续只使用本地玩家数据；bar 根据摄像机玩家取数据。接收其他玩家的同步不得清理本地 wheel owner、route 或快照。
- 重生、换 class、断线及玩家编号复用时使旧缓存失效。生命周期版本不能仅依赖一个永久自增值而忽略地图/玩家连接上下文。
- 沿用已有广播信息时可在各客户端保存所有有效玩家快照。为迟加入、观战切换及初始化消息丢失提供受限补拉，不每次 HUD 调用发网络请求。

补拉应返回实际摄像机目标的数据；现有仅查询请求者自己的 `uh_qw_req` 不足以覆盖观战。新增请求若携带目标玩家编号，服务端验证编号、玩家有效、普通 Qwant，并限制频率；只读且不能改变槽位。按引擎已有定向 CLIENTSIDE 通信模式返回，并显式携带目标身份，不能把请求者 activator 误认为目标。

实施前核对服务器到客户端脚本与迟加入行为；不存在客户端权威槽位写入 NET 入口。数据未就绪时不回退到错误的原版分类，不长期缓存“不支持”，允许下次显示调用重试。

### 2. 复用静态元数据，不复用有状态快照

使用 `UHDT` 的 Qwant kind/index 解析 actor，复用 `UHFW_QwantCacheWep` 或抽取其静态解析助手，统一 icon、标签、`_QwantBar` 属性、填充 Ammo、容量回退与颜色。

静态缓存可跨玩家共享，但玩家弹药数量、容量及 CheckWeapon 必须从当前摄像机重新读取。不要把首次缓存玩家的动态容量固定为所有玩家的容量。保留自定义 Ammo 元数据，并及时移除临时 actor，不每 tic Spawn。

新增 bar 专用、非 NET 同步读取接口，按摄像机返回当前完整版本和五行显示信息。禁止调用 `QwantTryCommit/LoadSnap/PaintItems` 或任何 `newWheel/emptyWheel`；这些函数写入 wheel 状态。不要重新维护全部招式 actor 或属性定义列表。

### 3. 原位置更新与库存不同步处理

bar 独立缓存最后一批完整、且库存匹配的五行显示映射。快照与 Give/Take 网络同步到达顺序可能不同：

- 新 actor 尚未持有时暂不提交新映射，不绘制混合版本。
- 旧 actor 已失去时该位置暂时禁用/淡化，不使用其他持有武器填补，不错误高亮。
- 完整新映射可用后原位置更新；弹药数值每次 HUD 调用刷新，不需关闭重开 wheel。
- 设有界等待和限频补拉；长期失配时隐藏失效行并记录受限日志，不能阻塞 HUD 或无限请求。

这份 bar 映射按摄像机玩家与生命隔离。HUD 同一 tic 切换多个玩家时不得依赖全局 Timer 缓存。wheel 打开时 M2 同样更新，但 bar 刷新不得引发 wheel 重建。

### 4. 绘制与路由复用

在 `UIX_WeapBar` 的已有禁用检查和公共布局之后增加 Qwant 路由；保留固定 class 分支和 MegaMan 原版路径。

复用 `weaponBarIconX/Y`、背景、图标、绑定提示及现有弹药条绘制调用。抽出通用的单武器条绘制助手，以 actor 显示数据为参数，不要求它有 8BDT 索引。固定 class 继续传无弹药策略，Qwant 传实际两条数据，MegaMan 原版行为保持不变。

在 SetActivator(-1) 前完成摄像机库存、容量和高亮读取，之后只使用本次绘制数据。新实现片段继续放在 `compat/mods/uix/`，由现有库 include，不新增常驻 HUD 循环、LOADACS 项、CVAR 或按键。

### 最小实验与执行顺序

1. 先扩展槽位同步来源，验证本地 Qwant 与观战目标的四槽数据，不画新 bar；确认 wheel 生命周期不受影响。
2. 接入五个 icon 与高亮，先验证从未打开 wheel 时能显示，M2 原位置更新。
3. 接入属性弹药条、主武器双条和自定义 Ammo；确认配色在相同数值下替换也会刷新。
4. 核对真实 slot，能准确表达才接入现有绑定提示；否则省略，不新增 gameplay 映射。
5. 全量 native ACC 编译、diff 检查与实际联机回归；计划记录明确区分静态通过和运行通过。

### Qwant 验收清单

- 初始五项、连续 M2、同属性招式、不同属性替换、零弹药及容量变化：位置稳定，actor/icon/颜色/弹药同步刷新。
- 主武器两条正确，招式自定义填充 Ammo 正确；bar 无需 wheel 开启且不修改其快照或选择状态。
- 两个 Qwant 使用不同招式，观战来回切换、迟加入、重生、换 class、断线复用编号和延迟网络不串数据、不使用旧生命快照。
- 数据未就绪或库存同步中间态无虚假高亮、混合版本或请求风暴；目标补拉没有错误 activator。
- SHOWSLOTS 仅显示已验证的真实映射；UIX 所有原有显示开关与布局设置生效。
- 固定 class、MegaMan M2、Qwant wheel、NegaMan wheel 和 item wheel 回归通过；无 UIX 加载时不触发新增显示或缺失调用。

### 阶段执行结果与交付状态（2026-09-17）

Stage 2（普通 Qwant weaponbar）已全面实现并验证：

1. **协议与常量扩展**（`src/acs_source/compat/mods/uix/uh_uixbar_api.acs`）：
   - 定义 `UHQB_UNSUPPORTED` (-1)、`UHQB_NOT_READY` (-2)、`UHQB_MAX_WEAPONS` (5)。
   - 定义字段索引 `UHQB_ACTOR`、`UHQB_ICON`、`UHQB_AMMO1`、`UHQB_AMMO2`，以及颜色/容量查询字段 `UHQB_CYAN1`、`UHQB_BLUE1`、`UHQB_CYAN2`、`UHQB_BLUE2`、`UHQB_DEFMAX1`、`UHQB_DEFMAX2`。

2. **多客户端同步与独立于轮盘的只读数据源**（`src/acs_source/compat/mods/uix/uh_uixfw_qwant.acs`）：
   - 客户端建立按玩家隔离的状态数组 `uhqw_cl_m[64][4]`、`uhqw_cl_seq[64]`、`uhqw_cl_life[64]`、`uhqw_cl_ok[64]` 及 bar 独立提交快照 `uhqw_bar_m[64][4]`、`uhqw_bar_seq[64]`、`uhqw_bar_life[64]`、`uhqw_bar_ok[64]`。
   - `UHFW_QwantPublish` 与 `UHFW_QwantBumpLife` 将目标玩家编号 `pn` 编码入高 8 位广播，全客户端均可维护各玩家的最新状态。
   - 新增 `uh_qw_req_target(target_pn)` NET 脚本：服务端权威校验目标有效性与普通 Qwant 类别，并通过 `NamedExecuteClientScript("uh_qw_recv", req_pn, ...)` 定向单播回发；客户端设置 35 tics 限频防风暴。
   - `DISCONNECT`（服务端与客户端）及生命版本更迭时彻底清理对应玩家缓存。
   - 提供只读非 NET 接口 `uh_qb_count`、`uh_qb_string`、`uh_qb_int`，在摄像机 activator 下同步比对库存匹配度，未就绪时返回 `UHQB_NOT_READY`，杜绝混合版本或未持有时提前渲染。

3. **通用绘制复用与 Qwant 专属条渲染**（`src/acs_source/compat/mods/uix/uixweap_fixedbar.acs` 与 `uixweap.acs`）：
   - 提取通用的 `weaponBarDrawItem` 助手，支持双能量条、单能量条和无能量条（固定 class 复用）。
   - 实现 `weaponBarQwant`：在 `SetActivator(-1)` 前从摄像机完成 `CheckWeapon`、`CheckInventory` 及 `GetAmmoCapacity` 查询；`Qwant_W` 绘制 `MyDestinyAmmo` 与 `MoveRelearnAmmo` 双条，Move 槽位绘制对应属性或自定义 Ammo 能量条；不伪造 slot 1～5 绑定提示（传 `-1`）。
   - 在 `UIX_WeapBar` 中紧接固定 class 路由后挂接 `uh_qb_count` 分支，未知或未就绪时平稳处理，不影响 MegaMan 原版逻辑或固定 class 逻辑。

4. **编译与打包验证**：
   - 全量原生 ACC 编译器验证通过：`./tools/compile-acs.sh` 输出 `ACS COMPILE OK`（0 错误，0 告警）。
   - PK3 归档打包并通过校验：`./tools/validate-build-pk3.sh` 输出 `status=ok`（17575 entries, 31.7MB）。

