# UIX killfeed 兼容实施计划：MegaManU

## 已确定的目标

首期为 MegaManU 接入 UIX v3bh 原有 killfeed，使用带有 4x 缩放定义的 `UMUG_0`（包装了 `C@ICN0`）作为头像。头像不随武器颜色变化，不接入 UH 的动态头像颜色层。先完成一个角色的接入，再按验证结果扩展其他角色。

> [!NOTE]
> **头像缩放机制发现**：
> UIX（`UIXMSG.acs`、`UIXTEAM.acs`）与原版 MM8BDM（`TEXTURES.MUGSHOT`）的所有头像统一采用 `XScale 4.0 YScale 4.0` 定义（32x32 纹理缩放至 8x8 逻辑尺寸）。Zandronum 引擎在 `FSinglePicFont` 中读取 `GetScaledWidth()` / `GetScaledHeight()`。若直接返回未缩放的原始 patch `C@ICN0`，逻辑尺寸为 32x32，在 UIX 绘制时会被放大 4 倍，导致中心大击杀头像超大且无法与 8x8 规格的骷髅特效层（`UXMGSKIE`）对齐。因此需返回 `UMUG_0`（已在 `TEXTURES.classes.faces` 中定义为 `XScale 4.0 YScale 4.0`）。

## 源码依据

- UIX 参考源：`../references/for_8bdm-v6b/8bdm-uix-v3bh/acs_source/UIXMSG.acs`。`UIX_KillfeedDispatch` 为客户端 DEATH 脚本；`UIX_Killfeed` 获取头像，返回空字符串时终止显示。
- UIX 参考源：`acs_source/uilib/SHRTFUNC.acs`。`getMugshotGraphicFromTID` 根据玩家 Actor 名检查 `PBMug_<Actor名>` 标记 Actor，再调用同名 ACS 脚本，以玩家 TID 为参数获取头像资源名。
- UIX 参考源：`acs_source/pb-skinsupport/PBSKINS.acs` 与 `decorate/pbskins.dec`，提供原版 MegaMan 的 PBMug 接入样板。
- 原版 MM8BDM 参考源：`TEXTURES.MUGSHOT` 均以 `XScale 4.0 YScale 4.0` 定义。
- 本项目 `src/TEXTURES.classes.faces` 已将各 Survivor 头像定义为 `UMUG_<id>`（包含 `XScale 4.0 YScale 4.0`）；MegaManU 对应 `UMUG_0`。

## 实施步骤

1. 核对 MegaManU 实际玩家 Actor 名、现有 DECORATE 兼容文件的 include 位置及 `UMUG_0`（`C@ICN0`）的字体可用性，确认不存在同名 PBMug 定义。
2. 在 `src/actors/compat/uix/` 下新增头像兼容文件 `MegaManU_Mugshot.dec`，定义无行为的 `PBMug_MegaManU` 标记 Actor，并在 `MegaMan.dec` 末尾引入。
3. 在 `src/acs_source/compat/mods/uix/` 下新增头像实现片段 `uh_uix_mugshots.acs`，由现有 `uh_uix.acs` 聚合。添加 `PBMug_MegaManU` 命名脚本，接受玩家 TID 参数并通过 `SetResultValue("UMUG_0")` 返回 4x 缩放头像。
4. 复用现有 `uh_uix` 库及 LOADACS 条目，无需新增库、覆盖 UIXMSG 或修改 UIX 击杀分发逻辑。所有参考树保持只读。
5. 使用现有 ACS 编译方式检查 `uh_uix`，将 `src/` 打包到 `out/build.pk3`。静态核对 Actor include、脚本名称、参数和头像资源。
6. 使用 `tools/mm8bdm-v6b-linux.launch.json` 的 `mm8bdm-v6b-uix` 配置烟雾测试与联机验证。保留 base → v6b fixes → UIX → 本模组的加载顺序。

## 验收条件

- MegaManU 作为被查询玩家时，PBMug 接口返回 `C@ICN0`，且该资源可由 `CheckFont` 使用。
- 进行中的回合里，MegaManU 击杀或被其他已支持头像的玩家击杀时，对应观察视角能显示正确头像；双 MegaManU 场景也正常。
- 切换不同武器后，头像保持 `C@ICN0` 的原色。
- UIX 原有服务器、客户端 killfeed 开关和 `cl_showlargefragmessages` 仍控制显示。
- 未加载 UIX 时，本模组正常加载，不出现缺失依赖或额外 HUD。
- 检查 UIXTEAM 对同一 PBMug 接口的调用，记录 MegaManU 头像显示结果。

## 后续范围

首期保留 UIX 对自杀、环境死亡和分数变化的现有过滤规则。若普通击杀未触发显示，先检查客户端 DEATH 分发、死亡后的攻击者指针、frag 变化及 UH 回合状态，再根据证据决定是否适配事件入口。

完成 MegaManU 后，再规划其他 Survivor、Boss 和 Demoneye 的头像映射，以及复活、变身和回合清场等特殊流程。
