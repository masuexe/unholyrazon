# 蓄力 CustomBar 看似错位的根因

## 结论

CaptainBlitzkrieg、Misery 等蓄力条的症状不是 `position` 坐标算错，而是 TOML 中迁移了错误的前景/背景图形：这些条使用了 `UHVT238` / `UHHT238` 作为 full bar，但该组图形的 full 实际上是全透明图，empty 才是 `NOBAR` / `VNOBAR`。

`DrawBar` 会先绘制完整背景，再根据数值裁剪并绘制前景。当前组合等价于：

1. 先画完整的黄色空条；
2. 再用透明 foreground 覆盖/清除“已充能”的区间；
3. 屏幕上只留下“尚未充能”的黄色区间。

所以随着蓄力变化，黄色条的可见起点发生移动，并向正常填充方向的反方向缩短。截图中黄色条从正常 bar 中段开始、向下延伸，视觉上像整条 bar 的 Y 坐标错位；实际上它是**反向显示的剩余区间**，不是同一完整条被平移。

## 直接证据

### 1. CaptainBlitzkrieg 与 Misery 都引用了错误图形组

`tools/bars.toml`：

- `:345-358`：`UHBar_CaptainBlitzkrieg` 使用 `UHVT238/UHVB238/UHHT238/UHHB238`。
- `:1552-1562`：`UHBar_Misery` 的 `overcharge` 同样使用该组图形。

生成结果保持了 TOML 输入：

- `src/SBARINFO.h.uhappend:1811`：CaptainBlitzkrieg 使用 `UHHT238` 作为 foreground、`UHHB238` 作为 background。
- 同文件 `:1921`：Misery overcharge 使用同一组合。

因此生成器没有产生坐标漂移；它忠实生成了错误的素材配对。

### 2. `238` full 是透明图，不是蓄力条 foreground

`src/TEXTURES.bars:348-351` 当前定义：

```text
texture UHVT238, 8, 56 {patch TNT1A0, 0, 0}
texture UHVB238, 8, 56 {patch NOBAR, 0, 0}
texture UHHT238, 56, 8 {patch TNT1A0, 0, 0 {rotate 90}}
texture UHHB238, 56, 8 {patch VNOBAR, 0, 0}
```

也就是说：

- `UHVT238` / `UHHT238`：透明；
- `UHVB238` / `UHHB238`：黄色 `NOBAR` 空条。

这组定义适合充当“透明擦除/反向遮罩”一类效果，不适合作为普通从 0 向 capacity 增长的蓄力条。

### 3. 引擎行为解释了截图形态

Zandronum 的 `CommandDrawBar::Draw` 位于：

- `../references/zandronum/zandronum-stable-branch-default/src/g_shared/sbarinfo_commands.cpp:2633-2639`：先绘制完整 background；
- 同文件 `:2642-2659`：按数值计算裁剪区域，再绘制 foreground。

当前 foreground 为透明纹理，因而被裁剪的充能区间不会提供黄色像素；可见黄色来自先画出的 background，并只剩下未被 foreground 区间替换的部分。这与截图中“黄色条只从中途开始”的现象一致。

### 4. 旧版使用的是有色 foreground

旧 Unholy v7b pb1 的 CaptainBlitzkrieg 定义为：

- `../references/for_8bdm-v6a/unholy_bosses_unbound_v7b_pb1/SBARINFO.VB.txt:1185`：`34_B_V11` + `NOBAR`，坐标 `16,8`；
- 同包 `SBARINFO.HB.txt:1181`：`34_B_H11` + `VNOBAR`。

Razon patch 中也保持相同语义：

- `../references/for_8bdm-v6a/uh-ub_razonpatch_3.11.1/SBARINFO.VB.txt:1591`；
- 同包 `SBARINFO.HB.txt:1578`。

Misery overcharge 同样使用：

- `../references/for_8bdm-v6a/uh-ub_razonpatch_3.11.1/SBARINFO.VB.txt:1815`：`34_B_V11` + `NOBAR`；
- 同包 `SBARINFO.HB.txt:1800`：`34_B_H11` + `VNOBAR`。

而当前 `src/TEXTURES.bars:322-329` 仍保留正确的 `34_B_V11` / `34_B_H11` 有色 foreground。因此不是素材缺失，而是 TOML 条目在迁移时选择了 `UH*238` 透明包装组。

## 为什么不是 position 错误

当前生成器对 `position = "1"` 使用：

- 竖条：`16,8`
- 横条：`58,184`

CaptainBlitzkrieg 的旧竖条坐标同样是 `16,8`。截图中的黄色条也位于标准 ammo-bar 横向槽列；异常主要体现在可见部分的起止高度，而非整张 8×56 bar 的锚点被平移。

Misery 的 `cooldown` 与 `overcharge` 都声明为 position 1，只通过 priority 叠层。这符合旧版把状态条覆盖在既有 bar 槽上的设计。priority 只控制绘制顺序，不改变坐标，也不是此次根因。

## 形成原因

这是一次数据迁移错误：把旧 BARLIB/兼容槽位编号 `238` 当成了它所代表的视觉 bar，继而在 TOML 中引用生成后的 `UHVT238/UHHT238` 名称。但槽号只是兼容目录索引，并不保证对应包装纹理就是原始游戏逻辑使用的 foreground。

迁移时应以原调用中的四个实际纹理名为准，而不能根据旧 slot 编号反推素材。对 CaptainBlitzkrieg 和 Misery，旧调用的实际语义是：

```text
vertical:   34_B_V11 + NOBAR
horizontal: 34_B_H11 + VNOBAR
```

## 潜在影响范围

当前 `tools/bars.toml` 共有十个 namespace 引用了 `UHVT238/UHHT238`，都应按各自旧 SBARINFO 或迁移前调用逐项复核，不能假定全部都应统一替换：

- `UHBar_CaptainBlitzkrieg`
- `UHBar_Wahwee_W1`
- `UHBar_IronCurtain`
- `UHBar_Misery`
- `UHBar_ChieftainTomahawk`
- `UHBar_Clownpiece`
- `UHBar_Joterra`
- `UHBar_EyelentoMajor`
- `UHBar_TheShadowManMythBoss`
- `UHBar_ScrotoStuntDouble`

旧参考中多项确实使用 `34_B_V11/H11`，但它们原先可能位于 position 1、2、3 或 HP 槽，也可能与其他状态条重叠。修复时应分别核对四个纹理名、position、priority 与 source，避免只修正截图中的两个 class 后留下同类问题。

## 修复方向（本报告不实施）

1. 将 CaptainBlitzkrieg 与 Misery overcharge 的 TOML 图形恢复为旧版实际 foreground/background：`34_B_V11/NOBAR` 和 `34_B_H11/VNOBAR`，或使用内容等价且无旧 slot 耦合的新名字。
2. 对其余八个 `UH*238` 使用者逐项比对旧 SBARINFO，按原纹理和原槽位修正。
3. 给生成器测试增加约束：普通增长型 bar 不允许使用“full 全透明、empty 非透明”的组合，除非条目显式声明反向/遮罩意图。
4. 回归测试竖条与横条 HUD；分别在 0、中间值、满值截图，确认可见区域从正确端增长并与目标槽重合。

本次仅记录根因，没有修改 TOML、生成器、SBARINFO 或 TEXTURES。
