# Changelog — xg-dev-workflow

Behavior-level history of the skill (the curated view; `git log` is the full one). Maintained by
the M6 retro step: when a retro changes skill behavior, prepend a dated entry here, newest first.
Each entry says *what changed* and *why*, not the raw diff.

## 2026-08-16 — 020 close-out review fixes (carriers edges + retire predicate)

- `workflow-status.py` carriers: closed-list modes (ledger/doc-gate) now also surface actual
  top-level `notes/*.md` as `expected=False` discovery rows (grill logs are real mining
  carriers — Layout's `notes/` line was silently narrowed to two globs); family-glob
  exclusion made single-level so nested `notes/review-X/*.md` enumerate; non-md dir rows
  are discovery (`expected=False`) in every mode. Why: close-out review H1/H2/M2 — the
  golden sample (legacy) never exercised the closed-list branches.
- Retire-accounting detection unified into `RETIRE_ID`/`RETIRE_MARK` (cell-scoped,
  case-insensitive, separator-tolerant), shared by `--check` superseded-ref and the trace
  gap-flag suppression; recognized forms pinned in templates/requirement.md. Why: review M1
  — three detectors had split, each missing forms the templates/practice produce (017's R7
  false ⚠ now clean); live rows merely mentioning "retired" still flag.
- `steps/learn.md`: §9 carries a 「无」 line when no input card is in flight (ten-section
  shape invariant); empty-口径 declaration pinned to the §1 metadata field; the 非真相源
  declaration's dangling template citation replaced with its actual terms.
- `templates/index.md`「参考对象注记」: list lines only — a `| NNN |`-shaped row would be
  parsed by board() and silently overwrite that card's kanban entry.

## 2026-08-13 — workflow-status --check:retire 记账行不再误报 superseded-ref

- `_referenced_ids` 跳过 retire 记账行(需求 R 表 `~~…~~ retired` 行、design trace
  「retired——」行):它们是 M2 撤销语义要求的形态(留 id、不重编号),不是对已 retire 决策的
  活引用;plan `Implements:`/ledger `depends-on` 的活引用照旧报。Why:020 close-out 实测
  R9 划线引用被误报,exit 1 阻塞「--check ok = exit 0」验收;trace matrix 不受影响
  (retired 行仍可见)。

## 2026-08-13 — learn 报告用词规则(用户 convention)

- `steps/learn.md` Render 节增用词规则:中文行文里该操作一律称「学习」(与 verb 名 learn
  对应),不用「蒸馏」。Why:2026-08-13 用户对金样报告用词的直接反馈;既有金样报告标题与
  longrun_test 看板注记已同步修正。

## 2026-08-13 — 020 落地:learn verb(从既有 card 提炼重做输入)

- 新增 `learn <card>…` verb(`references/steps/learn.md`):对同项目 1..N 张既有卡只读挖掘
  全生命周期文档,产出固定十节重做输入报告(事实类带时效标注、非事实类一律非约束标注+证伪
  依据、执行区暴露点 canonical 指路),落 `investigations/learn-*.md`;chat stop 采纳门——
  人 go 是 approved-note 身份唯一来源,回填(roadmap 无条件指针、看板参考对象注记、KB
  graduation、`adopted:` 行)只在 go 后。Why:2026-08-07 longrun_test 001/002 手工提炼证明
  该工作有效但无固定流程、落点分散、时效核验靠人工补。
- `workflow-status.py --json` 新增 `carriers` 字段(应有载体×存在性,四档判档)——learn 覆盖表
  的机械骨架;闭列映射只活在工具内一处(SKILL.md Layout 的机器可读镜像)。
- 消费通道:steps/requirement.md beat 1 增 learn 报告消费纪律(点名合法以 `adopted:` 行为判 +
  轴→节区映射 + 采纳门 + 重核纪律);steps/design-grill.md 明确 learn 报告不适用 pre-design
  消费;templates/facts.md 头注登记跨卡窄翻例外;KNOWN_ACTIONS 增 `learn`。

## 2026-08-11 — 019 落地:决策区讨论式议程(discussion-first)

- **决策区节奏倒转**(grill.md 新增「Discussion-first flow」节):需求/设计先讨论达成共识、
  文档只做共识转录——设计侧固定前段两拍(understanding statement · candidate spread)+
  agenda negotiation 独立 mini-round + 议题轮按 driving axis 排序;需求侧两拍(problem
  understanding · boundary spread)。多轮收敛循环(信息缺口逐项 resolved/deferred、增量重述、
  chosen 列实质)。起因:用户要「讨论出来的而不是模型直接写出的文档」(019 R1/R6)。
- **骨架 doc 取代 pre-draft window**(019 ADR-0001):两档 phase start 建骨架、节内共识前零散文;
  「先讨论」由转录不变式承载而非文件不存在——消化 SKILL.md lazy-creation 既存漂移,解
  doc-gate 讨论期容器死结。grill-log 决策区讨论式下 round 1 起强制落盘(豁免仅 generic
  grill);溯源锚 = ledger 行 + receipts commit。
- **转录保真**:lens 4 在 confirm/freeze ask 加双向核(不夹带/不漏记,not-satisfied 子型);
  (落纸补充)为 grill.md 自有讨论流标记(不入 provenance 三类),gate sweep 逐条列出、
  approve 清除。
- **检查轮型化**:When to run 加 discussion 行引 design-agenda.md 轮型映射(override:ADR 级
  与 freeze 前仍全 panel);receipts 记轮型/重派/依据;批组至迟簇末轮落盘。放行规则合并为
  一条双依据(panorama/siblings);round 扩义(一议题/一拍 = 一轮,backstop 计人侧触点);
  dry-check 基底拓宽为卡级 diff(过程行不计)。
- **新数据文件 `references/design-agenda.md`**:议题库(索引既有三处枚举,契约固定项标注)·
  driving axis(开放类 + 无主导轴缺省)· 轮型映射 · XS/S 条目表(14 行——小卡留讨论实质、
  省议程机器)。回填:park/resume/omission-check/id-schemes/templates-design/SKILL 措辞。
  设计全程以本流程 dogfood(019 卡自身,9 轮讨论 + 3 次 panel)。

## 2026-08-10 — retro:panel 结论的引用侧核对义务(Cite-side duty)

- **adversarial-critic.md「Receipts」增一句**:后续 doc/相引用 panel finding 必须点名可定位
  的收据,定位不到即按 M1 未验证断言处理。起因:017 详设曾以「panel-3」标号引用设计轮
  panel 结论而收据不存在(标号错),其中一条(viewer drawer 泛化渲染「免费」)恰为错误结论,
  借无收据引用传进 detail/design 两文档,直到合并 gate lens4 亲验才抓回——receipts 缺位
  不止损审计,会直接掩护错误传播。同批:017 轮次数据补进讨论式议程提案 §6(升卡对照基线);
  check-code-refs ledger-id 覆盖缺口入 roadmap 候选;design 相 usage 记录补 corrective
  (5→4,panel 产出含一条被后续证伪)。

## 2026-08-10 — 017 落地:治理双档(ledger/doc-gate)·约定 core 共享·check-sync·part-check

- **治理双档**(SKILL.md「Ledger」Governance mode · gate-digest「Doc-gate cards」· grill/
  change/park/resume/improve/omission-check/templates 全链分支):卡模式为两级 cascade——
  requirement frontmatter `governance:` 字段优先(new 按 sizing 预填,需求 gate 人拍为第一
  判定项),无字段 = legacy 回落 decisions.md 存在性轴,存量零迁移。XS/S 走 **doc-gate**:
  缩放版 digest(仅免 §2 账本卡片与转录环,§1 自检/receipts 保留)、status 直写 + Change log
  gate 行审计锚、决策/事实/提案的 doc 三载体;M+ ledger 全套不变;升级 doc-gate→ledger
  一次性 M2 不回填。工具:`card_mode` + 四条无条件检查(i1–i4)+ viewer tile/drawer badge。
  实证:018 演练卡全周期人侧动作 2≤3。起因:2026-08-07 复杂度评估——决策区 gate 固定附属
  动作 ≥8 类且不随 sizing 缩放,是主膨胀轴。
- **约定 core/supplement**:跨包共有写作规则装配为 `references/conventions-core.md`
  (byte-identical 双副本,diagram-gotchas 同入同步集),doc-conventions.md 收缩为 workflow
  supplement;wikilink 全集留 FORMAT.md(避免 $KB 悬空)。
- **check-sync**(`tools/check-sync.py` + `sync-manifest.txt`):manifest 驱动的同步物确定性
  检查(六组,含 $KB 两对),只报不改;wire 进 retro 周期项 + CLAUDE.md invariant 1;
  FORMAT.md 140 行存量漂移人批清零,raw-archetypes.md 入 lite init 拷贝集。
- **part-check**(implement.md 新 beat):part 完工点 1–2 个 fresh-context agent 攻该 part
  diff,非人 gate、每 finding 留痕(修 or log)、实测项按项目 test mode 分流;产物
  `notes/part-check-*`;首跑(017 自举)即抓 13 条含一条实测漏报。
- 全程 receipts:dev_root xg-skills/017 卡(需求 e234858 · 设计 c237357 · baseline+授权
  9530529;close-out review 6 findings 全修)。

## 2026-08-10 — check-code-refs 补上 card-internal id(T<n>/R<n>/S<n>),仅限注释行

- **起因**:card 006 的 close-out review 挖出 13 处代码注释里写着卡内任务号(`(T42)` /
  `T43e's` / `T42 measured`),而 `check-code-refs.py` 在这些行上**退出 0** —— 它的模式表
  只覆盖 `.md` / wikilink / `ADR-NNNN` / `file:line`,没有 card id。规约本身早就禁止
  (「代码里不放工作流/KB 引用」),缺的是检查手段。
- **新增 `COMMENT_PATTERNS`,只在注释行生效**:`\b[TRS]\d{1,3}[a-z]?\b`。
  **注释限定是这条能用的全部理由** —— 代码里的裸 `T1`/`T2` 是泛型类型参数与普通标识符,
  全域匹配会把它们全报出来,而没有人会在散文里写「T42 measured」。
- **实测**:同一个探针文件上,改前退出 0、改后退出 1 并逐条点名;
  `func apply[T1 any]` 这行(非注释)不报。

## 2026-08-07 — 复杂度评估第一批:progress cap · XS KB 默认缓记 · gate 成本预算 · model-tiering 外移

- **起因**:同日复杂度评估(dev_root `xg-skills/notes/2026-08-07-workflow-complexity-assessment.md`)
  实证:决策区一次 gate 的固定附属动作 ≥8 类且不随 sizing 缩放;card 016 文档 4231 行、
  decisions.md 799 行超过 design.md 本体;resume 006 时 progress.md 已 2335 行而 resume 实际只读
  4 节(usage note)。主刀(治理层按 sizing 降级为 M+/L 叠加)与次刀(文档约定共享包)入
  roadmap 待开卡;本批只落 retro 尺寸的四小修。
- **progress.md 硬上限 ≈150 行**(templates/progress.md + omission-check「snapshot, not a log」
  项):超限即 flag、不豁免;Design iterations / Discovered issues 改为**只留 open 项** ——
  resolved 的收敛成一行链接迁出(此前两节按日期追加,是 2335 行事故的主要来源)。
- **XS 卡 KB-capture 默认满足**(omission-check「Knowledge captured & compiled」项):不再要求
  每轮显式 capture/defer 表态;发现明显可复用仍写 KB。
- **Pruning pass 新增 gate-cost budget 检查**(retro.md):新增 per-gate 动作须说明替换了哪条
  既有动作、或如何随 sizing 缩放;答不出即拒。把「per-gate 固定成本是主要膨胀轴」变成每次
  retro 的显式预算项。
- **model-tiering 外移**(SKILL.md → `references/model-tiering.md`):rationale + session-model
  tiering 段外移,SKILL.md 留核心规则 stub(heading 保留,既有「SKILL.md〈Subagent model
  assignment〉」引用继续解析);park.md / review-deep.md 改指新文件;Usage logging 段同批压缩。
  SKILL.md 374→365 行 —— 剩余大头是契约文本,继续瘦身属治理卡范围,本批不强压。
- **step binding 段检视后不动**:7 行全为载重条款(no-op test 反向结论 —— 非 sediment 不砍)。

## 2026-08-07 — panel finding 落盘;subagent 封顶 opus;resume 停顿等 go

- **Panel receipts 升级为 finding 级**(adversarial-critic.md):原一行 verdicts 丢掉的正是
  后续轮需要的内容 —— 被裁死 finding 的 why。新形态:header(row · lenses)+ 每条 finding
  一行 disposition(adopted → G/D ref · refuted — 一句 why · open → G row);落点不变
  (grill-log / closing message,park 兜底)。verified-facts pack 增加 **dead-findings 区**
  (claim + why-dead),后续 dispatch 附带,防止死 concern 每轮被重新"发现";凭新证据方可复活。
- **Subagent 封顶 opus**(SKILL.md「Subagent model assignment」+ adversarial-critic /
  review / review-deep / improve / evidence 各引用点):fable session 只让 orchestrator 本体
  跑 fable,inference-heavy dispatch(panel lenses、review axes、improve scan)默认
  `model: opus` —— 与 sonnet-for-gather 同构(限定域 mandate + orchestrator 复核),
  单价减半(Opus 5 $5/$25 vs Fable $10/$50);仍挂 M6 calibration。evidence.md 的
  recall-无兜底 carve-out 豁免 cap(cap 的安全论证正是 orchestrator 兜底,该场景不存在)。
  gather → sonnet、执行区 `/model sonnet` + `/advisor opus` 维持不变;不引入 haiku。
- **resume 汇报后停**(resume.md step 5):3 行 situation report 后 STOP 等 go,不再自动
  continue —— resume 是人的重入口,常带改向意图;调用自带指令("resume 016 继续 T5")则
  直接执行;go 后执行区自治照常。
- **环境事实边界半句**(grill.md「载重事实入账」):用户口述的环境事实(版本/规模/部署形态)
  未验证前不入 facts.md,归 phase doc Context 并标 provenance(M1)。
- 方案与四点评估:dev_root `xg-skills/notes/2026-08-07-panel-persistence-models-resume.md`。

## 2026-08-07 — grill 写入节奏钉死(round = 决策簇;doc 按轮写;禁转写确认 ask)

- **起因**:grill 中实际出现「已按推荐写进文档,要一句确认」—— 人未作答先落 doc,再加
  逐条转写确认 micro-gate。诱因是 grill.md 旧句 "convergence lands inline as you go" 与
  Round-end order(round 末才 sync doc)有张力,doc 写入单位没钉死;且 round 本身只有
  "a batch of resolved questions" 的模糊界定。方案:dev_root
  `xg-skills/notes/2026-08-07-grill-write-cadence-and-round-boundary.md`。
- **grill.md Protocol 三处**:(1) 写入三级节奏 —— per-question 只入账(逐条入账/载重事实
  入账)、per-round 才 doc fold-in + checkpoint(Round-end order 为 SoT)、per-gate 确认
  (digest 批账本行,不批 doc 文本);(2) 新 bullet「recommendation is not a decision」——
  人未作答前推荐不落 doc/ledger,合法 ask 仅三种(答案 ask · round-end go ask · gate ask),
  转写确认 ask 为禁止形态;(3) round 定义 —— 一个决策簇的解决过程(载重分支点开轮,
  walk 离开簇或簇内全 resolved/Open 收轮;adversarial pass 自成一轮;~6-8 resolved 问题
  兜底强制收轮),panel checkpoint / doc 写入 / go-ask 三机制共用此边界,~3-round 规则
  单位随之明确。共享层一改两阶段(requirement/design-grill)同继承;detail 无 grill 不涉及。
- 连带扫齐(invariant 6):试行窗口尾句改指 write cadence · Convergence 开头括注改指
  Protocol「Round」;requirement.md:85 原句已与新节奏一致,未动。
- 暂缓(记观察):requirement 阶段 ledger-first / prose 推迟到收敛后统一重写 —— 牵动
  试行窗口/fold-in/park,先观察钉死后的效果,M6 凭 usage log 再定。

## 2026-08-07 — gate digest 与 M2 修改列表体量收敛(digest 单条 chat 消息;M2 提案先入账本)

- **起因**:实测 longrun_test 项目落盘了 10 个本不该存在的文件共 1270 行 —— gate ask 两份
  (169/160 行,违反「digest never lands on disk」)、M2 修改列表八份(62–183 行,最大那份
  是完整变更提案而非 touch-list)。根因四条:卡片/自检段实际形态是 spec 设想的 2–3 倍;
  trace/pending 附件条款落后于实践(实践已自行压缩);「确认前零写入」把 M2 提案实质逼进
  note 文件(确认后誊入账本 = 双写);全局「长内容写文件」约定与「digest 是 chat 消息」冲突
  未显式解决。方案与答疑:dev_root `xg-skills/notes/2026-08-07-gate-digest-change-list-slimming.md`。
- **gate-digest.md 六处收敛**:自检段严格「verifier · receipt · verdict」一行制、上限 ~10 行
  (战报归 grill notes);卡片定形 ≤7 行(why ≤2 行 · alt 展示 ≤2 条 · 禁注意/连带类子弹,
  其家在账本行/doc §);trace 附件改为缺口行 + 一行统计 + 全表命令(不再全量内联);
  其余 pending 改按级别分组 id 清单,需特别注意的行单独点名;待你判每项 ≤3 行;新增
  「One chat message, never a file」规则 —— digest ≤~70 行,超限是内容回家的 routing 信号,
  落盘禁止,并明示 digest 是全局「长内容写文件」约定的唯一例外。
- **change.md 0b 顺序重排**:M2 提案实质(新陈述+why+alt)先以 proposed block 入账
  (推广 case A 步骤 0 的既有先例;被拒 → retired 留一行原因);修改列表回归 touch-list
  (写操作每行「id · doc · action · 一句话」指向 proposed 块;re-verify 归并一行),不落盘;
  确认门守的是「approved 行不翻、phase doc 不动」。净效果:双写变单写,dev_root 总量净减。
- **decisions.md 模板细则**:proposed 块确认前可就地改写(git 留痕,016 已有实践),
  supersede-into-new-block 只约束 approved 块;why ≤1 段,更长论证归 doc §/ADR。
- 连带扫齐(invariant 6):SKILL.md M2 摘要与目录行 · design-grill.md trace 附件句 ·
  grill.md「restates verbatim」句 · README.md M2 句。

## 2026-08-05 — trace 矩阵三类假信号修掉(gate 仪表可信度)

- **加粗/删除线 id 单元格不再被漏读**(`trace_requirement`):条目表里 `| **R21** |`(新增条目的写法)
  与 `| ~~R16~~ |`(retired 行)都是 id 单元格,而正则只认 `| R21 |`/`| [R21] |` ⟹ 每个这样的行都被
  报 `not-in-需求条目`。发现于 longrun_test/002 的设计 freeze ask ——「设计 freeze 必须附 trace 矩阵,
  人读的是 R→design 列:一个没有设计落点的 R-id 是缺口」,而缺口列表里两条是工具自己造的假信号。
- **跨卡引用不再算本卡 id**(`XCARD_REF`/`_strip_xcard`):`001 的 R34` 是另一张卡的条目,被当作本地
  R-id 收割后,一张条目止于 R22 的卡凭空长出 R31–R36 六行、逐行报 `not-in-需求条目`。
- **retired 行不再报缺口**(`RETIRED_ITEM`):retired 条目按构造就没有设计落点/task/test,把它标成
  ⚠ 等于把已解决的行推到 gate 读者眼前。
- 三条共同的教训:**gate 仪表的假信号比没有仪表更糟** —— 它训练人忽略 ⚠。三条各配回归测试
  (74 → 全绿),因为都是「正则少认一种写法」这类最容易在下次重构中退回的缺陷。

## 2026-08-04 — retro(015 周期):新前缀接线 checklist;depends-on 占位归一

- **新前缀接线 checklist**(id-schemes.md Rules 新条):V<n> 前缀落地时提交自述「LEDGER_HEAD 是
  最容易漏的一步」却仍漏了 `_id_level`/decisions 模板枚举/回归测试三处(015 close-out review #2
  抓获,requirement 阶段的 V 引用失效检测曾静默失效);连同 (g) 检查落地时的 M3 枚举句义务
  (commit 2573df5 先例),「闭合枚举必须同批接线」已两例 ⟹ class-to-constraint,checklist 六项
  成文。
- **`depends-on: —` 占位在 parse 层归一**(parse_ledger 过滤 PLACEHOLDERS;decisions 模板头注
  明示省略):015 需求/设计两阶段各被 `--check` 打回一次——占位 `—` 在 design 级块出现后被
  `_id_level("—")→design` 判成 dangling id。与 norm_part/norm_blockers 同款「源头归一」。
- KB `viewer-architecture` 补「数据 API 两道准入门」(board 需 index.md;trace/diff 需项目注册
  ——2026-08-04 demo 卡三轮返工实证);roadmap 挂 loose-匹配收紧与存量账本 findings 判定两候选;
  KB compile backlog(cbdb/common/hashdata 各 2)属他项目 session,本 retro 明示 deferred。

## 2026-08-04 — 拆分发起机制化 + part 轴贯穿(card 015)

- **动机**: 三次真实拆分决策(longrun_test 001→002、hashdata 005 不拆卡、005→006 载体拆出)全部由
  人发起或 freeze 后偶然发现 —— 拆分执行机制齐全(card 001)而发起机制缺位;part 轴(design Parts 表
  → plan `Part:`)在 trace 矩阵与 viewer 里完全隐形。
- **发起侧(零新 gate,全挂既有停点)**: requirement 步骤新增必答的**拆分审视拍**(beat 8,结论落
  Scope 固定行、confirm digest 复述,不拆也留痕);design-grill 的 Parts bullet 改**双向** grill(向上
  逐 part 跑 A↔B 判定)且 freeze 前置清单加「Parts 表复核」;detail/implement 各加**探测句**(「装不下
  本卡/需独立核证」⟹ A↔B → M2 提议),change.md A.0 时窗扩为 freeze 后全程;split-isolate.md 新增
  **split-out procedure**(五步指针序列,R-id 承接 = M2 撤销 mode 实例);SKILL.md A↔B 判定补单向必要
  质量判据(seam 写不出具名契约 → 先 investigation)。
- **贯穿侧(part 轴数据契约,ADR-0001)**: Parts 表增 **`R` 列**(R→part 归属,多值;兼作**新格式标记**
  —— 无 R 列的 legacy 表全链路视作未拆,005 型卡零变化);`--trace` 三出口按 part 分组(pinned shape
  两定义点同批);viewer trace 视图分组行 + Tasks 表条件 Part 列;plan 按 part 组织升为 step 要求;
  `--check` 新增 **(h) part 一致性**(plan `Part:` ⊆ canonical 名集,仅新格式表激活)。
  未拆卡零加税:CLI 输出 byte 级不变(014/005 双卡对拍验证)。测试 68+23+71 项全绿。

## 2026-08-04 — 新增 `V<n>` id 前缀:判据共用定义进账本

- **动机**: longrun_test/002 的 Effect 有三个共用定义（`SNAP`/`TSUM` 及新增的 `CSUM`）被 7–12 条判据共用,
  而它们**没有账本行** ⟹ 改一个定义就要 supersede 每条引用它的 `R` 行（该卡是 8 行）,而那些行的**陈述
  其实没变**。给判据定义独立行后,一次定义变更只 supersede 一行。
- `references/id-schemes.md` 登记 `V<n>` = **verification-criteria definitions**（判据比什么、作用域、
  基数断言）,requirement 级账本行,Effect 以 `[V<n>]` 引用。
- `tools/workflow-status.py`: `LEDGER_HEAD` 与 `LEDGER_ID` 两处正则加上 `V\d+` —— 不加则 `### V1
  [requirement] proposed` 会被检查判成 `bad-header`（新前缀落地时最容易漏的一步）。测试 49 项全通过。

## 2026-08-03 — M3 新增 facts marker 完整性检查 (g);evidence.md 补两条载重断言形态

- **动机(事故)**: longrun_test/002 的 `F6` 以 `[VERIFIED]` 落盘,而它自己的 `来源` 栏写着「由
  [F1]+[F5] 的参数拼接位置推断(仍未实测)」。设计 grill 第 1 轮据它**结构性排除**了「复用 cb3x 起
  容器」这一整类方案;人工反问「为什么 cb3x 不行来着」后实测证伪 —— docker 标量 flag 后置覆盖,
  `--rm=false` + `-d` + `--restart=always` 全部可经 extra args 达成(记为 002 的 F34)。同类失误此前
  已两次(001 的 G2;002 的 F21 把两个事实的组合推论标成 VERIFIED),本次为第三次 ⟹ 从纪律层面升级
  为机械检查。
- `tools/workflow-status.py` 新增 **(g) facts.md marker↔来源 完整性**:`[VERIFIED]` 块的 `来源` 若
  自述推断(`由…推断` / `仍未实测`)无条件报;弱 hedge(`推断` / `未验证`)仅在 `来源` 无正向证据
  token(`实测`/`实读`/`已核`/代码反引号/wikilink)时报;superseded/retired 免检。`SKILL.md` 的 M3
  描述与 `templates/facts.md` 的纪律注释同步(并去掉 M3 里「on a ledger card」的限定 —— 该检查不
  依赖 ledger)。
- **校准数据**: 第一版宽匹配(扫整块 body)在 40+ 张真实卡上命中 3 条,经核**全是假阳性** —— 三条的
  hedge 词都在描述「本条纠正了哪条旧推断」(`取代早前推断级 F7` / `修正了…那条推断` /
  `001 的 F7 … 未验证`),那是应当鼓励的写法。收窄后:真事故 1/1 命中、全卡 0 假阳性。三种假阳性
  形态已锁进 `tools/test_workflow_status.py`(6 个新测试,套件 49 全通过)。
- `references/steps/evidence.md`:「Feasibility claims」新增**外部工具/运行时的行为断言 —— 跑一次,
  别推理**(该节原先通篇在讲「怎么把本仓代码读准」,从未覆盖「断言对象是可当场调用的工具」这一格,
  正是 F6 落空处);「最容易漏标的载重断言」从两种扩到三种,新增**「这条 alt 做不到所以否决」** ——
  否决理由与选择理由同等载重,且比被选中方案的前提**更危险**:被选中的会在实现里被检验,被否决的
  没有任何下游动作会碰它。`steps/detail.md` 的节名引用同步。
- **有意不去重**: `grill.md` 的 Recommendation pre-check #1 仍保留其一行清单式表述(它是检查触发点),
  完整规则以 `evidence.md` 为准 —— 把清单项改成跳转会在最该立即照做的时刻增加一次查阅。

## 2026-07-31 — 新增 park 动词:交接给新 session(resume 的写侧,014)

- **动因**: 用户需求「想增加一个交接给新 session 的动词,与 resume 对应」。写侧此前无动词
  承接——交接质量依赖各步骤随手维护 progress.md 的纪律,session-end hook 只兜底 commit、
  不校验自足性;M4 明言 prefer fresh-session resume,但「决定离场」到「可 resume」之间无 owner。
- **新动词 `park [<slug>]`**(`references/steps/park.md`,authored inline): 离场四拍——
  1 容器分流(决策/事实/KB/grill-log/pending 审计行→log.md/Unit-registry 欠账,progress.md
  是唯一入口非唯一容器)→ 2 progress.md 校验补全至 resume 自足下限(mid-grill = grill.md
  round-end order 提前收口并强制持久化 grill-log;mid-task = 半成品只记不动)→ 3 M3 +
  scoped commit → 4 收尾回复 = receipts + 末行 `resume <slug>` 启动指令(+execution zone
  可选模型建议)。不变量: product tree 逐字节不变、看板/派生 status 不动、幂等、不新增交接
  文件。人发起,Claude 仅建议(护 M4 unbroken-window)。
- **Wiring 八落点**: SKILL.md(Verbs/M4/description 触发词)、README、grill.md ×2、
  resume.md 互引、provenance.md、KNOWN_ACTIONS ×3 同步。
- **验证**: 双形态 dogfood 于本卡自身——execution zone 真离场(E1 零上下文 subagent 凭一行
  指令完整复述现场)+ mid-grill fixture(续 open G99、不重问 resolved G98);E1–E8 全绿。

## 2026-07-31 — gate digest 版式改版:「Grill / 自检状态」领段 + 卡片分行 + 全段 list 化

- **动因**: 用户在 014 设计 freeze gate 现场试用后拍板("先按这个订吧,用一段时间看看")。
  旧版式把 why/alt 压进卡片同一行、段落体呈现,读 gate 时判断点不易定位; 且收敛判定
  ("还要不要继续 grill/自检齐不齐")散落在 digest 之外,人要自己拼装"这份 ask 够不够格判"。
- **改动** (`steps/gate-digest.md` The-digest 节重排, 7 段固定序):
  - 新增**领段「Grill / 自检状态」**: 收敛判定 + 必做自检清单(panel/lens-4/micro-check/M3,
    每行带 receipt 指针——吸收原「已验证(勿复核)」段职责) + 一行结论(可判/欠什么;
    欠→先补,ask 不可摆出)。
  - **卡片固定版式**: 加粗头行 `[<id>] <一句话陈述标题>`,陈述/why/alt(拒)/锚点各占一
    sub-bullet 行,禁止压行; 其余 pending 行仍以`其余 pending(一并批)`清单跟出。
  - **全段 list 化**(doc-conventions structure-over-paragraphs 应用到 chat digest);
    gate ask 段明示 partial approve 合法。
  - 同批回填(invariant 6): `adversarial-critic.md` Receipts 段的 已验证 引用改指领段。
- **语义不变**: panel-receipt 前置、枚举表 paste 规则、自包含规则、--trace 附带、
  approve transcription 全部原样; 纯呈现层改版。试用期观察,M6 retro 复盘。

- **动因**:cbdb card 006 的跨 session 复盘(其 notes/review-2026-07-30-retro-second-opinion.md)。
  需求 grill 用 5 条 DDL 探测关闭了「按写者轴逐核 7 个写点」的判据(键被换掉、Effect 自勾
  「已完成 5 条」),confirmed 的需求带着自相矛盾进入设计;设计 G6 的完备性核查又按方案形状
  枚举(`ATController` 入口而非 `finish_heap_swap` 调用者)。且整个需求+设计周期
  **零次 fresh-context panel 派发** —— 机制在文档里,执行被跳过;两道 gate 收到的都是结论
  而非可核对的表。用户四问后设计换向、代码返工六次。
- **Enumeration-criterion key fidelity** — 枚举型 Effect 判据在判据文本里声明**枚举键 + 必填列**
  (`templates/requirement.md` Effect note · `steps/requirement.md` #6);fold-in 不得换键,
  异键结果只算 partial evidence 且必须点名未核行(`steps/grill.md`「Key fidelity on fold-in」);
  关闭判据只能靠全行齐的表,禁「已完成 N 条」。M3 新增 well-formed 核查项(异键的满表也 fail)。
- **Criterion-conformance judge (lens 4)** — `steps/adversarial-critic.md` 新增 gate-adjacent
  第四 lens:输入只有 `{判据原文, 制品}`,逐条裁「要求的产物是否存在、键是否一致、行是否齐、
  行行有据」,不接受制品自称的 done;四个 decision-zone gate ask 前必跑(requirement confirm
  对本阶段 claimed-closed 判据;design freeze 对需求条目+Effect;详设 baseline 对 design
  决策/契约的覆盖声明;execution authorization 对 plan 的 R-id/design↔task trace ——
  后两个阶段无 grill,lens 4 是其唯一派发),挂点已接入 requirement/design-grill/detail/plan
  四个 step 文件与 change.md 的 re-freeze(按变更范围 scoped)。
- **Panel receipts as gate precondition** — 每次 panel 派发留一行 receipt(checkpoint · lenses ·
  verdicts);gate digest 的「已验证」段只收带 receipt 的行,decision-level checkpoint 无 receipt
  → gate ask 不可呈(`steps/gate-digest.md` 新规 + `steps/omission-check.md` 新核查项,
  2026-07-30 前的 gate 豁免)。枚举型判据在 digest 里**贴表不贴结论**。
- **Coverage inherits the requirement's enumeration** — `steps/design-grill.md`:方案完备性辩护
  枚举的对象必须是需求枚举表的行(同键加列),不得由候选方案的形状反推枚举集合。
- **两条机械化跟进(同日,同一动因)**:(1) `workflow-status.py --check` 新增检查 (f) ——
  design.md 无条件必备节(思路/速览/How-it-meets/影响面)的存在性,不依赖 ledger,
  created < 2026-07-31 的设计 grandfathered(006 的 design.md 徒手写就、整卡零次 M3,
  必备节全靠残留记忆,「How it meets」就此丢失);条件节(验证策略/存储足迹/图)留在
  judgment 子集。(2) 设计 freeze ask 必须附 `--trace` 覆盖矩阵(`steps/gate-digest.md`),
  freeze 时 task/test/commit 列合法为空,人看的是 R→design 列的空洞。

## 2026-07-30 — Recommendation pre-check 扩到四条(价值归属 + 载重前提)+ 提交前验证对象(card 008 / hashdata)

- **pre-check 第 4 条「价值归属」**(`steps/grill.md`)—— 提案必须点名「谁需要它、不做会怎样」;
  只以「让设计更自洽」为最强论据的提案不通过。附推论:规模不同的选项**不得**排成
  minimal/medium/complete 阶梯 —— 阶梯暗示 more-is-better,把「要不要」偷换成「要多少」。
  **动因**:hashdata card 008(GetRangeSize 估算回落)。实测给出两档毛病 —— 8.4 KB 报 0、
  42 KB 报 100 KB(2.39x);我把它们当同一问题的两个程度、排成三档递进方案并推荐「四步全做」,
  推荐理由是「硬上限让阈值可以自由选,两者配套更好推理」(自洽性论证,不是价值论证)。
  人在需求 gate 上做了框架内能做的最大收窄(否 R1、把 R2 并进 R3),但 R3 是框架层面的问题、
  收窄不掉 —— 直到实现完看见 50 行代码 + 四个包级 var 才被否("是不是太复杂了")。
  返工:50 行 → 35 行,删 4 个 var + 整套 unit 公式。事后才想清的区分(已进 KB
  `wiki/hashdata/fdb-range-size-estimation`):**假 0 是语义错误(会被读成「索引是空的」)必须修,
  2.39x 是精度不足、无人需要** ⟹ 判据的分辨率只需匹配「会被误读的输出」。
  教训的落点是**选项呈现方式**,不是「需求阶段要更严」—— gate 只能审摆上去的框架。
- **pre-check 第 1 条从「comparative claims」加宽到「载重前提」**(同文件)—— 明确含**可行性前提**,
  且「靠试,不靠推理」。**动因**:同一天 usage log 另一条 requirement 记分 2 ——
  两处方向性决策被人推翻,根因「未验证前提就下断言(没先试 extra args 能否满足需求、
  没先查宿主有无 psql)」。与 008 合看是同一模式的两次:**R 条目在缺少某类必要支撑时被写下并过
  gate**(一次缺前提验证、一次缺价值论证)。原第 1 条只覆盖「比较性断言」,盖不住可行性前提。
- **提交前验证对象**(`steps/implement.md`)—— build/test 绿证明不了 commit 内容;
  index 与 worktree 可能分叉时(典型:`reset --soft` 之后 index 留的是**旧**内容)
  必须查 staged/committed 的 blob 本身(`git show :<file>` / `git show HEAD:<file>`)。
  **动因**:card 008 实现末期 `reset --soft` 后漏 `add` 就 commit,提交的是未简化版;
  随后跑的 build/test 针对 worktree(简化版)全绿,正好掩盖了这件事,靠人追问「没有 amend 吧」
  才暴露。
- **Pruning**:同时想加在 `steps/requirement.md` 的「pre-check 在写条目前跑完」指针被砍 ——
  pre-check 的措辞本就是 "Before recommending",该指针是重复。

## 2026-07-30 — improve verb(存量巡检)+ module-depth 留痕核验 + review depth 判据(card 013)

- **New `improve <project> [<region>…]` verb** — read-only deepening scan: region check
  (>200 source files without a region → refuse, never sample), KB-vocabulary-informed friction
  probes + deletion test, per-candidate fresh-context refutation (sonnet; uncertain →
  weakened), negative-list conflict matching against all cards' accepted ADRs/ledger
  (clear conflict → suppress or mark `contradicts <id>`; doubtful → `possible-conflict`, never
  suppress), in-flight-card hints; report → `investigations/improve-<scope>-<date>.md`; the
  only exit is roadmap Next-up (no card creation). *Why:* the improve-codebase-architecture
  bare-run proved the method but hit an accepted ADR it couldn't see — negative list and
  refutation are what make candidates trustworthy (013 [F2]/[F4]; first E2E: 8/8 candidates
  demoted or scope-narrowed by refutation — 6 demoted, 2 narrowed, 0 refuted outright,
  0 false kills).
- **Module-depth record now verified, not hoped-for** — design template gains a
  Design-qualities line (deletion-test conclusion + seam adapter count per new/extended
  module), design-grill's Module-depth lens now instructs writing it, and omission-check
  flags structural cards missing it (deterministic exemption: frozen designs or created
  before 2026-07-30). *Why:* the lens existed since dbac5b3 but only ran in chat — silently
  skippable, M3-invisible.
- **Review depth criteria** — review-deep quality/simplify adds locality
  (tested-helpers-around-untested-orchestration) + single-adapter-seam families;
  simplify-checks gains item 3 (deletion test + locality), carried automatically by both its
  consumers (review Standards axis and implement's simplify sweep). *Why:* locality was
  absent review-side; deep tier alone misses most diffs.

## 2026-07-29 — 设计期主导流程按位置追问 + data-flow 图必须走完一条流程

**动机**: 设计阶段对异常侧是三处明文强制(Core values 异常完整性 · Design qualities · detail 的
边界与错误矩阵),而 normal flow 只在「哪个是难点」一句里被侧面提及,既无产物也无检查——非对称。
且"哪条流程主导"本不是全局一个答案: 不同 层/模块 可以各选其一,每种选择让另一条流程付出的代价
不同。落地取**收紧已有句子**而非新增节/表(一张 per-module 表会变成填格仪式,并给模块加第 4 条税)。

- `templates/design.md`:「Diagrams」的 data-flow 由"数据关系视图"收紧为**端到端走完一条被点名的
  流程**(normal 或设计所攻的 dominant anomaly);静态关系图不再满足——走查才能显示契约串得起来。
  「Alternatives considered」那句改为: 说明哪条流程主导、**positions 不同则按 层/模块 分别说**、
  并说**该选择让另一条流程付什么**(异常主导的设计仍欠正常路径一句话,反之亦然)。
- `references/steps/design-grill.md`: Core values + 方案优先 lens 均改为**逐 层/模块**追问难点在
  哪条流程,并要求 lens 里给出每种策略对另一条流程的代价;新增**塌缩检查**(把 deletion test 用在
  拆分本身: 全设计统一成一种策略,若无可度量的变差就统一)——防"因地制宜"退化成不一致。
  Diagrams 小节同步为 data-flow walk(跨文件复述保持一致)。
- `references/steps/omission-check.md` Design completeness 同步收紧(检查 data-flow 是否走完一条
  被点名的流程),不新增检查项。

## 2026-07-28 — retro(012): 压缩编辑先列语义点 · requirement 消费已批笔记 · --check 空 depends-on 修复

**动机(card `xg-skills/012` 当日复盘)**: (1) T4 字面精简误剪 go-等效授权半句,评审双轴抓回
——R5 有语义点清单而 R4 全面无清单,是方法学缺口;(2) 本卡需求期把 grill 折进 gate digest
(scope 已获本 session 明确 go),流程顺畅但无明文依据,补成规则;(3) 需求期实地踩中
`workflow-status.py --check` 误报: 空 `- depends-on:` 行经 `\s*` 跨行吞掉下一行,判为
dangling-id(模板本说 "or omit the line",解析器应双向健壮)。

- repo CLAUDE.md editing conventions 新增: trim/compression edits list semantic points first。
- `references/steps/requirement.md` step 1 新增: ask born from an approved analysis note 消费
  该笔记、只 grill 其余留(design-grill「pre-design」的需求侧 sibling)。
- `tools/workflow-status.py` parse_ledger deps regex `\s*` → `[ \t]*`,附回归测试(38 tests OK)。

## 2026-07-28 — 012 常驻面瘦身: SKILL.md 447→351 行,写作细则下推 doc-conventions.md

**动机(card `xg-skills/012-skill-context-rightsizing`,源: Claude 5 context-engineering
原则审计)**: SKILL.md 每次唤起全量加载,而其中写作规约细则、Ledger 机制展开、verbs 对
step 文件的复述只在特定时刻需要——把常驻/按需的分层线下移,机制是**锚点稳定压缩**
(被 `SKILL.md「…」` 引用的 heading 全部原地保留)。

- 新增 `references/doc-conventions.md`(gloss / 链接三规则 / provenance-F 容器 / Reasoning
  shown / Reader-aware / 短行 / 结构 vs 段落 的单一 owner);SKILL.md Conventions 留 13 行
  常驻要点+指针,措辞「read it before writing any workflow doc」——显式覆盖 investigation/
  review notes 与 KB 注记,不只 phase docs。6 处规则级引用改指新 owner。
- Ledger 章压至 9 行契约;rewritable-views 机制归 `templates/decisions.md` 头注;
  pre-010 fallback 一行留守常驻(无账本的卡不会打开 decisions 模板)。
- verbs investigate/diagnose/review 压至 2 行 front-door 契约;Layout 注释、五阶段段落、
  Subagent/Versioning/References 等段删解释性文句;usage-logging 的 verb 枚举改指
  `KNOWN_ACTIONS`(脚本为词表单一 owner)。
- 模板示例规则入册(repo CLAUDE.md editing conventions + retro.md 半行指针):
  contrast-pair 优先 / ≤6 行 / 标「示意」;存量 11 处示例 10 keep(思路 pair 补标记)/
  1 delete(Alternatives filled sample,其 Why-rejected 要点并入字段行)。
- 落点 351 行(-21.5%),未达卡片 ≤325 验收线:剩余余量在契约项上,压缩即损义——按 R8
  「无损优先」停手;差额裁决见卡片评审。

## 2026-07-28 — 三处「信息已在手却没对照」的失败,补三条察觉机制

**动机(card `hashdata/006-meta-vacuum-on-v311`,详设阶段五轮压测)**:同一形状的自我推翻出现
**三次**,且三次做出正确判断所需的信息**都已在手**,只是没被放在一起对照:

1. `reads` dump 段的立论 —— 断言「重切 range ⟹ 键集合变而计数不变」。实际区间连续按序分发,
   重切后键序列逐字节相同。我读过 dispatcher,没推演那个场景就把它写成了机制的理由。
2. `ops` dump 段的顺序语义 —— 断言「按生成顺序,顺序即语义」。实际 toast 的 op 顺序由
   `toastCache.LoopAll` 的 **map 遍历**决定(Go 随机化);我通读过该文件。
3. rocksdb fixture 的不可变性 —— 为「原目录从不被打开」这个目标选了 **checkpoint**,
   而 `NewCheckpoint()` 是 `*DB` 上的方法、**必须先打开源库**。签名我查过并抄进了文档,
   与目标句相隔二十行,没碰到一起。

三者的共同结构:**缺一个对照动作**,不是缺信息;而现有规则(M1 的标记制度、方案优先的
provenance 列)都假定「你知道自己在下断言」。

**改动**(均为 step 文件,行为级):

- `steps/evidence.md` —— 新增「两种最容易漏标的载重断言」:「这机制能抓住 X」(为机制编的使用
  场景本身是运行期断言,写下前须在代码里推演一遍)与「这个序列有序/去重/稳定」(此类属性只能从
  **产生者**的代码读,不能从用途推)。补的是**察觉**,不是标记规则本身。
- `steps/design-grill.md` —— 方案对比表新增 **前提/要求列,且排在收益列之前**。收益是你本来就想要
  的、有动机去看;前提是它跟你要的,最容易略过。专门针对「为目标 G 选的机制,其前提违反 G」。
- `steps/detail.md` —— 新增 **baseline 前的最小压测清单**(前提先于收益 · 顺序类断言指向产生者 ·
  目标句与手段句两两对照)。该步原有的收敛信号只说「何时停」,没说「至少压什么」;而详设正是
  机制第一次获得前提与顺序性质的地方,这些恰恰是设计层读不出来的。

**校准数据**:同一 card 的详设阶段,我两次判定「不必再 grill」,两次均被随后由人指定的压测推翻
(5 轮压测中 3 轮推翻了我前一轮刚写下的结论)。⟹ 自评「问不出更多了」不可作为收敛依据;
上述清单给出的是**机械可执行的下限**,与主观判断脱钩。

## 2026-07-28 (card 011 MS1 — cross-reference backfill + process rules)

Source: the 2026-07-27 template-explicitness audit (three-agent sweep) found 16 broken/drifted
cross-doc hand-off edges, ~10 orphan template sections, and dangling references — root cause:
two structural evolutions (详设 phase, the 010 ledger) landed without backfilling references.

- **Backfill discipline made mandatory** (repo CLAUDE.md Cross-file invariant 6 + retro sweep
  upgraded): structural edits grep both skills for stale references in the same batch; new
  template sections must be wired to a filling step or marked optional. Why: the rule existed
  only in retro.md and never fired on either evolution.
- **Hand-off repairs**: concrete-code deferral now points at detail.md「代码级接口」(was
  plan.md, 4 sites); test-case home narrowed to test.md; dead 阅读稿 promise removed; progress.md
  gains `Build/test:` / `Close-out:` slots with all four write sites naming them; test template
  gains a 回归 sub-section fed by design 影响面; assorted pointer fixes (Symbol budget,
  board column name, resume/board wording, design status enum drops `approved`).
- **010 ledger propagated to the producing side**: detail template carries three-class marking +
  `S<n>` entry hint; adr template gains 被取代表述 section + derived-Status note; `F<n>` defined
  as a per-container scoped id (card → facts.md, standalone doc → doc-local 事实清单; never
  both); "R12" references replaced by the named **derived-status rule** homed in SKILL.md;
  grill gains 载重事实入账 (the facts.md write path, bounded against the verified-facts pack).
- **Promised checks got executors**: close-out review verifies the design's 验证策略 scenarios
  ran (per-row verdict); M3 design completeness now covers 速览/验证策略/存储足迹; orphan
  sections wired into design-grill (速览 regenerate, Design qualities/Risks/Understanding/
  存储足迹 by name); roadmap Rejected got its write side; log type tags + test/plan status
  setters named.
- **Gate digest rules** (from live gate feedback on card 011): cards written for comprehension;
  decision-object references self-contained (inline or linked; evidence refs exempt) at both
  the digest and the ledger write layer; every gate ask carries a 判断分工 split — 已验证
  (don't re-check) vs 待你判 (owner trade-offs with stakes).
- **test.md is now skeleton-first**: seeded at plan authorization (coverage from 验证策略,
  regression from 影响面), Unit registry appended one line per implement slice, 测试 becomes
  close-out instead of end-of-phase reconstruction. Why: retrospective inventory is an
  omission breeding ground — the same defect class this card repairs in the templates.
- **Micro-examples in the ten highest-variance gate-reviewed sections** (each ≤6 lines, marked
  示意): design Chosen approach / Understanding get good-bad contrast pairs, 影响面 /
  Alternatives / 验证策略 / Interface contract (now with fixed columns) / requirement Context /
  decisions 陈述 / detail mechanism / plan Acceptance get filled examples. Why: the audit found
  22 sections where "how good is good" was adjectives only — the two pre-existing examples
  (design 思路, KL FORMAT §3) were the only variance dampeners.

## 2026-07-27 (card 010 — decision ledger: gate currency moves from documents to decisions)

The largest contract change since the two-zone model. Motivation: gate reading exceeded the
approver's bandwidth (gates degraded to grill-trust) and design changes carried
document-granularity ritual (supersede ADR + sweep + re-grill + re-freeze felt like "一下就
都做了"). Full derivation: dev_root xg-skills/010-decision-ledger (R1–R12, G1–G16, ADR-0001/2).

- **Per-card `decisions.md` ledger** (templates/decisions.md): one block per human-judgment
  decision (requirement 条目 · design D/ADR · new 详设 `S<n>` ids · execution-zone
  escalations); states proposed/approved/superseded/retired — freeze/baseline are binding
  *forces* derived from level, not states. Single-active-block; in-place edits whitelisted
  (state word, approve/supersede notes, 澄清 note); `approved:` cites the gate receipts
  commit (auditable via git; Claude never self-approves).
- **Gates approve rows, not documents**: gate-digest cards are generated from pending rows
  (why excerpt + alternatives, never a bare pointer; the 3–5 ceiling caps emphasis, all
  pending rows disclosed). Doc status fields become derived (confirmed/frozen/baseline ⇔
  level fully approved; ADR Status line = display snapshot).
- **Docs become rewritable views**; card-local facts move to `facts.md` (`[F<n>]`) so
  rewrites can't lose them; phase docs mark three content classes (decision refs / fact refs
  / synthesis prose).
- **M2 shrinks to reopening a row**: escalation persists as a proposed row (gate-at-entry
  exemption); 修改列表 (dependency-closure + trace ripple) confirmed by the human before any
  write; targeted re-grill scoped to the closure.
- **Tooling**: `workflow-status.py --check` (id integrity · R12 mappings · dep cycles ·
  approve-note format · single-active-block; exit 1 = findings, self-caught exceptions);
  card_status/trace/viewer show 待评审(n)/decision rows; pre-ledger cards byte-identical
  (two degradation axes: no file → legacy; level without blocks → frontmatter fallback).

## 2026-07-27 (retro — process/design/grill quick-fix batch from user's 10-idea list)

Source: the user's raw 10-idea list on process/design/grill friction, organized in
`dev_root/xg-skills/notes/2026-07-27-process-design-grill-ideas.md`. This batch lands the four
no-contract-change items plus two trial wirings; the big items (iteration model, M2 gates,
de-freeze) are parked as decision-ledger MS2 grill input (roadmap).

- **Structure over paragraphs** (SKILL.md Writing style): parallel/enumerable content goes in
  nested lists, one point per bullet; paragraphs reserved for chained reasoning. Why: gate
  reading is scanning — long prose paragraphs exceeded the approver's reading bandwidth (the
  standing gate-bandwidth feedback), and "plain prose" was read as a bias toward paragraphs.
- **Module 归属 tag** (design template, Chosen approach): each module is classified 复用已有 /
  已有扩展 / 全新; feeds 影响面 and the 详设-necessity call. Why: user asked "涉及到哪些已有
  模块,自己是新模块,还是之前模块的一部分" — the template had module lists but no provenance
  classification.
- **Whole-doc rewrite at convergence** (grill.md Fold-in): at 建议收敛, judge the doc's shape
  as if written fresh; patched shape → one content-preserving rewrite (with the 改写时澄清
  checklist, mirroring change.md). Why: user reported multi-round grills leave the doc
  patch-shaped ("多轮 grill 之后,需要重写文档"); per-round fold-in fixes sentences, not shape.
- **假设 closure sweep** (design-grill freeze gate + plan.md cross-check): every load-bearing
  假设/推断 marker is discharged pre-freeze or explicitly carried with a verification home
  (验证策略 row / plan verify task). Why: user asked for "假设和求证" — markers existed but had
  no lifecycle; an assumption could ride to implementation untracked.
- **试行 (trial — evaluate after one card, then solidify or drop):** (a) pre-draft discussion
  window (grill.md Protocol) — first rounds of an open-shaped phase may run doc-free, write the
  doc once direction stabilizes ("写文档前缺少一个讨论过程"); (b) candidate side-by-side table
  (design-grill 方案优先) — present competing approaches as one compact comparison table in the
  round message, archived in Alternatives considered ("设计的候选方案").

## 2026-07-24 (comprehensive skill audit vs writing-great-skills — Sediment/Duplication/Sprawl sweep)

Audited both skills against their `~/.agents/skills` fork sources and the `writing-great-skills`
standard (six read-only lens agents, one per fork cluster). Verdict: the structure is healthy and
the forks are actually *condensed* against real source material (~0.22–0.32x for the build
cluster) — the accreted bloat is not size but three failure modes: **Sediment** (dated incident
anecdotes inlined as justification), **Duplication** (one meaning restated across SKILL + step +
template), and **Sprawl** (branch-specific reference resident in every-load files). Root cause:
the M6 retro kept writing the motivating incident into the step body instead of the CHANGELOG.
Landed in phases (P0–P3).

### P0 — Sediment sweep + retro policy (the root fix)

- Stripped ~40 dated incident anchors (`(Learned YYYY-MM-DD: card-NNN …)`, retro / calibration /
  transcript notes) from SKILL.md and the step files (grill, requirement, design-grill, review,
  adversarial-critic, implement, test, detail, investigate, change, gate-digest). Every rule an
  anchor justified is kept; a few load-bearing insights were folded into the rule sentence itself
  — e.g. test.md "an all-int suite can silently keep a type-specific wrong-results path green";
  review.md "an embedded shared sub-expression evades a whole-function dup scan"; grill.md's
  mechanism list gained the missing **convergence** item. The 2026-07-04 grill anchor that
  `adversarial-critic.md` cited four times is now recorded once — here.
- Dropped an `implement.md` negation ("never filter build output to errors only" → keep the
  positive "surface warnings on every build" with its undefined-symbol why-note) plus two
  intra-file duplications; compressed `adversarial-critic.md`'s over-argued parallel-dispatch cost
  rationale to one sentence.
- **`retro.md` anti-sediment policy strengthened — the actual root-cause fix.** Added *"Rule in
  the body, evidence in the CHANGELOG"* (the motivating incident's date / card-id / calibration
  data goes to the CHANGELOG entry, never inlined as `(Learned …)`; if a rule is opaque without an
  example, keep a bare undated one) and *"Prune your own additions first"* (run the No-op /
  Duplication / Sediment tests on the lines the retro just wrote). Step 5 now names the CHANGELOG
  as where the incident lives.

### P1 — Sprawl disclosure (progressive disclosure to on-demand references)

Branch-specific / consult-when-naming reference that was resident in every-load files moved behind
context pointers, per `writing-great-skills`'s information hierarchy — the main files keep only
what every branch needs:

- SKILL.md's **Fixed ID prefixes** block (24 lines) → `references/id-schemes.md`; SKILL keeps the
  core five (`NNN`/`ADR-NNNN`/`R`/`T`/`M1`–`M6`) + a pointer.
- `review.md` **deep-tier machinery** (lens fan-out menu + per-lens model assignment, standing
  model-diversity sweep, 5b saturation stop-rule) → `references/steps/review-deep.md` behind a
  hard must-read pointer at the deep branch (252 → 170 lines); light/standard now resident-only.
- `design-grill.md` **Mermaid gotchas + ASCII CJK-width alignment** (~24 lines — the fallback path
  that dwarfed the recommended prefer-Mermaid one) → `references/diagram-gotchas.md`; the SKILL.md
  and design-template pointers retarget to it.
- `test.md` **browser + mobile real-device** testing → `references/frontend-testing.md`
  (branch-specific; backend projects no longer load it).

(xg-knowledge-lite's parallel Sprawl/Duplication cleanup is recorded in its own CHANGELOG.)

### P2 — Duplication → single source of truth

One meaning, one home; the other sites became pointers (writing-great-skills「single source of
truth」):

- **Shared elicitation tactics** (sharpen-language, stress-test scenarios, grep-before-accepting,
  fresh-context adversarial panel + tiered dispatch) now live once in `grill.md`'s new "Shared
  elicitation tactics" section; `requirement.md` and `design-grill.md` keep only each phase's slant
  + a pointer — changing a tactic is now a one-file edit.
- **Investigate cluster** canonical homes nailed: M1 discipline → `evidence.md`, M5 / Synthesis
  lens → `understand.md`, single-front-door recording branch → `investigate.md`. `investigate.md`
  keeps a 4-point M1 preload and points to evidence.md for the detail; `understand.md`'s duplicated
  "open-question investigation loop" (which also contradicted the single-front-door rule) is gone,
  replaced by a pointer; evidence.md's model-cost paragraph trimmed to its carve-out + a pointer.
- **simplify-sweep reuse/cohesion checks** — the pair that each self-admitted "keep the two in
  sync" (`implement.md` ↔ `review.md` Standards axis) extracted to `references/simplify-checks.md`;
  both now point to it.
- Scattered constants folded to their authority: task-churn logging → M2 case B (`change.md`);
  binary-verify `[x]/[!]/[ ]` → `implement.md`「Binary verify」; the board monotonic constraints →
  `omission-check.md`「Board (kanban) consistency」 (`split-isolate.md` + the index template now
  point to it).

### P3 — project-name generalization + leading words + description trim

- **Project names generalized** — generic step files and templates that treated `cbdb` as the
  default project now frame the rule as the *project's*, with cbdb demoted to an "e.g." example
  (the "describe, don't run" test policy, change rules, retro classification target); the
  cbdb-specific `FloorTable` schema placeholder in plan/detail became a generic `<SomeTable>`. The
  load-bearing "describe, don't run" test-mode distinction is preserved; patched-fork examples
  (Greenplum/Cloudberry on PostgreSQL) stay as concept illustrations.
- **description trimmed** — SKILL.md frontmatter drops the identity clause already in the body
  (the phase pipeline + "one card dir"), keeping the leading word + per-branch triggers
  (writing-great-skills「Cut identity that's already in the body」).
- **Leading word restored** — `diagnose.md`'s Phase 1 regained the "be aggressive / don't give up"
  mobilization from the `diagnosing-bugs` source (the default drift is to read code for a theory
  before the feedback loop exists).

Adjudicated / deferred: (1) **CONTEXT-MAP — verdict: keep self-contained** (not a real cross-skill
duplication; it's load-bearing across 6 steps + M3, and `domain-modeling` is never a dependency of
this repo — full reasoning in xg-knowledge-lite's CHANGELOG). (2) **Done** — adopted the Fowler
12-smell names as leading words: new `references/smell-catalog.md` (the 12 smells + the
repo-standard-wins / skip-tooling-enforced binding rules); the deep-tier quality lens now names its
families with them (Speculative Generality / Duplicated Code / Middle Man) and points to the
catalog, and the standard-tier Standards axis falls back to it where the repo documents no
convention.

## 2026-07-23 (design-doc readability: fold-in, prose-for-reasoning, F-list provenance — hashdata card 005)

Seven grill rounds left hashdata/005's design.md archaeological — layered dated corrections,
superseded plans in the body, reasoning compressed into table cells (three "what does this cell
mean" user round-trips; user verdict: 凌乱、有的地方过于简略). A freeform rewrite read better;
these fixes make the template version read well without losing the process anchors
(full analysis: card 005 `notes/retro-2026-07-23-design-doc-readability.md`):

- `grill.md` gains **Fold-in (压实)**: each round's correction rewrites the phase doc's live
  text; process history goes to grill-log/Change log only; superseded alternatives leave the
  body (verdict + pointer); no stacked dated corrections. The append-only supersede discipline
  is explicitly scoped to the grill-log.
- SKILL.md conventions: **tables carry facts, prose carries reasoning** (a table cell is a
  label — its rationale must be prose in the same section; folded into Reasoning-shown);
  **provenance 集中制** — optional per-doc `F<n>` fact-list cited as `[F<n>]` (new ID prefix);
  **symbol budget** — a prime evolution survives one generation, the next supersession renames;
  a second staging scheme must declare its mapping and avoid ID-letter collisions.
- `templates/design.md`: fixed **速览** first-stop section (terms + staging-vocab map + open
  gates; regenerated, never appended); body declared current-state-only; optional one-shot
  freeform 阅读稿 at freeze (never co-maintained).
- `design-grill.md`: Mermaid gotcha — ASCII `;` is a statement separator inside diagram text;
  use fullwidth punctuation and grep mermaid blocks for `\x3b`.

## 2026-07-21 (commit-data-repos scoped to project — card 008)

Two parallel Claude sessions working different projects could pull each other's still-uncommitted
docs into a gate commit: `commit_repo()`'s `git add -A` had no path scoping at all, so any dirty
file anywhere in the repo rode along regardless of which project the commit was for. Two
same-day accidents surfaced it (a postgresql/004 gate commit pulling in xg-skills/007's `design.md`
+ notes, and a vagrant-qemu/002 gate commit pulling in xg-skills/007's `log.md`).

- `commit-data-repos.py` gains `--project <name>`: commits only that project's paths in both data
  repos (dev_root: bare project-name prefix; KB: `raw/<project>` + `wiki/<project>`), scoped on
  **both** `add` and `commit` — scoping only `add` would still let a path a concurrent session
  staged in its own add→commit window get swept into this commit at commit time. Paths outside the
  scope stay uncommitted, warned rather than silently dropped.
- Without `--project` (the session-end safety-net sweep), dirty paths are now grouped by project
  and committed one group per commit (message suffixed ` [<group>]`) instead of one whole-repo
  commit; unowned stragglers land in a `(root)` group. Existing `--message`/`--reason`/`--only`
  behavior is unchanged.

## 2026-07-21 (sweep substance + a standard-tier reuse lens — follow-up to the card-005 retro below)

vagrant-qemu card 002 hit the **same class** the card-005 retro (below) had just addressed —
manual-review-caught reuse/cohesion, not bugs — but through the residual gap that fix left:

- The simplify-sweep gate checks that the sweep **ran** (or a skip is recorded), not that it had
  **substance** — a sweep executed as a one-line comment/lint nit satisfies the gate while doing no
  reuse/cohesion work. Two misses reached the human: a new `homebrew_prefix` helper duplicating the
  `arch→prefix` logic already in `default_qemu_dir`, and a `preflight` special-cased with
  `if net_mode == :socket_vmnet` in the driver instead of reusing the backend-hook shape the same
  change had just built for `launch_prefix`.
- The **standard** review tier's three axes (spec · convention · invariants) have no reuse/cohesion
  lens; the close-out review confirmed correctness cleanly and still missed both. An embedded shared
  sub-expression (not a whole-function dup) also evades a quick dup scan.

Fixes, minimal-diff (sharpen the existing sweep + fold into the existing Standards axis — no new
blocks, per anti-sediment):
- **Simplify sweep now carries a concrete reuse/cohesion checklist** (`implement.md`): new helper →
  grep the touched module for the same logic first; new cross-cutting concern → match its just-built
  sibling's shape (hook, not caller special-case). A comments-only sweep diff on a change that added
  abstractions is declared "didn't run" — state the reuse/cohesion checked, not just "swept".
- **Standard review tier gains a reuse/cohesion check in the Standards axis** (`review.md`): the same
  two named checks, so it isn't only correctness + convention.

## 2026-07-21 (review fix-application must sync test.md + run M3)

`review.md`'s fix-application clause said only "each fix is committed" — silent, at the site
where fixes land, on updating `test.md` for a behavior-changing fix. Applying fixes as a quick
commit batch bypasses implement's per-slice test-write, and M3's test-consistency check fires
only if actually run after the edit; the two blind spots combined let 6 card-005 review-fix
commits change behavior with no `test.md` coverage row until the human noticed. Added one line
requiring a behavior-changing fix to update `test.md` (coverage row + suggested-verification)
like an implement slice and then run M3. (Mostly an execution miss of existing mechanisms — the
addition just names the obligation at the one place the fix-application flow lives.)

## 2026-07-21 (pin the base ref for review + simplify scope)

Both the close-out review and the implement simplify sweep said they cover "the whole change"
without defining what that's measured against — ambiguous for a card whose implementation spans
many commits across sessions (the trap: basing on the latest session's slices silently drops the
earlier sessions' commits from the sweep/review).

- **`review.md` step 1 now pins the base ref** and requires stating it in the report: the human's
  explicit range/PR wins; a close-out gate bases on the card's **integration point**
  (`origin/<main>` / its merge-base); a **repeat** review is incremental from the tip the last
  `notes/review-*.md` covered (each report records its reviewed-through SHA); ad-hoc uses what the
  human named.
- **`implement.md` simplify sweep** defines "whole change" as the card's diff vs that same
  integration point, with the concrete `git diff $(git merge-base origin/<main> HEAD)..HEAD`.

Why: without a pinned base, cross-session cards get partially-reviewed/partially-swept — exactly
how the card-005 quality issues (previous entry) reached manual review.

## 2026-07-21 (catch quality/altitude issues earlier — prevention default-on + a merged review lens)

From a cbdb card-005 retro: a batch of manual-review findings that were all quality/altitude,
not bugs (dead code, duplication, expensive work above a guard, over-built internals, a missing
why-note). Root cause = the quality passes the skill already had weren't reliably run, plus one
genuinely-uncovered check. Fixes, minimal-diff (fold/gate over adding new blocks, per the
anti-sediment pruning rule):

- **Simplify sweep is now a `Done when` gate item** (`implement.md`) — it existed as a phase step
  and a harness task but wasn't in the done gate, so it could be silently skipped; a skip must
  now be recorded in `progress.md`.
- **Deletion test extended from module seams to a function's own generality and a mechanism's
  internals** — `implement.md` review lens adds a **caller audit** (a static-fn parameter/mode no
  caller exercises is unused generality → delete, add back at the second caller; YAGNI);
  `design-grill.md`'s module-depth lens now runs the same delete-it-in-your-head test on internal
  machinery (extra field/flag, multi-pass state machine, ranking, cache) — catching over-built
  internals at design is far cheaper than at review.
- **Two why-note cases named** (`implement.md` comment hygiene): a load-bearing field/guard with
  no line saying *why* it exists (a reviewer then burns a round confirming), and code that
  diverges from / repairs a patched-fork upstream (this tree is PG 14.4 + Greenplum) — the latter
  may cite the **upstream commit SHA** as a stable public anchor (like an issue ref).
- **New `quality/simplify` review lens, deep tier only, one bundled sonnet agent** (`review.md`):
  the review-side backstop to the implement sweep, bundling the low-inference cleanup family
  (dead code / duplication / efficiency-hoist / altitude) into a **single** cheap agent — recall
  loss on a missed cleanup is cheap, which is exactly why merging is safe here and not for
  correctness/concurrency/security (those stay separate session-model agents). Not added at
  light/standard (their Standards axis already carries hygiene), keeping the token cost bounded.

Why the shape: prevention (sweep gate, deletion test, why-notes) is near-zero marginal cost and
short-circuits the expensive implement→manual-review→fix round-trip; the one paid addition (the
review lens) is confined to deep tier and a cheap model.

## 2026-07-21 (session-model tiering — execution zone on a cheaper model)

- **Plan-gate digest gains a model tip** (`plan.md` step 7): alongside scope/risk/test-mode
  cards, the execution-authorization ask now reminds the human they can switch
  `/model sonnet` + `/advisor opus` for the execution zone after go — ideally in a fresh
  session via `resume` (prompt caches are per-model, so a fresh session makes the switch
  free) — and switch back at the next decision gate.
- **SKILL.md「Subagent model assignment」extended to session-model tiering**: decision zone
  keeps the strong session model; the execution zone runs on a cheaper one with the advisor
  covering decision points. The tradeoff that 评审 adjudication also runs on the cheap model
  (advisor-assisted) is stated explicitly and placed under M6 calibration like every other
  downgrade — weak adjudication verdicts revoke it.
- Why: a strong model end-to-end costs roughly 3-5x Sonnet while the post-freeze execution
  zone is spec-driven work with low judgment density; existing gates (tests, review report)
  bound the cost of executor mistakes.

## 2026-07-20 (board drawer progress + trace status — card 007)

Source: roadmap Card B. The board drawer becomes a per-card progress/trace surface, backed by
a new trace data pipeline; one CLI defect fixed on the way:

- **Board JSON gains `tasks`** (`workflow-status.py parse_tasks()`): tolerant Task-status-table
  parsing — columns keyed by header names, rows by id grammar (`T`-prefixed or bare numeric,
  date-safe); shapes that aren't one-row-per-task degrade to `[]` rather than rendering
  wrong-semantics rows. `blockers` placeholder values normalize to `""` at the source.
- **`trace_data()` single-source builder** extracted from `render_trace()` (CLI text output
  byte-equivalent; `--trace --json` now works). Per-task/per-R `commit_state` is four-valued
  strict/loose/none/**unchecked** (no repo anchor — excluded from presence judgment); the old
  no-repo `("strict", [])` mislabel is gone.
- **Strict commit-card matching excludes the abbreviated hash** (`card_in_message()`): hex
  digits could contain the card number (a400654 vs 006) — cross-card commits no longer pollute
  strict trace rows.
- **New `/api/trace` endpoint** (viewer.py): per-card on-demand, always 200 + pinned-schema
  JSON with an `error` field, card located without the diff gate-commit git call.
- **Drawer sections** (shell.html): Blockers row (non-empty only), task table + x/y-done
  summary (source-labeled `progress`), per-R five-cell trace summary (design/verify/task/test/
  commit + gap flag) with as-of badge and click-only 重算; per-card client cache survives poll
  rebuilds without refetching. **Matrix view** `kind:"trace"` renders the same JSON with
  data-nav doc links; not in the poll's auto-refresh whitelist (snapshot semantics).
- New tests: `tools/test_workflow_status.py` (16, first coverage of workflow-status internals);
  test_viewer +3; test-shell.mjs +4.

## 2026-07-19 (viewer interaction fixes — band unit, hotkey guards, tree-state authority)

Source: daily-use defect reports (card 006). Three behavior fixes in the status viewer
(`tools/viewer/shell.html`), no data-contract changes:

- **Current-line band picks the semantic unit.** Rect choice goes through `SV.pickLineRect`
  (smallest rect containing the click, not the first — container border boxes precede text-line
  rects in Range client-rect lists), and a click inside a table highlights the clicked `<tr>`.
  Fixes whole-table banding; multi-line list items now band a single line too.
- **Global bare-key hotkeys ignore modifier combos** (`c` comment-basket, `/` focus-search):
  cmd+c no longer loses the selection into the basket, cmd+/ is not hijacked. Rule for future
  hotkeys: bare key only.
- **Tree fold state changes only on user interaction.** `highlightInTree` split into mark
  (re-render paths: refresh/sort/filter/scope/theme — active tag only) and reveal (expand
  ancestors; only on doc-link click and quick-open). Persist merges over the saved set
  (`SV.mergeTreeOpen`) instead of overwriting, so a project-scoped toggle no longer wipes other
  projects' saved folds, and stray async `<details>` toggle persists are idempotent (the
  `treeApplying` flag is gone). Note: current Chromium fires toggle for parser-inserted open
  `<details>` — first visit materializes the default fold state into localStorage, harmlessly.

## 2026-07-17 (gate-experience batch — decision digest, trace view, sketch, gate merging, 验证策略)

Source: same-day user feedback — decision-zone docs exceed gate-time reading bandwidth (gates
approved on grill-trust, 详设/plan waved through, tests uninspected, R-spine invisible), plus the
sequenced-production analysis (requirement quality needs solution-shape feedback). Five landings
(MS1 of the decision-ledger direction note in dev_root); contracts intact except the sizing-scoped
gate-merge opt-in, which SKILL.md Stop-at-gate names as an explicit exception.

- **Gate digest** (`steps/gate-digest.md`, new shared step; wired into the requirement/design/
  detail gates + plan's execution-authorization ask): every decision-zone gate ask leads with
  decision cards — load-bearing decisions citing their doc section, least-confident spots, open
  questions — before the go-with-receipts. The doc becomes the drill-in reference, not the
  reading assignment; a decision existing only in the digest is an omission (M3).
- **Trace view** (`tools/workflow-status.py --trace <project>/<card>`): derives the
  R→design→task→test→commit matrix from the designated mapping fields and flags unimplemented /
  uncovered R-ids and R-less tasks. New commit convention (implement.md Commit cadence): per-task
  product commit subjects carry the card-qualified tag `(<NNN> T<n>)`; bare `T<n>` collides
  across cards and renders as a loose match.
- **Disposable design sketch** (requirement grill tactic): a shape question (feasibility, cost
  magnitude, scope size) gets a throwaway 非约束 sketch feeding R-item gaps and price tags back
  before the confirm gate — the solution-shape sibling of the spike; never presented at the gate,
  never renamed into design.md; sketch-leaning R items carry 推断/假设 until design verifies.
- **Gate merging, sizing-scoped + human opt-in** (SKILL.md Requirement sizing): XS may take
  需求+设计 in one invocation with one combined gate; M may merge the 详设 baseline with the
  execution authorization. Formalizes the observed usage (详设/plan being waved through) without
  weakening decision authority — default stays one gate per phase.
- **验证策略 section** (design template; design-grill fills+grills it, test.md consumes it):
  per R-id/Effect item the shortest E2E proof scenario + the design-provided observation point;
  an item with no cheap E2E path is an explicit decision (unit proxy with a why, or redesign for
  observability). The human approves the verification contract at the freeze; the test phase
  reports promised-scenario results instead of inventing coverage post-hoc.

## 2026-07-17 (model-capability calibration retro — three compensatory mechanisms retuned)

Source: the 2026-07-17 skills-vs-model-capability analysis (dev_root note) — the skill's
governance rules are model-independent, but three mechanisms were calibrated for weaker single-pass
models and needed retuning. Contracts untouched; all edits are step-file level.

- **Sonnet-downgrade calibration check run — downgrades retained.** Evidence across recent review
  reports: sonnet lenses keep producing adjudication-surviving findings (fresh-eyes contributed to
  overlap hits on 2026-07-11; an all-sonnet 4-lens run produced the F1/F3/F5/F6 fixes; kill cases
  were normal-rate, e.g. one pre-existing-issue call). No lens meets the revocation bar. To make
  future checks computable instead of anecdotal, `review.md` now tags **both sides** of the tally
  with source lens + model: killed findings in 误报澄清 (step 5) and confirmed findings' hit paths
  (step 5b).
- **Deep tier starts lean, expands on 5b evidence** (`review.md` step 4): pass 1 = sharp core
  (correctness-vs-invariants · adversarial trio · sonnet sweep) + only plainly-indicated menu
  lenses; the rest join a later pass only on a 5b under-sampled verdict. Why: recent deep passes
  came back overlap-dominant (5-path redundant hits, 2026-07-06) or 0-confirmed (2026-07-15) —
  with a stronger session model, max fan-out upfront buys redundancy, not recall.
- **Standard-tier 5b caveat** (`review.md` step 5b): the three axes are disjoint by design, so
  singleton-heavy is the expected shape at standard tier — judge stop by dry-stop there, not
  overlap (usage log 2026-07-16: 7/7 singletons on a review accepted verbatim).
- **Grill sibling-batch opt-in** (`grill.md`): 2–3 mutually-independent questions (no `depends-on`
  links, none gating another's framing) may go out in one round; per-question recommendation +
  grill-log row unchanged; dependencies stay sequenced. Default remains one-question-at-a-time —
  a throughput-only relaxation now that batched questions no longer cost quality.

## 2026-07-16 (karpathy-guidelines comparison — two Surgical-Changes points adopted)

- **Orphan asymmetry added to P0.5** (`implement.md`): scope discipline now states both
  directions — clean up imports / variables / functions your own change orphans; pre-existing
  dead code stays (note it, don't delete unless asked). Previously only the
  don't-touch-adjacent half was written.
- **Changed-line traceability test added to the Spec axis** (`review.md` step 4): every changed
  line traces to a requirement / design item; an untraceable line is creep or an unrecorded
  decision. Applies at light and standard tiers (light reviews inline against the same axes).
- *Why / source:* comparison against the `andrej-karpathy-skills:karpathy-guidelines` plugin —
  its other principles (surface assumptions, simplicity-first, goal-driven verification) were
  already covered more operationally here (grill/requirement gates, P0/P0.6 + deletion test,
  plan/test verification); these two were the only genuine gaps.

## 2026-07-16 (close-out review fixes — same-day standard-tier review of the retro batch)

- **Round-end order respects grill-log proportionality** (`grill.md`): the ask-with-receipts
  round-end order unconditionally required a grill-log append, contradicting the small-grill
  conversation-is-the-log rule; the append (and the receipts list) now applies only when a log
  is persisted — a small grill's receipts are the phase doc + the checkpoint commit.
- **Tier-bump calibration landed in `review.md` step 4**: the stake-tiered dispatch's recall
  backstop (a target class repeatedly reviewed at light/standard whose misses surface later
  gets its default tier bumped) existed only in the commit message/CHANGELOG — no skill file
  carried it, so a fresh session couldn't apply it. Mirrors the model-downgrade calibration.
- Consistency sweep from the same review: HatchDeck milestone citations renamed to `MS<n>` per
  the ID registry (six bare-M spots + a D/E gap-id rewrite); standing-rules citations count all
  three; progress template task row `T1`; word-count figures corrected; long prose rewrapped
  per the short-lines convention.

## 2026-07-16 (retro batch — comparison against the ~/.agents/skills 2026-07-09 set)

- **New `diagnose` verb + vendored step** (`references/steps/diagnose.md`, forked from
  `diagnosing-bugs`): feedback-loop-first defect localization — a red-capable repro loop before
  any theory (trap rule: reading code to build a theory before the loop exists → stop), 3–5
  ranked falsifiable hypotheses shown to the human, tagged instrumentation (`[DBG-*]`, one-grep
  cleanup), minimise-until-load-bearing, fix routed through Prove-It as an 实现 slice. Context
  branching mirrors `investigate`. *Why:* the workflow had no step for "why is this behavior
  wrong" — bug localization sat ad-hoc between investigate (read-only) and implement. Wired:
  SKILL.md verb + M5 + logging vocabulary, `investigate.md` cross-ref (defect ≠ spike),
  `provenance.md`, `log-usage.py` KNOWN_ACTIONS (all three copies).
- **SKILL.md slimmed ~36%** (5020 → 3238 words; no contract change): stop-at-gate and
  execution-zone autonomy each converged to one authoritative section (previously restated
  5×/4×); `status` viewer/gitweb detail pushed down to README; retro-origin parentheticals
  stripped; phase contracts trimmed to contract level (procedure detail stays in steps).
  First-use gloss rule gains its other half: after the first gloss, use the term bare. *Why:*
  writing-great-skills audit — duplication and sediment inflate always-loaded context.
- **Descriptions pruned** (one trigger per branch, identity statements moved to the body;
  681 → 508 bytes) and the `diagnose` trigger added.
- **test.md: tautological-test anti-pattern** — expected values must come from an independent
  source of truth; an assertion that recomputes the expectation the implementation's way passes
  by construction (from `tdd`).
- **plan.md: expand–contract exception** for wide mechanical refactors whose blast radius can't
  land green as one vertical slice: expand → migrate in blast-radius-sized batches → contract
  (from `to-tickets`).
- **review.md: fail-fast + report cap** — resolve the ref (`git rev-parse`) and confirm a
  non-empty diff before dispatching lens agents; lens reports capped at ~400 words.
  ("Skip tooling-enforced findings" was already covered by the false-positive exemplars — not
  duplicated.)
- **requirement.md: redundancy + prior-rejection checks** before drafting — search for an
  existing implementation by domain concept (not the ask's wording), and scan the roadmap's new
  「Rejected / won't do」ledger so rejected proposals don't return unnoticed (from `triage`).
- **Templates:** roadmap gains the「Rejected / won't do」section (requirement-level rejections;
  design-level ones stay in ADRs); progress gains a no-secrets redact note; split-isolate gains
  the card-vs-fog test (can the question be stated precisely, not answered — from `wayfinder`).
- **Fixed ID-prefix registry** (SKILL.md Conventions): one letter, one meaning — `NNN` card ·
  `R<n>` requirement 条目 (reserved) · `ADR-NNNN` · `T<n>` plan tasks · `G<n>` grill questions ·
  `M1–M6` mechanisms · `P<n>` implement principles; review findings `#<n>` + severity spelled
  out; parts named, never numbered. Collisions fixed: implement.md's forked rule set
  R0/R0.5/R0.6/R1/R2/R5 renamed to P* (numbers kept — R1 "one concern per commit" read as
  requirement R1 in the same phase docs); grill.md's stray `Q4` → `G4`; plan template's
  "Task 1 / Task N" formalized as `T1` / `T<n>` (user rule, 2026-07-16).
  Second sweep over *real* design docs added the design-side schemes: `L<n>` abstraction
  layers, `MS<n>` milestones (a live design used bare M1/M2/M3 for milestones — ambiguous
  against mechanism M2 in the same doc), grill ids continuous across rounds (a past grill
  escalated G→H→I letters per round; H also reads as a High finding), parts named with
  long-form `Part <n> (<名>)` only, Mermaid node ids diagram-local/exempt. Third sweep:
  `D<n>` design decisions/子决策 registered (organic in two projects' designs, incl. the
  ADR-scoped form `ADR-NNNN D<n>`); modules confirmed **named** like parts (`Mod<n>` only
  for a compact table/diagram id). Mapping direction pinned: cross-scheme mappings are
  recorded **downstream→upstream only** in each doc's designated field (design How-it-meets ·
  detail 可追溯 · plan `Implements:` · test Coverage · `ADR-NNNN D<n>`); reverse maps are
  derived, never hand-maintained (hand-kept reverse lists drift on every plan edit).
  Cross-file id citations are **markdown links to the id's home** (`[R1](./requirement.md)`,
  `[ADR-0006 D5](./adr/0006-….md)`) — designated fields and first mention always link, repeat
  prose mentions may stay bare; same-file citations stay bare. Templates' mapping-field
  examples updated to the linked form (user rule, 2026-07-16).
- **Short-lines convention** (both skills' Conventions): wrap prose ~100 chars; a long list
  item splits into sub-bullets rather than one long line — applies to authored docs and the
  skill files themselves (existing long lines rewrap opportunistically on edit). The two worst
  offenders restructured as the exemplar: SKILL.md's Fixed-ID-prefixes and Links mega-bullets
  are now sub-lists (user rule, 2026-07-16).
- **Stake-tiered review & grill dispatch** (review.md step 4, adversarial-critic.md,
  design-grill.md): the heaviest shape is no longer the only default. Review tiers — **light**
  (XS/S, <~150 lines, not invariant-heavy): no subagents, orchestrator reviews inline across
  spec/standards/invariants; **standard** (M): three **axis** agents (axis shape borrowed from
  the external `code-review` skill's two-axis economy — Spec / Standards / our KB-Invariants
  axis, each with a complete pasted brief, no sweep); **deep** (L / invariant-heavy / 「彻底审」):
  the existing full lens fan-out + trio + different-model sweep + saturation. Grill critic —
  M+ decision-level checkpoints keep one-agent-per-lens (the 2026-07-04 satisficing finding
  stands there); XS/S and edit-only rounds default to the single-agent form. Adjudication
  unchanged at every tier (it is the precision backstop that makes cheaper/fewer finders safe);
  M6 calibration bumps a tier that repeatedly misses what deep catches. *Why:* grill/review
  cost scaled with the mechanism, not the stakes — 6–9 agents per review pass and 3 per grill
  checkpoint regardless of diff size (user go, 2026-07-16).
- **workflow-status.py flags off-vocabulary 整体状态** — a board state outside
  `backlog|todo|active|blocked|paused|done|dropped` gets a visible ⚠ in the text view and a
  `state_noncanonical` flag in `--json` (viewer-safe extra key). *Why:* the tool passed states
  through verbatim, so `doing`/`in-progress` sat on live boards unnoticed; only rows too broken
  to parse degraded to `?` (found while diagnosing three real boards, all three repaired)
  (user go, 2026-07-16).
- **Card↔external anchors** (templates): `requirement.md` frontmatter gains optional `issue:`
  (originating tracker issue/ticket — the outward ref code comments may cite; `new` records it
  at scaffold time); `progress.md` frontmatter gains `mr:` and `merged:` beside the existing
  `branch:` (card↔code / review-thread / landed-commit anchors; per-task commits stay in git on
  `branch:` — no hash lists in docs, and a `merged:` SHA is resolved via git, never
  hand-composed). Follow-up (same day): `progress.md` also carries an `issue:` mirror
  (requirement.md stays the owner) and an optional `repo:` — required in a multi-repo
  workspace so `branch:`/`merged:` are unambiguous (user rule, 2026-07-16).
- **Storage footprint section in design.md** (存储足迹, by module; required when the design
  touches any storage): every store added/touched — file / shmem / catalog / DB / 内存态 / GUC —
  with owner module, durability, lifecycle. *Why:* ops + I/O already had a per-module home
  (Interface/contract table) but storage was scattered across Scope/Constraints/ADRs in real
  designs (hatch-deck's 内存态+ring lived in Constraints, its persistence decision in an ADR).
  Design altitude = which/who/durability; concrete schema stays detail.md 数据结构 (division
  noted there). Feeds 影响面's 兼容/ABI 面 (user go, 2026-07-16).
- **Ask with receipts — write first, then ask** (Stop-at-gate; wired into grill round-end,
  investigate close/pause, review report reply): an advance ask or verb-closing reply names the
  artifacts just written (doc paths + dev_root commit) — no receipts, no ask. *Why:* M3 is
  edit-triggered, so an omitted write produces no edit and no check; a past grill ran rounds
  chat-only and lost its grill-log. Receipts turn a silent omission into an ask that can't be
  made (user go, 2026-07-16).
- **Harness task list as display mirror** (implement.md + resume.md): at the execution "go",
  create one harness task per plan `T<n>` (+ Final sweep) and update them at the same beats as
  `progress.md` — display-only; `progress.md` stays the resume truth and a fresh session
  rebuilds the list from it. Long walks (investigate campaign, diagnose phases, large M2
  affected-set) may mirror the same way. Decision-zone grills, M3/Lint checklists, and review
  fan-out deliberately don't use it (human-paced / scripted / minutes-long) (user go, 2026-07-16).
- **Simplify sweep closes 实现** (implement.md; M+, XS/S may skip): after the last slice, one
  behavior-preserving pass over the whole change (reuse / dead code / altitude / final comment
  pass) with the green suite as the net, suite re-run, separate commit; bindable `use:simplify`.
  test-after projects restrict to non-structural cleanups (no runnable net → asymmetric risk),
  noting skipped candidates. Per-slice P0 + deletion test stay — the sweep is the whole-diff
  pass they can't do; refactoring stays out of the red-green loop (tdd's rule). Wired: plan
  template gains a Final checklist block; SKILL.md phase 4 names the sweep (user go, 2026-07-16).
- **The advance word is `go`, uniformly** (Stop-at-gate): every advance ask is phrased around
  `go` and names what it authorizes (「回 go 进入设计」); the human's `go` (or an equally
  explicit equivalent) is the authorization — comments/praise without a go are feedback, not
  a go. Covers phase gates, the execution authorization, and post-verdict grill continuation
  (user rule, 2026-07-16).
- **implement.md: test-mode uncertainty asks** — when the project's test-execution policy isn't
  recorded anywhere (project CLAUDE.md / KB / a prior card's progress.md), ask the human
  TDD vs test-after before slice 1 instead of silently inferring; record the answer as the
  project's standing policy so the next card doesn't re-ask (user rule, 2026-07-16).
- **retro.md: KB usage-frequency scan** (periodic extra): tally `[[wiki/…]]`/`[[raw/…]]`
  citations across dev_root (one grep) to see which knowledge pays off — heavily-cited raw
  with no concept → promotion candidate; zero-citation concepts → dead-weight candidates.
  *Why:* KB reads leave no trace (`wiki/log.md` records mutations only, by design); the
  citations workflow docs already carry are the usage record — the retro just has to count
  them. Chosen over per-read logging (user decision, 2026-07-16).
- **Second pass — fresh-context writing-great-skills audit** (same day; 15 findings, 13 fully +
  2 partially applied): the batch's slimming had *compressed instead of disclosed* in places —
  M2/phase-6/verb entries still carried step-level procedure inline; converged them to
  contract-level pointers (change.md owns the M2 mechanics; Requirement sizing owns the
  close-out gate; Usage logging owns the `--action` mappings; Two zones owns the autonomy
  handoff — Stop-at-gate and Verbs now point). review.md's model-assignment rationale
  deduplicated to SKILL.md「Subagent model assignment」. Two completion-criterion fixes: the
  ~400-word lens cap gains an overflow rule (keep highest-severity + state count omitted —
  silent truncation was an unmeasured recall loss); requirement's Done-when now includes the
  redundancy/prior-rejection checks (they were ungated). Writing-style line collapsed to
  "plain prose, technical terms intact". SKILL.md 3238 → 3126 words.

## 2026-07-11 (card-002 retro batch — grill economy + fail-safe discipline)

- **Mid-grill new mechanism → pin principles, defer axes** (`grill.md` Protocol): when an answer
  injects a new mechanism into the phase doc, the current phase pins only its principles and
  boundaries; axis enumeration belongs to the next phase's grill. *Why:* card 002's requirement
  grill spent 3+ of 8 rounds enumerating LLD-grade axes for a mechanism injected mid-grill.
- **Verdict reports facts, never forecasts** (`grill.md` Convergence): "预期下轮 dry" is not
  dry-check output and anchors the human on optimism (a round-4 "衰减" forecast was refuted by
  round 5's wrong-results findings).
- **Third standing rule「class-to-constraint」** (`adversarial-critic.md`): the second same-shape
  finding pins a structural rule instead of continuing instance-hunting (symmetric closure took
  three rounds to be promoted; the trigger should be round two). References updated in
  `requirement.md`/`design-grill.md`.
- **Tiered dispatch on requirement repeat passes** (`requirement.md`): after a round that only
  edited already-grilled text, targeted re-verify of new clauses + lightweight consistency sweep
  — not another full pass (rounds 5–8 re-swept the whole doc while every finding sat in the
  previous round's new text).
- **Review lens「lifted fail-safe symmetry」** (`review.md`): a diff removing/relaxing a rejection
  path triggers a walk of the symmetric surface and type-wrapper (RelabelType) boundaries — the
  two silent-wrong-results bugs in card 002's close-out were both born from lifting v1 refusals
  without this walk.
- **Future items obey M1** (`review.md`): review-born Future/deferred items carry provenance —
  an unverified premise ("this wastes X") survived two phases before being empirically refuted
  mid-implementation (card 002 R12).
- **Data-type diversity for type-generic paths** (`test.md`): fixtures must include a type with
  non-trivial representation behavior (varchar/RelabelType, collatable) — an all-int suite kept
  a varchar-only wrong-results path green through 14 TDD slices.
- **Environment recon before slice 1** (`implement.md`): record the exact build/test invocation
  + baseline suite status in `progress.md`; run the baseline first; never filter build output to
  errors only (an implicit-declaration warning is a load-time undefined symbol).

## 2026-07-11 (status viewer — UI polish)

- **Visual direction ("terminal"):** the `status` HTML viewer (`tools/viewer/shell.html`) gets a
  coherent identity — mono-chrome (labels/ids/phases/tree/meta), squared corners, an amber accent,
  and a high-contrast dark palette — replacing the default-dashboard look. The card phase row is
  redesigned into a **gate-track** signature: one line of node + label per phase (fill = done /
  in-progress / pending), a marker at the decision→execution boundary, doc deep-links preserved.
- **Fullscreen ergonomics:** the list board is a responsive grid within each project section
  (equal-height cards, phase tracks bottom-aligned) instead of one stretched banner; a single
  document reads at a comfortable **measure** (left-aligned) with a **measure ⇄ full-width** toggle
  (persisted). Two-doc split and kanban are unchanged.
- **Manual theme toggle:** a 3-state control (follow OS / light / dark) whose choice overrides
  `prefers-color-scheme` and persists; mermaid re-themes on toggle. Cards use a compact eyebrow
  (state pill + project·id) → title → aligned Now/Next skeleton; doc frontmatter renders as a
  compact meta line, not a table; unknown/`?` status reads as a dashed outline; badge text adapts
  per theme. Plus an a11y floor (visible focus, reduced-motion) and a top-level "browse code"
  (gitweb) entry. Why: the viewer is used fullscreen for long reading + at-a-glance triage; the old
  layout wasted width, ran prose edge-to-edge, and had no distinct identity.

## 2026-07-08 (subagent model assignment — cost)

- **New SKILL.md rule「Subagent model assignment (cost)」**, generalizing review step 4's
  per-lens model table (from a 2026-07-08 standalone investigation, landed via M6 on human
  approval): checklist/gather/verification-driven subagent work defaults to Agent-tool
  `model: sonnet`; inference-heavy analysis, adjudication, and decisions stay on the session
  model; deterministic checks are scripted rather than delegated; every downgrade sits under
  M6 calibration (revoked when its findings repeatedly die in adjudication or it repeatedly
  misses what the orchestrator catches). Why: Sonnet runs ~3.3× cheaper per token than the
  session model and delegated reads leave the main context entirely; the orchestrator's
  existing re-derive/adjudicate duties already backstop precision, so the downgrade costs
  recall at worst — applied only where recall doesn't lean on inference depth.
- **Dispatch points wired to the rule:** M1 gather dispatches pin `model: sonnet`
  (`evidence.md`; exceptions stay on the session model — swappable-seam full enumeration and
  birth-certificate-negative traces, where recall is the deliverable with no cheap backstop);
  M3 gains a「How to run (cost)」section (`omission-check.md` — deterministic subset
  script-eligible, judgment subset to one sonnet agent, inline stays fine right after an
  edit); the critic's lightweight consistency pass pins its "cheaper model" wording to
  `model: sonnet` (`adversarial-critic.md`); `review.md` step 4 now names itself the origin
  of the generalized rule. `change.md` needed no edit — its "consistency agent" mention is a
  historical note, not a dispatch instruction (corrects the investigation's initial reading).

## 2026-07-07 (fourth batch — review rounds 1+2 fixes)

- **Two new M3 items** (review F8, human opted for both): decision-zone comparison/evaluation
  tables carry a provenance marker per comparative claim; a persisted grill log using
  session-local codenames carries a legend line. Templates caught up with the round-1 rules
  (design Alternative scaffold states the provenance requirement; test template carries the
  post-suite log-sweep line); `detail.md` regained its explicit read-only-on-product-code
  contract.
- **log-usage.py normalization extended to report time** (supersedes the second batch's
  "at write time" description): `canonical_action()` is applied to stored rows *and* to the
  `--action` filter argument (per-row, under each row's skill) in `cmd_report`, so pre-fix
  records aggregate under canonical verbs and filtering by an alias spelling still matches.
  The append-only log is never rewritten. Synced to all three copies.

## 2026-07-07 (third batch — writing-great-skills audit, Tier 1+2)

- **SKILL.md de-duplicated and disclosed** (5630 → 4763 words; no behavior change — every cut
  either collapsed a duplicate to its single source or moved branch-specific reference down the
  ladder): the `detail` verb bullet (near-wholesale duplicate of phase §3) deleted; `investigate`/
  `review` verb bullets compressed to front-door + gate + step pointer (details live in their step
  files); M5's restatement of the investigate front-door replaced with a pointer; Stop-at-gate's
  duplicate "one phase" bullet merged and its execution-zone tail (a preview of the Two-zones
  section that immediately follows) cut to one pointer line; the fork-provenance table moved to
  `references/provenance.md` and 拆分与隔离 field mechanics to `references/split-isolate.md`
  (SKILL.md keeps the essence + A↔B 判定 stub — existing 「拆分与隔离」 references still resolve);
  Step binding compressed; two meta/no-op sentences removed ("balance still being tuned",
  first-use-gloss transcript-evidence tail). Tier 3 (phase-paragraph section enumerations) left
  for future pruning passes. Audit: dev_root xg-skills notes/retro-2026-07-07-wgs-audit.md.

## 2026-07-07 (second batch — from the ~/.agents/skills comparison study)

- **retro.md: pruning pass (anti-sediment), every retro.** No-op test sentence-by-sentence,
  duplication collapse to a single source of truth, sediment check (a rule whose justifying
  friction no longer shows up gets retired). *Why:* retros only ever added rules — the
  `writing-great-skills` failure-mode vocabulary names where that ends (sediment/sprawl);
  deletions now have a standing home, with the same human confirm as additions.

- **Description pruned to branches + leading words** (~160 → ~95 words, `wc -w`). Mechanism details
  (M1/M5 discipline, lens fan-out, report locations, frozen-design list) moved back to the body
  they restated; one trigger form per branch kept (CN+EN). Same treatment applied to
  xg-knowledge-lite's description. *Why:* the description is always-loaded context — per
  `writing-great-skills`, it earns harder pruning than the body.

- **Spike — a throwaway probe when reading can't settle it** (investigate.md new section;
  grill.md interleave bullet routes empirical questions to it; SKILL.md investigate verb notes
  it). Probe lives outside the product tree, never committed; the answer upgrades the claims
  table to VERIFIED and lands via normal routing; the code is deleted. A probe needing product
  changes isn't a spike — escalate. *Why:* grills kept parking empirical open questions as
  待验/落地前验 (cbdb 002 left two); adapted from the `prototype` skill ("throwaway code that
  answers a question").

- **M4 session hygiene** (one sentence in SKILL.md): decision-zone grills stay in one unbroken
  window (no mid-grill compact); execution-zone tasks cold-start from `progress.md` — prefer
  `resume` in a fresh session over pushing a long degraded one. *Why:* M4 mechanically supported
  fresh-session-per-task but never recommended it; borrowed from ask-matt's context-hygiene flow.

## 2026-07-07

- **grill.md: recommendation pre-check — self-proposals get the same rigor as external ones.**
  Before recommending an own idea inline (not only in dispatched panels), three checks must pass,
  else it's presented as an open question: comparative claims VERIFIED (no unread-code claims in
  comparison tables), magnitude × medium cost (multiply by the requirement's design scale and the
  access medium's per-op cost), cost symmetry (list what the proposal *adds* — writers/schema/
  state/RPC shapes — not only what it saves). *Why:* 2026-07-06/07 proposal-T grill — three
  consecutive design recommendations overturned by the human on exactly these grounds (overstated
  "零cache/零save hook" table; per-row catalog lookup at 10^6 over RPC; a read turned into a
  write to save a join); the rigor applied to user proposals wasn't applied to own ones, and the
  07-05 dispatch fix only covered agent panels, not inline recommendations.

- **First-use gloss rule (SKILL.md conventions) + grill codename legend.** Coined terms,
  session-local codenames, and non-standard abbreviations carry a one-line parenthetical
  definition at first use per doc and per chat session; a term used fewer than ~3 times isn't
  coined at all. Persisted grill logs that coin scheme codenames (方案 T/S, N1…) keep a one-line
  legend up top. *Why:* transcript scan found 14 "xxx 是什么意思?" questions in two weeks — all
  coined-term/codename/idiom category (M+, 不变量台账, R1, T/S, tp-bearing…); M3 checks term
  *consistency* but nothing covered first-use *comprehensibility*.

- **design-grill.md: comparison/evaluation tables carry a provenance column from the first
  draft** (VERIFIED/INFERRED per cell-claim) — a comparative claim about existing code is a code
  claim (M1). *Why:* same proposal-T retro; the unverified comparison table was the round-1 defect.

- **test.md: post-suite log sweep.** After a full-suite run, sweep server/process logs for silent
  failures (green ≠ no error lines; masked paths pass assertions while logging the real failure);
  "describe, don't run" lists the sweep command alongside. *Why:* cbdb 002 — suite green while
  the log carried a silent sync failure masked by the manual path; the ad-hoc sweep caught it.

- **design-grill.md: card graduated with pre-design.** When a card is born from another card's
  M2/grill evaluation note that already reached design/LLD depth, the design phase *consumes*
  that note (ADR-ize + trace + link) rather than re-deriving; the grill targets what the note
  left open. *Why:* cbdb 003 graduated from 002's proposal-T evaluation at LLD precision — the
  shape worked but wasn't blessed.

- **retro.md periodic extras: KB compile-backlog triage** — each uncompiled raw gets compiled or
  an explicit `compiled_to: deferred — <why>`; missing frontmatter gets repaired. The
  session-start hook only surfaces the backlog; the retro resolves it. *Why:* 6 uncompiled raws
  (2 without frontmatter) had accumulated across acme-db/postgresql/vagrant-qemu with no owner.

- **log-usage.py: recurring mis-logged actions normalized at write time** (implement→plan,
  implement/test→plan, design-note→design, change/adr→change; synced to all three copies).
  *Why:* off-vocabulary spellings kept fragmenting the report aggregation the retro mines
  (4× "implement" alone) despite the warning.

## 2026-07-05

- **grill.md: convergence verdict must surface in the round-closing user message** (not only in
  the grill log / phase doc). The verdict format line already said "one line in chat" but weakly;
  in practice the ADR-0006 grill filed each round's 继续/建议收敛 into the log while closing the
  user-facing message with only *what was found/fixed*, forcing the human to ask "还要继续吗?".
  Strengthened to MANDATORY: the 继续/建议收敛 recommendation is a *conclusion* the human needs
  to decide next-step, so omitting it is a defect. Covers **both** grill users (`requirement`
  elicitation + `design-grill`) since both run this shared step. *Why:* user 2026-07-05 — "为啥
  grill 完没有直接给出是否需要继续 grill".

- **Anti-residual mechanism for semantics-changing changes** (retro of ADR-0006 propagation:
  three old-semantics restatements survived a full rewrite + a consistency agent — an untraced
  Scope tail sentence, the `FloorMerge` module name, a self-noted-then-dropped clarification).
  Root cause: trace-driven M2 propagation touches traced items only; docs also carry
  *restatements* outside the trace, and *names* assert nothing false so consistency reads miss
  their drift. Three additions: (1) `change.md` step 2b **supersede sweep** (mode 变更/撤销
  必跑): retired-phrasing grep across all phase docs, every hit rewritten / annotated-历史表述 /
  justified, plus a rename check per changed contract and a rewrite checklist collecting
  scattered "改写时澄清" notes; (2) `adr.md`: superseding/semantics-changing ADRs list
  **被取代表述** (the sweep's word list); (3) `omission-check.md`: new M3 item verifying the
  sweep ran. New tool `tools/check-superseded-phrases.py` (deterministic grep, exit-code
  gated, `--exclude` for history dirs).

- **adversarial-critic: grill dispatch made faster without lowering the M1 floor** (retro of the
  2026-07-04/05 ADR-0006 grill — 6 rounds, 2 heavyweight agents ≈15 min / ≈140k tokens each;
  user asked how to accelerate). Four dispatch-level changes; verification discipline untouched
  (blockers still orchestrator-verified, every CONFIRMED still cites `file:func`):
  1. **Parallel one-agent-per-lens is now the default panel form** (the merged three-mandate
     agent demoted to trivial checkpoints). *Why:* mixed mandates satisfice on secondary lenses —
     search-before-build skipped the remediation design and cost two extra rounds; single-lens
     agents in parallel cut wall-clock to ~the slowest lens and decorrelate blind spots.
  2. **Verified-facts pack (new third artifact).** CONFIRMED findings + positive verifications
     accumulate in the grill log and are attached to every subsequent dispatch, scoping mandates
     to the delta + integration seams. *Why:* rounds 1 and 5 each re-proved the same kernel
     chains (suppress-only semantics, aggressive read-point) from zero.
  3. **Invariant ledger is maintained in-session, not deferred to as-built.** A grill-confirmed
     invariant lands as an evidence-cited ledger line immediately; only concept articles may
     wait. *Why:* the deferred ledger was the root cause of (2)'s re-verification.
  4. **Tiered passes in design-grill.** Full three-lens panel only at decision-level
     checkpoints; a rewrite implementing an already-grilled decision gets a lightweight
     text-consistency agent (cheaper model, no kernel re-verification; escalate only findings
     that implicate code truth). *Why:* 7 of 8 post-rewrite findings were text-consistency —
     the heavyweight pass mostly re-proved settled facts.
  design-grill.md's panel bullet now points at this dispatch guidance and extends the lenses to
  newly proposed remediations mid-grill (search-before-build the fix before designing it).

## 2026-07-03

- **review.md: checklist lenses default to the cheaper model.** Conventions / tests-hygiene /
  docs-accuracy / git-history lenses dispatch on `model: sonnet` by default; correctness,
  the adversarial trio and security stay on the session model, and step-5 adjudication is never
  downgraded (the precision backstop that makes cheap finders low-risk — recall on checklist
  lenses doesn't lean on inference depth). M6 revokes a downgrade whose findings repeatedly die
  in adjudication or whose axis stops contributing (5b overlap stats). *Why:* user 2026-07-03 —
  token cost; the same-day sonnet pass had just demonstrated verification-driven work holds up.

- **review.md: standing model-diversity agent in the fan-out.** Every review now dispatches,
  besides the lens agents, one light-sweep agent on a different model (Agent `model: sonnet`)
  with fresh-eyes framing (intentional-changes list + "zero findings is a good outcome" +
  execute-don't-just-read where safe); 5b's unused-axes list gains the model axis. *Why:*
  same-model lenses share failure modes — the 2026-07-03 sonnet pass caught a false-positive
  class (check-code-refs flagging the skill's own directory name) that three same-model lenses
  had all missed, at the cost of one extra agent.

- **Review-driven fixes (reviews/2026-07-03, 4M/15L, all applied).** Tools: `--root` value no
  longer leaks into workflow-status's project list (quoted-tilde emptied output) and `--root=`
  accepted; template placeholders no longer mask the gate-derived next step; check-code-refs
  same-line allowlist swallow + `++`-line header misparse fixed; commit-data-repos argparse
  errors exit 0; parse_key strips inline comments. Wiring: investigate.md adopts the blessed
  investigations naming (`<topic>.md`, campaign dir for large ones); design-grill's old
  convergence bullet now defers to grill.md's canonical auto-verdict, and every "protocol +
  grill-log + rollback" enumeration gained the fourth shared piece; **grill checkpoint commits**
  (one per round verdict) give the dry check its diff baseline; review-vs-investigate anchoring
  difference documented as deliberate in both steps; `pre-gate done` grandfather note recognized
  by the M3 close-out item; change.md Guardrail admits the better-approach reason, seam flow
  gains its proportional re-grill, entry gate covers the design-driven entry.

- **New `status` verb + `tools/workflow-status.py`: the card view.** Workflow visibility was
  split across the kanban (coarse: Phase + 整体状态) and each card's `progress.md` (the detail,
  one file at a time). The new read-only tool aggregates, per card: the pipeline position
  (每阶段 doc 的 frontmatter status), board 整体状态/Deps, progress's Now/Next/Blockers, and a
  **gate-derived next step** when progress has no Next bullet (which gate the card waits at).
  Computed from the docs on demand — no cached view to drift — and doubles as a light data check
  (its first run surfaced three real gaps: two cards' progress frontmatter missing `status:`,
  and webapp 003's frontmatter still saying in-progress after done). `status` added to the
  logging vocabulary (log-usage.py copies re-synced). *Why:* user 2026-07-02 — "workflow 可见性:
  card 视图、每卡具体状态、步骤展示、下一步是什么".

## 2026-07-02

- **Layout naming: underscore prefixes dropped.** `_index.md` → `index.md`, `_roadmap.md` →
  `roadmap.md`, `_investigations/` → `investigations/` across the layout tree, steps, and
  templates. The `_` was an inconsistently-applied "project-level meta" marker (`reviews/` never
  had it); the human chose full removal over extending it. dev_root data renamed in lockstep
  (git mv + in-doc reference fixes; `log.md` and `legacy/` untouched as append-only/archive), and
  all remaining old-format per-project index files were upgraded to the card-kanban format in the
  same pass. Historical CHANGELOG entries keep the old names — curated history stays as written.

- **Terminology: form rule + visible pins + human-initiated 术语纠正.** The sharpen-language
  tactic only fired on vague/overloaded terms and pinned them silently, and M3 only checked
  *consistency* — so a force-translated term used consistently everywhere (堆 for `heap`) passed
  both. Now: (1) canonical **form** follows the global Language rule (established EN technical
  terms stay EN) — a force-translated term is a pin trigger / M3 drift even when consistent;
  (2) pins are **stated as they happen** (`术语: heap (_Avoid_ 堆)`) so the human sees when a term
  got decided and can veto; (3) a human flagging a term while reading any doc is a defined
  **术语纠正** flow — pin in CONTEXT-MAP **first** (the anchor M3 reads, so one correction
  propagates), then the owning KB concept, then rewrite the current card's docs (other cards heal
  at their next M3), `log.md` entry inside a card. *Why:* user question 2026-07-02 — term
  decisions were invisible and the wrong-form class had no trigger.

- **`tools/check-code-refs.py`: the no-doc-refs-in-code ban is now a script, not an improvised
  grep.** The ban (no workflow/KB doc references, `.md` mentions, wikilinks, **bare `ADR-NNNN`
  references** (added same day), or line numbers in code comments — repo-public README/CHANGELOG
  etc. allowlisted, also same day) existed in implement.md but its check was "grep the changed
  files" — improvised
  each time, so it kept getting skipped and the refs leaked anyway. New stdlib script scans the
  working diff's added lines (or given files) for the banned patterns, quiet when clean, exit 1 on
  hits; issue/ticket refs stay unflagged. implement.md's hygiene pass now invokes it verbatim, and
  the review conventions lens runs it on the target range (a hit is a finding unless the file's
  domain is the docs — advisory, judged, not auto-stripped). *Why:* same lesson as the comment
  pass — a rule without a deterministic check point doesn't hold.

- **implement.md: mandatory per-slice comment pass; review conventions lens flags over-commenting.**
  The 代码即文档 bullet already said "few but necessary" but was descriptive prose with no check
  point, and projects built through the workflow kept accumulating narrative comments. Now the
  allowed set is explicit (file/function docstrings · step markers · why-notes for constraints the
  code can't show; density = the surrounding file's), a **comment pass** joins the per-slice
  hygiene sweep (re-read added comments, delete narration), and the review verb's conventions lens
  treats over-commenting as a finding. Same rule landed in global CLAUDE.md「Code Comments」so it
  also governs ad-hoc edits outside the workflow. *Why:* user feedback 2026-07-02 — guidance
  without a gate didn't change behavior; the delta is the checkable pass.

- **M2/change.md: R-id-scoped, mode-classified propagation (rewrite of Route A) + detail-only
  route.** Route A was wholesale ("re-evaluate design.md", "regenerate plan.md") even though the
  same enhancement batch had built the R-id traceability spine — and it skipped `detail.md` and
  `test.md` entirely while the seam trigger already did precise scoped rollback. Now: entry is
  **gated** (human decides, incl. escalated design-forks); each affected 条目 declares a **mode**
  — **追加** (new R-id: append downstream, nothing invalidated, approval scoped to the addition) ·
  **变更** (supersede: superseding ADR + traced `[x]→[ ]` resets + test-row resets + proportional
  re-grill of just the changed contracts) · **撤销** (retire, keep the ID, retire downstream) —
  and propagation walks the full spine (design → detail → plan → **test**) touching only traced
  items; **cross-card Deps** are checked for ripples; a new **case C** codifies the detail-only
  baseline change; seam-contract-disproved is labeled as case-A mode-变更. *Why:* 2026-07-02
  discussion — the mode split (直接改变 vs 追加) is the human's insight; scoped propagation
  brings Route A to the precision the seam flow already had. Same-day follow-up: Route A gained
  an explicit **design-driven entry** (方案变更 with the requirement unchanged — `requirement.md`
  untouched, record = superseding ADR + `log.md`, affected set = the changed modules/contracts'
  traces, the rewritten「How it meets」re-verifies the same R-ids); previously the steps forced a
  no-op requirement edit and mis-anchored the propagation on R-ids.

- **retro.md: outputs section + usage-log input/re-scoring.** Three gaps closed: (1) Inputs now
  include mining the usage log (SKILL.md M6 said it, the step file didn't); (2) step 5 adds the
  corrective re-scoring of optimistic provisional records (was only in the global logging rule);
  (3) a new "Where the outputs land" section states what M6 produces and where — fixes/CHANGELOG/
  commits in the skill repo, deferred fixes in `<project>/_roadmap.md`, card-scoped retro analyses
  in the card's `notes/retro-<scope>.md` (blessing the existing webapp practice), cross-card
  retros need no doc of their own. *Why:* user asked "M6 产生什么文档、在哪" 2026-07-02 and the
  answers existed only as convention.

- **Human-first docs must show the reasoning, not only cited facts.** The "logical/causal
  analysis, not a grep-hit list" discipline lived only on the `investigate` verb (M5) — it
  governed the investigation, not what lands in the docs, so a design's Understanding /
  How-it-meets could legally degenerate into an evidence-cited fact table with conclusions
  bolted on (uncheckable inference). New doc convention: in requirement/design/detail/ADR/review
  **and investigation-notes** prose (extended same day — standalone `investigations/` files and KB
  raw, where the rule originated) every load-bearing chain reads **evidence → mechanism →
  conclusion** so the approver can check the inference; design template's Understanding section
  says it explicitly. Execution-zone
  docs stay terse (link, don't restate). *Why:* user 2026-07-02 — 人读文档要有逻辑分析,
  不只是代码事实.

- **Layout: three project-level locations blessed + M3 no-strays check.** `investigations/`
  gains the `<topic>/` **campaign dir** form (charter + phase notes + progress — the shape large
  investigations already took) and new single files drop the redundant `investigation-` prefix;
  `<project>/notes/` (project-level scratch: proposals, triage, project retros — event artifacts
  dated) and `<project>/legacy/` (pre-workflow archive, read-only) are now spec'd. M3 gains a
  「项目根无散件」item. dev_root strays migrated accordingly (skill-notes + the detail-step
  proposal → xg-skills/notes/, 042-data-loss → acme-db/investigations/, webapp mvp0
  strays → notes//legacy/, vagrant-qemu triage → notes/, the mis-slotted xg-skills audit →
  xg-skills/reviews/) and existing card review/retro files renamed to the dated convention.

- **notes/ naming principle: event artifacts dated, living docs not.** Review reports and retro
  analyses are immutable event artifacts → `review-YYYY-MM-DD-<target>.md` /
  `retro-YYYY-MM-DD-<scope>.md`; the grill-log (one append-only file per phase, re-grills append)
  and topic scratch (edited in place, history in git) stay date-free. Stated once in the SKILL.md
  layout comment.

- **review.md: card-level report filenames carry the date.** `notes/review-<target>.md` →
  `notes/review-YYYY-MM-DD-<target>.md` — multi-round reviews of one target (saturation verdict,
  close-out + fix-verification) collided or dated themselves ad-hoc (acme-db appended dates,
  cbdb didn't); now mirrors the standalone `reviews/YYYY-MM-DD-<slug>.md` convention while
  keeping the `review-` prefix the M3 gate globs. Existing files stay (glob still matches);
  unifying them can ride the deferred layout migration.

- **review.md: anchoring question in step 1.** The report's two homes are by design (active
  card → `notes/review-*.md`, standalone → `<project>/reviews/`), but "active" was purely
  session-dependent, so one card's review history could scatter across both (cbdb appserver
  reviews: three in `reviews/`, one in `002/notes/`). Now, when no card is active but the target
  is plainly one card's work, review **asks** whether to anchor instead of silently defaulting to
  standalone. *Why:* user spotted the scatter 2026-07-02; explicit-linkage stays the rule — the
  fix adds a question at the boundary, not topical auto-anchoring.

- **review.md: saturation verdict + adaptive diversity (step 5b).** The review sibling of the
  grill convergence auto-verdict: "a re-review found something" is sampling variance (a review is
  a bounded search over a generative defect space), so whether another pass is worth it is read
  from **adjudication overlap statistics**, not from the existence of new findings — during step 5
  record how many independent paths (lens agents + orchestrator deep-read) hit each confirmed
  finding; **overlap-dominant → near-saturated, recommend stop; singleton-heavy → under-sampled,
  recommend one more pass along axes not yet used** (slicing / reading direction: diff-first ·
  problem-first · spec-first · history-first / polarity: verify-claims vs hunt-bugs — re-running
  the same lens is voting, not diversity); a pass with nothing above the action bar is **dry →
  stop** regardless (a new High on a later pass = genuine miss → retro). One-line verdict goes in
  the report 总体结论 + chat; human still decides. *Why:* same 2026-07-02 discussion as the grill
  rule — the 2026-07-02 xg-skills review itself showed the pattern (the High hit by 3/3 lenses =
  saturated top; several single-lens Mediums = unsaturated middle).

- **grill.md: explicit convergence rule + per-round auto-verdict.** "New questions exist" was an
  unreachable stop criterion (the question space is generative — a fresh pass can always ask
  more), so grills had no principled end. Convergence is now judged by **materiality** — would
  another round still change the decision this phase gates? — via three checks Claude runs at the
  end of every round, emitting a one-line `Grill 收敛判定: 继续/建议收敛` recommendation (the human
  still gates): (1) slot three-state (evidence-backed · human-confirmed · explicitly Open — finite,
  bounds the elicitation grill), (2) decision-level dry check for repeat/adversarial passes (zero
  条目/方案/contract/ADR-level doc changes this round = dry → stop; XS/S one pass, M+ until dry;
  verified against the git diff, not memory), (3) ADR-weighted open points (hard-to-reverse ×
  surprising × real trade-off earns a targeted round; the rest get the recommended default + an
  Open row). A later pass re-opens settled ground only with a decision-changing finding (else →
  Open questions / `_roadmap.md`); M6 calibrates the bar from post-freeze M2 rates vs dry-round
  rates. *Why:* discussion 2026-07-02 — "第二次 grill 总能问出新问题" is perspective diversity,
  not incompleteness; depth must be stop-rule-driven, not count-driven.

- **`commit-data-repos.py`: a data dir only counts as a repo if it is its own work-tree toplevel.**
  Previously `rev-parse --is-inside-work-tree` also matched a not-yet-initialized `~/knowledge` /
  `~/dev-workflow` sitting inside an ancestor's work tree — `git add -A` would then have staged and
  committed the whole ancestor repo. Now such a dir gets its own nested `git init` (the intended
  lazy-init), and a top-level guard makes "Exit 0 always" hold even on unexpected errors (matching
  `kb-backlog.py`). *Why:* found by the 2026-07-02 review (reviews/2026-07-02, M2/L9).
- **Alignment fixes from the same review.** Commit-cadence summaries now say "after each
  **completed** task (runnable checks green)" — the old "verified task" wording read as zero
  autonomous commits in test-after mode, where acceptance stays `[ ]` pending-run. `progress.md`
  is created on **first need** (a mid-grill checkpoint or in-requirement `investigate` may create
  it before 实现) — "lazy" means don't pre-create, not implement-phase-only. The board `done`
  constraint now includes the close-out clause (review doc or `XS/S — review skipped` note)
  everywhere it's stated. Plus template/README alignment: 跨 part 联调 nested under Integration
  with a when-split grouping note, Reader tags on adr/index/roadmap, seam-vs-boundary scoped,
  READMEs cover 拆分与隔离 + `_roadmap.md` + hook-wiring examples, skill description mentions the
  评审 gate.

## 2026-06-30

- **M3 omission-check tightened: "knowledge captured" → "captured & compiled".** A reusable insight
  must reach the KB **through xg-knowledge-lite's Write flow (compliant frontmatter — not a bare
  hand-written file)** and be **compiled to a concept or explicitly deferred**, not left as an
  uncompiled raw. *Why:* this session routed an investigation through `investigate` but recorded it
  with a direct `Write` — producing a raw with no frontmatter that the compile-tracking couldn't see,
  and never compiled. Sibling fix in xg-knowledge-lite: `kb-backlog.py` surfaces uncompiled raw at
  every SessionStart (push, not the old pull-only Lint/Orient), and Compile now must back-annotate
  `compiled_to:` + update `wiki/index.md`.

## 2026-06-28

- **Docs (dev_root) + KB are now git-managed, with a commit cadence.** Each is its **own repo**
  (separate from the product-code repo and from each other), **lazily `git init`'d** on the first
  commit (announced once). dev_root commits at each **gate / doc boundary** (one per verb:
  new/requirement/design/detail/plan/per-task progress/test/review/change/investigate-notes, after
  M3); the KB commits after each **Write/Compile/Lint** (mirroring `wiki/log.md`). **Autonomous local
  commit, push human-gated, history append-only** — the same discipline as the product-code Commit
  cadence (an implement task → two commits: code to its repo, `progress.md` to dev_root). New
  helper `tools/commit-data-repos.py` (init-if-needed + commit-if-dirty + never-push, reads the
  shared config) backs an **optional session-end hook** that sweeps any uncommitted docs/KB. *Why:*
  "文档和 KB 也要被 git 管理,有提交时机,自动提交" — extends the commit discipline to the two data repos.
- **Project-global, card-transcending docs — placed by nature.** Added a project **roadmap**
  (dev_root `<project>/_roadmap.md`, new template): next-up / themes / someday / graduated — a
  savable plan lighter than the kanban so deferred work (cards' Future / Discovered-issues) isn't
  forgotten; items graduate to cards via `new`. **System knowledge stays in the KB**: the design
  step now links each card to the KB **architecture** overview (`[[wiki/<project>/architecture]]`)
  and refreshes it (as-built) on freeze, and adds durable invariants to the subsystem **invariant
  ledger** — both made first-class in xg-knowledge-lite (Orient surfaces them, Lint checks them).
  M3 now checks the roadmap is fed + the architecture/invariants didn't drift; retro scans the
  roadmap. *Why:* "每个 project 要有超脱各 card 的全局文档(架构 / 路线图 / 不变量台账)" — split by
  the repo invariant (planning → dev_root, system knowledge → KB); the invariant ledger already
  existed per-subsystem in the adversarial-critic, just not discoverable.

## 2026-06-27

- **需求条目 (Requirement items) as the traceability spine.** `requirement.md` now carries a
  canonical itemized list — atomic requirements with stable `R-id`s — that Scope/Effect and every
  downstream doc (`design.md`, `detail.md`, `plan.md`, `test.md`) reference by ID instead of
  restating. *Why:* a flat prose requirement couldn't be traced or changed item-by-item; IDs
  localise change and close coverage holes (an `R-id` with no test/task is now a flagged gap).
- **影响面 (Impact surface) section in `design.md`.** Design now states the blast radius —
  changed/added modules, callers & downstream consumers, compat/ABI surface, cross-card/cross-project
  ripples, behaviors to re-verify. *Why:* scope/risk and review focus were implicit; the Risk table
  alone didn't capture who-breaks-if-this-changes.
- **评审 (review) wired as the M+ close-out gate.** After 测试, an M-or-larger requirement runs the
  `review` verb to produce `notes/review-*.md` before the card can go `done`; XS/S may skip. *Why:*
  code earned a test doc but a formal review was ad-hoc; non-trivial changes now end with both.
- **Implementation phase autonomy made explicit.** The implement phase rolls through plan slices
  without per-task gates; Claude owns implementation-level decisions (makes + logs them), escalating
  only on a design/requirement fork (→ M2), a blocker, or a commit request. *Why:* Stop-at-gate was
  being misread as a per-slice halt.
- **Plan-task drops are logged.** Deleting / merging / deferring a task — or invalidating an `[x]`
  — now gets a `log.md` `[实现]` entry (what + why); routine refinement stays silent. *Why:* a
  freely-mutable plan left dropped tasks untraceable — resume/review couldn't tell "done" from "forgotten".
- **Provenance markers generalized.** Load-bearing claims in any phase doc carry an evidence-cited /
  推断 / 假设 marker (not only `investigate` conclusions). *Why:* unmarked assertions read as
  evidence-backed even when they're assumptions.
- **Mermaid preferred for diagrams; link policy clarified.** Diagrams default to Mermaid (ASCII
  fallback); intra-tree references use standard markdown links while KB cross-refs keep the
  load-bearing `[[wiki/…]]` wikilink. *Why:* `[[ ]]` and ASCII don't render/click in common viewers,
  but the wikilink drives KB recompile so it stays.
- **Issue/ticket references allowed in code comments.** The comment-hygiene rule still strips
  uncommitted-doc references and line numbers, but explicitly permits a stable issue/tracker ID/URL.
- **Two-zone model (decision vs execution) made a first-class concept.** The 设计/详设 freeze is
  framed as a single line that is *both* the binding-decision boundary *and* the reader/audience
  boundary: requirement/design/detail are **human-first** (reviewable, gated); plan/progress/test
  are **Claude-first** (autonomous execution + resume) — with `log.md` (audit) and the close-out
  review report as the two deliberate human-facing artifacts in the execution zone. Every template
  now carries a one-line **Reader** tag, and the implement-phase autonomy is tied to this boundary
  (plan = the one-time autonomy handoff; next human touch = the close-out review). *Why:* unifies
  the earlier "split docs by reader" and "implementation needn't wait for the user" points — they
  are the same boundary seen from two angles.
- **Stop-at-gate carve-out for the execution zone.** The hard stops are now scoped to the
  decision-zone gates (需求 confirm · 设计 freeze · 详设 baseline) **plus** the one-time execution
  authorization after `plan.md`. Within the execution zone there is **no per-phase stop** — on one
  "go", implement → test → the M+ close-out review report run autonomously, stopping only to
  escalate (design-fork/blocker/commit) and finally at the review report's fix decision. *Why:*
  "实现阶段不用等待用户决策" means the per-phase checkpoints between implement/test/review aren't
  human *decisions*, so they shouldn't gate; the binding decisions all live before plan.
- **CHANGELOG introduced** (this file) — the M6 retro step now records behavior changes here.
- **Refined after self-review (same day):** (F1) **requirement sizing** (XS/S vs M+) is now defined
  once in SKILL.md「Requirement sizing」, and the close-out gate is verifiable as "a review doc
  **or** an explicit `XS/S — review skipped` note (in `progress.md`)" — so M3 needs no size field,
  it just checks one-of-two is present. *Why:* the gate hinged on a requirement-size axis that was
  never defined and that M3 had no signal to evaluate. (F3) clarified **需求条目 vs Effect** as
  need ↔ acceptance-test (a 条目 = what's required; an Effect = the checkable condition proving it).
- **Investigation = logical analysis, not grep.** `investigate.md` gains an
  「Analysis, not just grep」rule (+ M5 pointer): grep/read only *gather*; the deliverable is a
  traced control/data path + a causal mechanism + the Synthesis lens — a grep-hit list is not a
  conclusion. *Why:* investigations were at risk of degrading to "found N matches, here's a list".
- **Commit cadence.** Implement now commits **autonomously and locally after each verified task**
  (and after each review fix), one concern per commit; **`push` stays human-gated** and history is
  append-only (no amend/squash). Respects an explicit project no-commit policy. *Why:* "每个 task /
  每次 review 修复后提交" — local commits are reversible (so they fit the autonomous execution zone),
  while the irreversible outward act (push) stays gated, reconciling with the global commit rule.
- **Design weighs the hack / 补丁 / 推翻重来 spectrum + each cost.** `design.md`「Alternatives」and
  design-grill「方案优先」now require spanning the solution-class spectrum (quick hack · localized
  patch · proper redo) and naming each one's cost (工期/技术债/影响面/可维护性); a hack/patch is a
  conscious, recorded debt decision, and the "correct" full redo still must pass 简单可靠/反过度设计.
  *Why:* 方案优先 surfaced variants but not this debt-vs-correctness axis explicitly.

- **实现 carries two test modes (TDD vs test-after), picked per project.** Comparing the vendored
  sources surfaced a lossy fork: our `implement.md` cycle had dropped incremental-implementation's
  **Test** step (it read "Implement → Verify"), and the rich `test-driven-development` red-green +
  Prove-It content only half-existed in `test.md` — so the flow looked test-after while claiming
  TDD. Fix: `实现` now carries **both** cycles explicitly — **Cycle A (TDD: RED→GREEN→REFACTOR +
  Prove-It)** where tests run, **Cycle B (test-after: Implement→Test→Verify, defer the run)** for
  cbdb's "describe, don't run". Mode is chosen by the project's test-execution policy and recorded
  in `progress.md` (State at a glance). Both are vertical/per-slice — never all-code-then-all-tests.
  `测试` is reframed as the **consolidation** phase (close coverage by R-id + module interface, add
  integration / 跨 part 联调 / manual / E2E, balance the pyramid, run-or-describe, record results);
  the per-slice red-green loop now lives in `实现`, not here. Commit cadence reconciled with
  test-after (commit when runnable checks pass even if acceptance is `[ ]` pending the human's run).
  Provenance table updated (implement ← incremental-implementation + test-driven-development).
  *Why:* "实现按项目分:能跑测试走 TDD,cbdb 走 test-after" — and a faithful prep of both needed the
  vendor sources, which also revealed the dropped-Test-step bug.

- **Provenance corrected + refactor depth.** A comparison against the real standalone `tdd` skill
  showed our TDD-mode loop ≈ its loop (the difference is structural — planning is frozen upstream in
  需求/设计/详设, so our Cycle A is the loop without the `tdd` skill's Planning step). It also surfaced
  a mis-attribution from the prior entry: the red-green loop's primary source is **`tdd`** (the
  standalone skill), not `test-driven-development` — the latter contributed only **Prove-It / pyramid
  / sizes**. Fixed the provenance table + step headers (implement ← incremental-implementation + `tdd`
  + test-driven-development; test ← `tdd` + test-driven-development). Cycle A's REFACTOR step now
  names deepen-modules / SOLID and points at `codebase-design`; added a note that `use:tdd` overrides
  with its **loop only** (skip its Planning — the design phases own it).

- **Reference the `codebase-design` skill (deep modules) at four points.** design-grill: optional
  **Design-It-Twice** (parallel agents try radically different interfaces — the *interface-shape*
  axis, complementing the hack/补丁/重做 *solution-class* axis) + a **module-depth / deletion-test /
  two-adapter-seam** quality lens. test: pick the test strategy by **dependency category**
  (in-process / local-substitutable / remote-owned port+adapter / true-external mock). implement
  review lens: the **deletion test** (sharper than "remove no-ops"). `design.md`「Interface/contract」
  sources its seam/depth vocabulary (interface = all a caller must know; deep module; seam = Feathers)
  from it. **Referenced (link, don't restate), not vendored** — so it's listed under References, not
  the fork-provenance table. *Why:* `codebase-design` is complementary (module/interface-depth layer)
  and supplies concrete mechanisms our 方案优先 / testability guidance only gestured at.

- **Grilling factored into a shared `grill.md` with history + rollback.** The one-question
  elicitation protocol (duplicated in `requirement` + `design-grill`) is now a shared mechanism
  (`references/steps/grill.md`), adding a **grill-log** (append-only Q / recommended / chosen / why /
  depends-on / status — inline for small grills, `notes/grill-<phase>.md` for large or multi-session)
  and **rollback** (回退 to a previous question = mark it + its dependent subtree `superseded`,
  re-walk, reconcile the phase doc — reusing the `log.md` / ADR supersede discipline, not deleting
  history). `resume` can continue a grill mid-phase from the open `G<n>`. **No new verb / state
  machine**; sized to the grill; a drafting-phase rollback re-walks branches, but once `design.md` is
  frozen a change goes through M2, not a rollback. *Why:* grilling is a dependency-ordered
  decision-tree walk — a structured history + clean rollback matches that and survives resume, where
  before only the in-session chat held it. (Generic non-doc grilling can still `use:grill-me`.)

## Earlier

See `git log` (init + the split-and-isolate part-axis / kanban additions) — this curated changelog
starts at the 2026-06-27 enhancement batch.
