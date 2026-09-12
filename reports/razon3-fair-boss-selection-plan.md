# Razon 3 低出场次数优先 Boss 选择迁移计划

## 目标与本阶段边界

本阶段只迁移 Boss 选择的公平化机制：在不改变现有稀有度概率、强制选择、
Strongman 队列、Boss Combo 和 Shadow 等特殊流程语义的前提下，优先选择历史
出场次数较少的 Boss；最低次数相同时仍随机选择，避免固定 ID 顺序偏差。

本阶段不修改 LMS event、bonus event 或玩家 Boss 身份的选择。实现时可以采用可复用
的“计数读取／最低计数候选选择／提交计数”结构，为后续事件公平化提供模式，但不要
提前把 Boss、LMS event、bonus event 混进同一数据表或同一策略函数。

## 已核对的现状

### Razon 3.11.1

参考实现位于：

- `references/for_8bdm-v6a/uh-ub_razonpatch_3.11.1/acs_source/UH_LIB.acs`
- `references/for_8bdm-v6a/uh-ub_razonpatch_3.11.1/acs_source/UH_RZTOOLS.acs`

旧实现使用 `world int 101:BossPool[]` 保存计数。在普通与稀有 Boss 的固定 ID 范围
内扫描最小值，把所有同为最小值的 Boss 放入候选数组，再随机选择一个；每个最终写入
`BossDataArr` 的 Boss 都会使 `BossPool[id]` 加一。`SimpleBossChange` 也会增加对应
计数，因此强制／特殊组合并未被排除在历史之外。

该算法的核心原则可以保留，但固定 `0..199` ID 范围、`bossCandidate[100]` 和直接以
Boss ID 作为数组下标均不能直接移植。

### Unholy Razon 4.0

当前普通选择入口是：

- `src/acs_source/unholy/uh_bossselect.acs` 的 `ub_SelectBossAndEvent`
- `src/acs_source/unholy/uh_boss_selection_helpers.acs` 的
  `TrueRandomBoss`、`SetUpBossSelection_Func`

Boss 定义与池位于 `src/acs_source/_imports/uhdt.acs`：

- 原版 Boss ID 为 `0..999`，但只有 `IsBossDefined(id)` 为真的条目有效；
- 自定义 Boss ID 为 `-1、-2…`，最多 `UH_MAX_CUSTOM_BOSS` 个；
- 每个稀有度池已保存实际的 signed boss ID；
- `RandomBossFromPool(rarity)` 当前在池中均匀随机；
- `TrueRandomBoss()` 负责先决定 Ultra、Special、EX、Rare 或 Common 池，并在失败时回退
  Common。

此外，以下路径会绕过普通 `SetUpBossSelection_Func`：

- Strongman 队列直接写 `bossdataarr[0]`；
- `TryBossComboRoll`／`ApplyBossCombo` 写入固定、池选或动态组合；
- Shadow fakeout/reveal 会替换 Boss 身份；
- Boss FFA bonus event 在 `uh_events.acs` 使用独立的 `eventbossid[]`，属于后续
  bonus-event 阶段，不纳入本次改动。

## 设计决定

### 1. 公平化发生在稀有度池内部

保留 `TrueRandomBoss()` 现有的稀有度抽取顺序和概率，只将
`RandomBossFromPool(rarity)` 的普通选择用途替换为新的公平选择函数，例如：

```c
PickLeastSeenBossFromPool(rarity, avoid)
```

它遍历 `GetBossPoolCount(rarity)`／`GetBossPoolId(rarity, index)`，找出最低计数，
再在所有最低计数候选中随机选择。

这样不会把 Common 与 Ultra 放在同一个最低值竞赛中，否则稀有 Boss 会因计数天然
较低而失去“稀有”属性。现有稀有度概率必须保持原样。

`avoid` 预留给明确要求不同 Boss 的双人 Versus 等路径；普通多 Boss 回合不应借此
悄悄新增“绝不重复”的规则。

### 2. 不按 signed boss ID 直接索引

4.0 的自定义 Boss ID 为负数，因此禁止使用 `count[bossid]`。实现计数访问器：

- 原版 Boss：使用 `id` 作为 vanilla 计数表下标；
- 自定义 Boss：使用现有 `UH_BossCustomIndex(id)` 转成 `0..255` 下标；
- 任何未注册或超范围 ID 返回失败，不读取或写入数组。

建议接口为：

```c
GetBossPickCount(id)
IncrementBossPickCount(id)
```

访问器隐藏 vanilla/custom 两张表的细节。后续 LMS/bonus event 应拥有自己的访问器，
不要复用 Boss ID 映射。

### 3. 计数为服务器会话级、跨地图状态

Razon 3 使用 world array，语义是同一游戏会话内跨地图保留。4.0 应保持这一点，而不是
使用随地图重载清零的普通 library 数组。

实现前先全仓库和目标 MM8BDM v6b 依赖核对未占用的 world-array slot，再为 vanilla
和 custom 计数各分配一个明确的 world slot；不要复用 Razon 3 的 `101`，也不要与
当前 `100:winstreak`、`103:mercygiven`、`104:lmsdudearr[]` 等相撞。最终 slot 号必须
记录在 `uh_def.acs` 邻近声明的注释中。

不需要启动时随机初始化：ACS world int 默认零值正好表示“尚未出现”。服务器重启后
自然重新开始统计。若未来需要管理员清零或调试修改，另建显式调试 API，不应作为本次
选择机制的前置条件。

### 4. 只在“本轮 Boss 阵容最终确定”时记账一次

选择函数本身只返回候选，不增加计数。由阵容提交点统一调用
`IncrementBossPickCount`，避免回退、重试或同一结果被多个 helper 重复计数。

本次定义“出场”为被提交到本轮最终 Boss 阵容，而不是成功完成 morph。这样保持
Razon 3 在 morph 前记账的行为，也避免 morph retry 重复增加计数。

应覆盖：

- 普通自动选择：计入最终 `bossdataarr` 中每个槽；
- `uh_sv_ForcedBossN`：计入，因为它确实占用一次本轮出场；
- Strongman 队列：计入；
- Boss Combo：固定、pool、forced、random-pair、shadow-pair、zankokuna-pair 均按
  最终阵容逐槽计入；同一个 Boss 占两个槽时计两次；
- Shadow：只统计实际提交为本轮阵容、用于出场的最终身份。不要同时统计占位 ID、
  fakeout 临时候选和 reveal 结果。实现前应沿 `ub_ShadowBossManager` 确认阵容提交点，
  将记账放在最后一次身份改写之后；
- EX：统计最终选择的 EX ID，而不是同时给 base 与 EX 加一，以保持 Razon 3 的行为。

不应计入：

- 无效强制 ID 及其失败尝试；
- 稀有度池为空时被放弃的候选；
- morph retry；
- Dickhead revival（同一轮既有 Boss 的复活）；
- Boss FFA 的 `eventbossid[]`（留给 bonus-event 推广阶段统一定义）。

为防止不同分支遗漏，建议在 `ub_SelectBossAndEvent` 中让所有标准/Combo/Strongman
分支汇合到单一 `CommitSelectedBossHistory()`，再启动 `ub_MorphSelectedBosses`。
如果 Shadow 的最终身份只能在后续异步流程确定，则该分支必须延迟自己的提交，并用
round/slot 标志保证只提交一次；不要为了统一位置而统计临时身份。

### 5. 同最低计数时使用蓄水池抽样

不建议复制 Razon 3 的固定 `bossCandidate[100]`。4.0 单池容量可达到
`UH_MAX_VANILLA_BOSS`，且包含自定义 Boss。使用单次扫描的 reservoir sampling：

1. 遇到更小计数：更新最小值、把当前 ID 设为候选、tie count 设为 1；
2. 遇到相同计数：tie count 加一，以 `1/tieCount` 概率替换候选；
3. 跳过未定义、与 `avoid` 相同或不满足调用方资格条件的 ID；
4. 没有候选时返回 `UHBOSS_FAIL`。

这样只需常数额外内存，并保证所有最低计数 Boss 等概率入选，适合 Zandronum ACS 的
静态数组限制。

### 6. 公平选择与资格过滤分层

普通池选择只要求 Boss 已定义。Versus、Zankokuna 等路径还有额外资格规则，不能让
通用 helper 写死这些特殊条件。

本阶段建议：

- `TrueRandomBoss()` 使用按 rarity 的最低计数选择；
- `PickRandomVersusBoss(avoid)` 改为在其现有资格集合中选最低计数者；
- `PickZankokunaVersusBoss(avoid)` 同理保留自己的资格判断；
- `BOSSCOMBO_MODE_POOL` 只在组合自己的 ID slice 内比较最低计数；
- 固定组合没有选择余地，仍只在提交阶段增加计数。

如果 ACS 无法传函数作为 predicate，就分别保留小型扫描器，复用计数访问器和
reservoir 更新规则；不要用“先从全池公平选择、失败后无限重抽”的方式实现资格过滤。

## 分阶段实施步骤

### 阶段 A：计数存储与访问器

1. 扫描本项目、MM8BDM v6b 与必要依赖的 world/global slot，选定两个不冲突的 world
   array slot。
2. 在 `uh_def.acs` 声明 vanilla/custom Boss 出场计数。
3. 在 `uh_boss_selection_helpers.acs` 增加经过 `IsBossDefined` 和上下界验证的读取、递增
   helper。
4. 增加 DEBUG 日志：提交时记录 signed boss ID、名称、旧值和新值；正常配置下不产生
   额外日志。

### 阶段 B：普通 Boss 公平选择

1. 实现按 registry rarity pool 扫描的最低计数随机选择。
2. 保留 `TrueRandomBoss()` 当前的稀有度抽取与 Common fallback；只替换池内 picker。
3. 保留 forced boss 与 `-666` true-random 语义。
4. 在多 Boss 场景中每选定一槽后尚不立刻永久记账；先写 `bossdataarr`，由提交阶段统一
   增加计数。若需要让同一回合后续槽感知前面槽，则使用本轮临时增量参与比较，提交时
   再一次性写入 world count，避免永久重复记账。

推荐让后续槽感知本轮已选槽。否则所有计数相同的初始状态下仍可能连续抽到同一 Boss；
临时增量既保留重复的可能，也会在存在同等候选时优先扩散阵容。

### 阶段 C：特殊标准回合路径

1. 将 Strongman 路径纳入唯一提交点。
2. 对 `ApplyBossCombo` 的各模式分别确认最终 ID 写入时机；固定组合只记账，动态池选择
   使用最低计数策略。
3. 检查 Shadow fakeout/reveal 的最终身份边界，确保每槽仅记一次。
4. 检查 EX 转换发生在选择的哪一侧，确保只给最终 EX/base ID 之一记账。
5. 保持 Boss FFA、复活和 morph retry 不计数。

### 阶段 D：调试与验证

先做静态和 ACC 验证，不为此功能启动引擎：

1. 编译所有受影响的 ACS library，确认 world slot、数组和 helper 语法兼容目标 ACC。
2. 用一次性、仓库外测试脚本或人工表验证 reservoir sampling 的候选资格与计数转换；
   不把一次性脚本留在 `tools/`。
3. 检查所有写 `bossdataarr[][BOSSDATA_NUM]` 的选择路径，确认提交覆盖且没有双计数。

只有静态分析无法判断实际跨地图 world 状态或 Shadow 异步提交时，才按项目 MCP 规则
进行一次聚焦运行测试。建议验证矩阵：

- 同一 rarity 内计数 `{0,0,1}`：只能选前两个；
- 同一 rarity 内计数 `{0,0,0}`：大量抽样不应固定偏向最早 ID；
- vanilla 与负数 custom ID 同池且同计数：两者均可选择且不会负下标；
- forced、Strongman、固定 combo：不改变选择结果，但各出场槽计数加一；
- 两槽选择：第二槽考虑本轮临时增量；
- EX：只增加最终 EX ID；
- 空池／无合格 Versus 候选：保持当前 fallback 或失败语义，不发生越界；
- 地图切换：计数保留；服务器新会话：计数归零。

## 验收标准

- 当前 rarity 概率与 fallback 行为不变。
- 每次自动池内选择只可能返回当前合格集合中计数最低的 Boss。
- 最低计数并列时随机，不受 registry 顺序决定。
- 原版与自定义 signed ID 都安全工作。
- 普通、forced、Strongman 与所有 Boss Combo 最终阵容每槽恰好计数一次。
- Shadow、EX、重试与复活没有双计数。
- Boss FFA 和其他 event 尚未接入该计数机制。
- 同一服务器会话跨地图保留，重启服务器后清零。
- 受影响 ACS 完整编译通过，`LOADACS` 顺序和 library 划分不变。

## 后续推广接口

Boss 阶段稳定后，再分别为 LMS event 与 bonus event 建立自己的：

- 合格候选枚举；
- 持久计数表；
- 最低计数并列随机 picker；
- “何时算一次出场”的提交边界；
- forced/pity/EX/禁用条件的覆盖规则。

后续可以复用 reservoir sampling 的代码形状和测试矩阵，但不应复用 Boss 的 signed-ID
索引函数或计数数组。这样能推广公平策略，同时保持三套选择系统各自的资格与概率语义。
