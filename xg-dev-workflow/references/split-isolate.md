# 拆分与隔离 (split & isolate) — 机制细节

SKILL.md「拆分与隔离」holds the essence + the A↔B 判定; this file holds the field-level
mechanics. 两种粒度，互相独立，都可选（够小就不拆，行为与现状一致）。

## A — 设计内 part 化（单 design.md）

一个设计可拆成若干 **part**（≥1 个 module 组成、作为独立单元实现+测试的命名块）；part 间边界为 **seam**，
其契约 = `design.md`「Interface/contract」对应条目，**随设计冻结**——这个冻结正是各 part 能对着它独立开发+
单测（mock 邻居）的前提。part 是一条**可选分组轴**，贯穿 `design.md`(「Decomposition/Parts」表) →
`plan.md`(task 的 `Part:` 字段) → `test.md`(按 part 分节 + Integration 下「跨 part 联调」子节) →
`progress.md`(Task status 的 `Part` 列)。**seam 契约被联调证伪**（冻结契约定错）= 架构级变更，走 **M2**
（`change.md` 的 `seam-contract-disproved` 触发），**不**静默改 plan。

## B — 需求级拆分 = 多 card + index 看板

拆大了就**拆成多个需求**（再跑 `new`）。每项目 `index.md` 是一块**看板**：一行 = 一个 **card**
（= 一个完整生命周期单元 = 一个 `NNN-slug/` 目录；card 是"需求目录"的看板别名，技能其余处仍称 requirement
指该单元——scoped homonym）。看板显示 **Phase**（走到哪，card 级摘要）+ **整体状态**（人设调度轴
`backlog|todo|active|blocked|paused|done|dropped`，**与内部阶段 status 值分离**，内部值不上看板）+ **Deps**
（同项目 NNN，M3 查无环）。两轴**松耦合**：除少数单调约束（done⇒tests通过&Phase=测试&评审 doc 或
`XS/S — review skipped` 注已存在；backlog⇒仅脚手架；paused/blocked⇒已起步）外自由。`new` 设初始
整体状态=`todo`。`resume` 不变（仍只进单 card 内部、不读看板）。

**Card 还是雾（fog）？**（借 wayfinder 的 fog-of-war 判定）拆出的一项能**精确表述问题**（不必能回答）
→ 立 card / roadmap Next-up 条目；还表述不清 → 留 roadmap Themes/Someday（雾），随前面 card 的推进再
具体化——不要把雾预切成 card。给人读的行文里 card 用**名字**指称（NNN 跟在链接里），不用裸编号。

## 术语

各一个 canonical 形：**part** / **seam** / **联调**(integrate, = `test.md` Integration 下的具名子节) /
**card** / **整体状态**。homonym：口语"part/部分"、既有"Integration"测试桶——按 context 区分，不算漂移。
