# Boss 公平选择阶段 C 复审结论

## 结论

阶段 A–C 的当前实现通过代码复审，可以进入阶段 D。

Bugbot 未发现缺陷；本地 `git diff --check` 与完整
`./tools/compile-acs.sh /tmp/unholyrazon4-stage-c-final-review` 均通过。复审覆盖
vanilla/custom signed ID、普通与多 Boss 选择、forced、Strongman、全部 Boss Combo
模式、Shadow 正常及提前退出路径、EX 最终 ID，以及永久计数的单次提交边界。

## 四项疑问的最终回答

### 1. Versus / Zankokuna 已完成最低次数优先

`uh_boss_combos.acs` 中的自动选择现在都在各自资格集合内：

- 先应用 `avoid` 和 allowlist；
- 读取 `GetBossPickCount(id)`；
- 加上 `UH_BossRoundSeen(id)` 的本轮临时增量；
- 只保留最低计数候选；
- 最低值并列时用 reservoir sampling 等概率选择。

这已覆盖普通 Versus、Zankokuna 六项 allowlist 和只能从 300/400 中选择的 primary
fallback。第二槽会避开第一槽并看到本轮临时增量。

Razon 3 的动态特殊组合并没有完整执行这项公平规则，但本项目的目标是把低出场次数
策略推广到所有自动 Boss 候选集合，因此当前实现比旧版更一致，同时保留各分支原有
资格限制。

### 2. EX 统计的是最终 EX ID

Unholy Unbound／Razon 3 的旧流程先调用 `EXBossChecker` 把 base ID 转为 EX ID，再对
最终 `BossDataArr[][BOSSDATA_NUM]` 增加 `BossPool`，所以旧版语义也是统计最终 EX。

4.0 不再有可执行的 `EXBossChecker`。EX Boss 是独立注册项，直接进入
`UHBOSS_POOL_EX`；公平 picker 返回的已经是最终 EX ID，提交点随后统计该 ID。因此
不会同时增加 base 与 EX，也不存在提交发生在转换之前的问题。旧的 `// EXBossChecker`
注释已不再代表实际流程。

### 3. Shadow 的遗漏与同轮重复问题已修复

当前分支边界为：

- 中央 `CommitSelectedBossHistory()` 跳过 Shadow 槽；
- 普通 Shadow 确定 reveal ID 后先写入本轮 delta，最终 reveal 时永久提交一次；
- Shadow-versus 重复目标 fallback 恢复原组合时，退出前逐槽提交原始最终 ID；
- bot、actor 消失等导致 Shadow 标志提前清除时，立即提交保留下来的原 Boss；
- 正常 reveal、fallback 与提前退出互斥，没有发现重复永久递增；
- morph retry 与 Dickhead revival 不进入提交路径。

Razon 3 原实现倾向统计 Shadow 的初始假身份；4.0 当前实现按新计划统计真正用于本轮
出场的最终身份。这是有意的语义改进，不需要回退到旧行为。

### 4. 阶段 D 仍需执行

代码与编译审查通过不等于运行期验收完成。下一阶段仍应执行：

1. 在仓库外创建一次性 reservoir 抽样验证，覆盖 `{0,0,1}`、全相等、`avoid`、
   vanilla/custom 混合候选和本轮临时增量；不要把脚本留在 `tools/`。
2. 聚焦验证 world arrays 在地图切换后保留、服务器新会话归零。
3. 聚焦验证 Shadow 正常 reveal、多个 Shadow 槽、bot/actor 消失、晚断线及重复目标
   fallback，每个最终槽恰好增加一次。
4. 验证 forced、Strongman、fixed/pool/dynamic Combo 和 EX 最终 ID 的实际计数结果。

## 进入阶段 D 的门槛状态

- [x] 最低计数池内选择
- [x] 并列候选无 registry 顺序偏差
- [x] signed custom Boss ID 安全
- [x] Versus/Zankokuna/primary fallback 公平化
- [x] 普通、forced、Strongman、Combo 单次提交
- [x] Shadow 正常及提前退出分支单次提交
- [x] EX 最终 ID 语义
- [x] 完整 ACS 编译
- [ ] 抽样统计验证
- [ ] 跨地图 world 状态运行验证
- [ ] Shadow 异步运行验证

因此阶段 C 已完成，剩余未勾选项属于阶段 D，而不是继续阻挡阶段 C 的代码缺陷。
