# 拆分与隔离 (split & isolate) — 机制细节

SKILL.md「拆分与隔离」holds the essence + the A↔B 判定; this file holds the field-level
mechanics. 两种粒度，互相独立，都可选（够小就不拆，行为与现状一致）。

## A — 设计内 part 化（单 design.md）

一个设计可拆成若干 **part**（≥1 个 module 组成、作为独立单元实现+测试的命名块）；part 间边界为 **seam**，
其契约 = `design.md`「Interface/contract」对应条目，**随设计冻结**——这个冻结正是各 part 能对着它独立开发+
单测（mock 邻居）的前提。part 是一条**可选分组轴**，贯穿 `design.md`(「Decomposition/Parts」表，
Part cell 短名即 **canonical part 名**，`R` 列 = 各 part 承载的 R-ids、兼作工具解析的新格式标记) →
`detail.md`(part 化的卡可按 part 拆 `detail-<slug>.md` 子文件；**总纲 detail.md 保留，其 part→子文件
映射是权威连接**——文件名取英文 slug，自由) → `plan.md`(task 的 `Part:` 字段，取 canonical part 名) →
`test.md`(按 part 分节 + Integration 下「跨 part 联调」子节) →
`progress.md`(Task status 的 `Part` 列)。**seam 契约被联调证伪**（冻结契约定错）= 架构级变更，走 **M2**
（`change.md` 的 `seam-contract-disproved` 触发），**不**静默改 plan。

## B — 需求级拆分 = 多 card + index 看板

拆大了就**拆成多个需求**（再跑 `new`）。每项目 `index.md` 是一块**看板**：一行 = 一个 **card**
（= 一个完整生命周期单元 = 一个 `NNN-slug/` 目录；card 是"需求目录"的看板别名，技能其余处仍称 requirement
指该单元——scoped homonym）。看板显示 **Phase**（走到哪，card 级摘要）+ **整体状态**（人设调度轴
`backlog|todo|active|blocked|paused|done|dropped`，**与内部阶段 status 值分离**，内部值不上看板）+ **Deps**
（同项目 NNN，M3 查无环）。两轴**松耦合**：除 M3 检查的单调约束（done / backlog / paused-blocked
的前置条件——权威列表见 `omission-check.md`「Board (kanban) consistency」）外自由。`new` 设初始
整体状态=`todo`。`resume` 不变（仍只进单 card 内部；看板只用于定位、不作状态源）。

**Card 还是雾（fog）？**（借 wayfinder 的 fog-of-war 判定）拆出的一项能**精确表述问题**（不必能回答）
→ 立 card / roadmap Next-up 条目；还表述不清 → 留 roadmap Themes/Someday（雾），随前面 card 的推进再
具体化——不要把雾预切成 card。给人读的行文里 card 用**名字**指称（NNN 跟在链接里），不用裸编号。

## Split-out procedure（升 B 后的拆出五步）

升 B 结论经人拍板后（requirement 拆分审视拍 / design-grill Parts 复核 / detail·implement
探测句 → M2 提议，任一入口），按序执行——每步指向权威文本，**不另立机制**：

1. **子卡 `new`** —— 走 SKILL.md `new` verb（编号、脚手架、看板行、roadmap graduation 照旧）。
2. **R-id 承接** —— 父卡侧是 **M2 撤销 mode 的一个具名实例**（`change.md` 撤销：retire 留
   ID、注记、永不重编号；父卡已 confirm 时须先走 M2 修改列表）；子卡 requirement 的对应
   条目加一行承接注记（「承接 <父卡> 同名 retired 条目」，002 先例）。**不得在此另写 retire
   语义**——change.md 是唯一权威。
3. **看板 Deps 接线** —— 父子卡在 `index.md` 的 Deps 列互记（本文件 B 节；M3 查无环）。
4. **seam 落具名契约** —— 卡间边界写成一份契约，家 = **provider 卡 `design.md`
   「Interface/contract」条目**（与 A 级 part seam 同 home、随其设计冻结）；provider 设计
   尚未冻结（需求期拆卡）时，先在**双方 requirement 的 Constraints** 各记契约要点
   （001→002 的 environment contract 形态），provider 冻结时正式化。
5. **剩余部分处置** —— 拆剩的内容按上方 **card-还是-雾判定**归位（立卡 / roadmap 雾），
   不悬空。

## 术语

各一个 canonical 形：**part** / **seam** / **联调**(integrate, = `test.md` Integration 下的具名子节) /
**card** / **整体状态**。homonym：口语"part/部分"、既有"Integration"测试桶——按 context 区分，不算漂移。
