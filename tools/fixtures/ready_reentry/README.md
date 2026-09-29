# Ready 重入回归 fixture

仅用于独立测试 addon；不要打进 `src/` 或正式 PK3。`DECORATE` 的 pickup
直接调用引擎 `A_Raise`，因此测试走真正的 `P_SetPsprite(...GetReadyState())`
入口，不需要修改生产武器。重复次数有限，不构成零 tic 循环。

将 `ready_test.acs` 用项目的原生 ACC 编译到临时 addon 的
`acs/RDYTEST.o`；将本目录的 `DECORATE`、`LOADACS` 和编译结果打成临时
PK3，在 mod 后加载。服务器和两客户端必须加载同一个 addon。
使用最小 v6b profile、dedicated LMS、`sv_cheats 1`；禁止加载只读参考树。

`pn` 是服务器玩家编号，不能从客户端启动顺序推断。普通 UH 玩家 TID
为 `1000 + pn`；先读取 actor_state 的 TID。所有脚本从客户端以
`pukename <script> <args>` 调用；`READY_TEST` 行出现在服务器日志中。

- `rz_debug_MorphMe 0 69`：KFC。先读取基线，再执行
  `ready_test_reenter pn 20`；native/total 增量均应为 1，容量应为 1500。
  `take DickGnawerAmmo 7` 后再重入，服务器弹药应仍为 3。
- `ready_test_health pn 1` 后约 0.4 秒执行重入：KFC 应只扣一次生命，
  `freeze=1 invuln=1 resume>0`。等待约 5 秒，三个值均应为 0。
- 正常 demorph 用 `ub_UnMorphThisTID tid bossid`，不要用 debug morph 的
  裸 `UnMorphActor` 代替清理链。读回 survivor，检查 phase 武器、完成标记、
  容量和 setup 标记已清除；再次 morph 同一 Boss 应重新获得一次初始化。
- Gravityman / MakeAGoodZero 的 bossid 分别为 119 / 306，初始生命增量
  分别为 1 / 2。Zero 进入第二、第三阶段后 native 应分别减少一条。
  Zero 动画有 200 tic 等待；重入会恢复当前等待帧，应等待至少 7 秒。
- `ready_test_eye_cycle pn`：从未 morph 的 survivor 开始，实际领取
  Tank PowerMorph、扣 123 弹药、Ready 重入、移除 PowerMorph，再领取一次。
  Tank Flash 有正常每次启动 +5 的回弹，不能要求弹药在重入后完全不变；
  扣 123 后重入 20 次仍应低于 400，不能再次执行初始化 +300。新身体必须重新
  初始化，即使前一次的库存 marker 曾随 unmorph 转移回来。
- `ready_test_snapshot pn`：补充读取服务器的 actor、生命、容量、弹药、
  属性层、阶段检查点和 eye 外观 / body claim。

建议再检查 Ballade 连续主射击（Buddha 固定为 1、地雷补回 3）、Neru
两个 watcher（各一个）、Tank/Brick 外观及 Archivist Shiny 模式重入稳定。
网络延迟测试应在传输层加入延迟，不能用降低 tic rate 代替。
