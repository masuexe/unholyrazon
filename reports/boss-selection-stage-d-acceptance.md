# Boss 公平选择阶段 D 待修复／待验收报告

日期：2026-09-13

## 结论

**不能删除 `reports/*`，阶段 D 尚未达到全部指标通过。**

本轮没有发现已证实的生产代码错误，但 Shadow、Strongman、EX 与 signed custom Boss 的完整端到端矩阵仍缺可靠证据。当前单机地图会自动加入并循环驱动 8 个 bot；运行数分钟后，大量常驻 ACS 和回合脚本会与人工触发的同名选择脚本并发，导致测试调用未消费 CVAR 或测试脚本长期保持 `Running`。这些受污染结果均已作废，不能据此判定产品失败或通过。

本次未修改模组源码。所有附加脚本、覆盖 object 和自定义 Boss 均只位于 `/tmp`；测试实例均已关闭。

## 测试环境

- MCP：`/home/user/mcpfiles/zandronum-mcp`
- 引擎：Zandronum `3.3-alpha-r260112-1855M`（commit `2d4749b0fa1d`）
- 顺序：`megagame.wad` → `mm8bdm-v6b.pk3` → `8bdm-v6b-miscfixes-v6.pk3` → `out/build.pk3` → `/tmp` 测试覆盖包
- 地图：MM2DW1、MM3DW1、MM3DW2

仓库 Linux profile 仍含另一台机器的 `/mnt/d/...` 与 `/home/user/...` 路径。本轮改用 MCP 显式绝对路径，能够稳定启动；端口被旧实例占用时，改用独立 instance 5–8 后恢复。没有改动仓库 profile。

## 已通过（直接调用真实 library 实现）

1. 全部 ACS library 编译通过；PK3 入口检查通过；MCP 启动无解析或致命错误。
2. `PickLeastSeenBossFromPool`：`{0,0,1}` 抽样 10000 次得到 `{4967,5033,0,0}`。
3. 三方并列抽样 12000 次得到 `{3965,3876,4159,0}`，无 registry 首项偏置。
4. 本轮临时增量：1000 次两槽试验中，第二槽重复第一槽次数为 0。
5. 标准 forced：Boss 0 的永久计数由 0 增至 1。
6. 固定 combo 201：ID `0/25`，槽数 2，总增量 2，各增 1。
7. POOL combo 501：槽数 5，总增量 5。
8. FORCED combo 206：ID `6/4`，槽数 2，总增量 2，各增 1。
9. RANDOM_PAIR combo 209：全新实例中槽数 2，总增量 2，各增 1。
10. ZANKOKUNA_PAIR combo 218：ID `300/403`，槽数 2，总增量 2，各增 1。
11. `changemap` 后探针值 `7 → 7`；终止服务器并启动新实例后归零。
12. 临时 addon 成功注册 Common custom Boss：`uh_bosscustomcount=1`，Common pool `77 → 78`。
13. 静态复核：custom ID 经 `UH_BossCustomIndex`；EX 为独立最终 ID；morph retry、revival、Boss FFA/event 不调用历史增量。

## 尚未通过的指标

1. signed custom Boss `-1` 实际参与最低计数抽样并提交一次。
2. Strongman 的真实 `ub_SelectBossAndEvent` 路径提交一次。
3. EX 池自动抽取后只给最终 EX ID 加一。
4. Shadow 正常 reveal、多 Shadow、bot/actor 消失、晚断线、duplicate fallback 的最终身份逐槽恰好一次。
5. morph retry 与 Dickhead revival 的运行前后计数快照不变。
6. 空池／无合格 Versus 候选的运行期 fallback/失败语义。

一次 Shadow 全流程人工触发后，脚本已结束但强制 CVAR 仍保持 `217/4/9`，说明该次调用没有真正消费配置；四个目标 ID 的零计数不是产品缺陷证据。另一轮 Shadow 原子探针长期 `Running`，同样因实例已有并发回合状态而作废。

## 待修复的测试条件

剩余验收需要无自动回合并发的隔离环境：使用仅位于 `/tmp` 的最小测试地图/PK3 构造 player/TID 状态，或启动专用 server 并连接多个独立客户端、禁用自动 bot，再驱动真实 LMS 回合。Shadow/Strongman/EX 最好由同一个原子测试脚本完成状态构造、调用、等待与快照。

只有上述六项补齐并通过后，才可以删除计划、阶段 C 复审和本报告。
