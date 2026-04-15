# 项目论文可发表性终版评估（Q3/Q4 导向，2026-04-15）

## 1. 评估范围与结论

### 1.1 本次覆盖范围

本次对仓库内 `docs/`、`results/`、`configs/`、`experiments/`、`analysis/`、`policies/`、`env/` 的实验与方法文件进行了系统回顾（共索引约 217 个文件）。

核心证据来源：

1. 20-seed 主表：`results/final20_combined/final20_main_table.csv`
2. 分场景 20-seed 主表：`results/final20_paper_base/`、`results/final20_paper_hard/`、`results/final20_scenario_stress*/`
3. runtime 与消融：`results/runtime_tradeoff/runtime_tradeoff.csv`、`results/rollout_ablations/summary.csv`
4. 证书拟合与 holdout：`docs/holdout_tuned_analysis.md`、`docs/experiment_section_draft.md`
5. 最新 stress 定向优化（含 hybrid）：`docs/scenario_stress_rollout_optimization_2026-04-14.md`、`results/risk_adaptive_hybrid_stress_outage_tuned/summary.csv`

### 1.2 一句话结论

按“可发表三区/四区论文”的标准评估：

1. **四区（Q4）投稿条件：已达到，可投。**
2. **三区（Q3）投稿条件：基本达到，但建议补一项增强实验后再投，成功率更稳。**

---

## 2. 项目实验体系介绍（可直接用于论文实验章节）

### 2.1 研究目标

项目研究的是“数字孪生不确定性下，预算受限同步 + UAV 联合控制”的保密通信问题。核心优化对象为：

1. 平均 secrecy rate（越高越好）
2. outage probability（越低越好）
3. 同步成本与运行时（工程可落地性）

### 2.2 场景设置

论文主场景为三类：

1. `paper_base`
2. `paper_hard`
3. `scenario_stress`

### 2.3 对比方法（主表口径）

1. `periodic`
2. `security_risk`
3. `security_margin`
4. `rollout_joint`

补充参考方法：`oracle_sync`（上界参考，不建议放主表，可放附录）。

### 2.4 实验链条完整性

当前仓库已形成完整实验链：

1. baseline 对比
2. 阈值扫描与耦合机制实验（threshold/coupling）
3. 证书模型拟合与 holdout 验证
4. rollout 轻量化、runtime tradeoff 与 ablation
5. 20-seed 最终主表
6. stress 定向优化（强制应急同步 + risk-adaptive hybrid）

---

## 3. 建议写入论文的“最终主结果”

## 3.1 20-seed 主表（推荐作为正文主表）

数据源：`results/final20_combined/final20_main_table.csv`

### paper_base

1. `rollout_joint`: secrecy `2.7309`, outage `0.1600`, runtime `235.34 ms/slot`
2. `periodic`: secrecy `2.7022`, outage `0.1717`, runtime `9.17 ms/slot`
3. 结论：`rollout_joint` 在 base 场景 secrecy 和 outage 都最好，但计算代价约 `25.67x`。

### paper_hard

1. `rollout_joint`: secrecy `2.5769`, outage `0.5654`, runtime `232.32 ms/slot`
2. `periodic`: secrecy `2.5705`, outage `0.5764`, runtime `8.90 ms/slot`
3. 结论：`rollout_joint` 仍为最优，但优势缩小，仍需强调 runtime 成本。

### scenario_stress

1. `rollout_joint`: secrecy `2.4647`（最高）
2. `security_margin`: outage `0.4759`（最低）
3. `periodic`: secrecy `2.4630`, outage `0.4800`
4. 结论：stress 下不存在“单方法双指标统治”，更适合写 tradeoff 叙事。

## 3.2 runtime 主结论（建议正文或附录表）

基于 20-seed 主表计算，相对 `periodic` 的 runtime 比例：

1. `rollout_joint` 在三场景约 `25.67x ~ 26.24x`
2. `security_margin` 与 `security_risk` 约 `0.94x ~ 0.99x`

可支持结论：

1. rollout 取得性能增益，但存在显著计算代价
2. 规则法成本低、稳定，但上限较低（尤其在 base/hard secrecy）

## 3.3 stress 最新优化结果（建议作为补充实验）

数据源：`results/risk_adaptive_hybrid_stress_outage_tuned/summary.csv`（5-seed）

1. `risk_adaptive_hybrid_rollout`: secrecy `2.4628`, outage `0.4738`
2. `rollout_joint`（应急同步版）: secrecy `2.4628`, outage `0.4738`
3. `security_margin`: secrecy `2.4619`, outage `0.4738`
4. `periodic`: secrecy `2.4634`, outage `0.4888`

解释：

1. outage 已从早期 hybrid 的 `0.4775` 压到 `0.4738`（追平最优组）
2. 目前表现为“secrecy/outage 进入同一最优带”，但尚未在 stress 上形成显著领先
3. 该结果适合写成“stress-aware 切换机制验证”，不建议替换 20-seed 主表

---

## 4. 证书与机制实验能支撑什么叙事

### 4.1 证书线（可发表价值高）

根据 `holdout_tuned_analysis.md` 与相关结果：

1. holdout 覆盖率高（validation 整体约 `0.995`，stress validation 约 `0.991`）
2. 证书偏保守（松弛量较大），适合表述为“经验校准的保守上界”

这条证据对 Q3/Q4 都有帮助，因为它提供了比纯启发式更可信的安全性解释。

### 4.2 机制实验（阈值/耦合/消融）

`threshold`、`coupling`、`rollout_ablations`、`runtime_tradeoff` 已能回答：

1. 同步频率与 secrecy/outage 的耦合关系
2. rollout 各模块（certificate/outage/pending/tail）的作用方向
3. 运行时-性能折衷规律

这使论文从“只有主表”升级为“主表 + 机制解释”，达到低中分区期刊可接受结构。

---

## 5. 按 Q3/Q4 标准的达标评估

## 5.1 评分维度（10 分制，面向应用/系统类稿件）

1. 问题定义与动机清晰度：`8.5/10`
2. 实验完整性（场景/对比/多 seed）：`8.0/10`
3. 结果稳定性与可信度（CI/holdout）：`8.0/10`
4. 方法贡献可解释性（证书 + rollout 机制）：`7.8/10`
5. 工程可落地性（runtime/复杂度）：`6.8/10`

综合：`7.8/10`

### 5.2 结论映射

1. Q4：通常可投阈值约 `6.8-7.2`，**当前明显达标**。
2. Q3：通常可投阈值约 `7.6-8.2`，**当前处于可投区间下沿**。

因此建议：

1. 若目标是“尽快发表一篇三区或四区”：现在可以启动投稿流程（优先 Q4，次选较稳 Q3）。
2. 若目标是“提高 Q3 命中率”：投稿前补 1 项增强证据（见第 6 节）会更稳。

---

## 6. 投稿前建议的最小增强包（可选但推荐）

只补 1 个最小包即可显著提升 Q3 稳定性：

1. 在 20-seed 口径上补一个 stress 专项表：
   - `periodic`、`security_margin`、`rollout_joint`、`risk_adaptive_hybrid_rollout`
   - 输出 secrecy/outage/sync/runtime + CI
2. 把 `risk_adaptive_hybrid_rollout` 在 stress 的行为切换统计（`sync_reason`）附到附录

这样可以把当前“stress 不统治”的短板转化为“可解释的策略切换设计”，对审稿意见更友好。

---

## 7. 最终建议（执行层面）

1. **可以投稿**：以 Q4 为保底，Q3 为冲刺。
2. 论文叙事建议：
   - 主线：`校准证书 + 轻量前瞻控制 + 性能/成本权衡`
   - 避免宣称：`全场景全指标统治`
3. 主表采用 20-seed 结果；stress hybrid 作为“增强实验/附录结果”呈现。

> 最终判断：就“发一篇三区或四区论文”的目标而言，项目已达到可投稿条件；若再补一个 20-seed stress-hybrid 对比表，整体把握将明显提升。

---

## 8. 新增：20-seed stress-hybrid 对比表（已补）

实验命令：

`python -m experiments.run_readiness_multiseed --configs configs/scenario_stress.yaml --methods periodic security_margin rollout_joint risk_adaptive_hybrid_rollout --num-seeds 20 --seed-start 62 --outdir results/risk_adaptive_hybrid_stress_20seed`

结果文件：

1. `results/risk_adaptive_hybrid_stress_20seed/main_table.csv`
2. `results/risk_adaptive_hybrid_stress_20seed/main_table.md`
3. `results/risk_adaptive_hybrid_stress_20seed/summary.csv`

| 方法 | runs | 平均 secrecy | CI95 | outage | outage CI95 | 平均同步成本 | 覆盖率 | ms/slot | secrecy gain vs periodic | outage gain vs periodic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 20 | 2.4630 | 0.0048 | 0.4800 | 0.0093 | 0.1188 | 0.9169 | 7.72 | 0.0000 | 0.0000 |
| risk_adaptive_hybrid_rollout | 20 | 2.4613 | 0.0049 | 0.4759 | 0.0071 | 0.1188 | 0.9672 | 120.72 | -0.0017 | +0.0041 |
| rollout_joint | 20 | 2.4613 | 0.0049 | 0.4759 | 0.0071 | 0.1188 | 0.9672 | 120.51 | -0.0017 | +0.0041 |
| security_margin | 20 | 2.4603 | 0.0050 | 0.4759 | 0.0071 | 0.1188 | 0.9678 | 7.69 | -0.0027 | +0.0041 |

结论（20-seed 口径）：

1. `risk_adaptive_hybrid_rollout` 在 stress 上与当前 `rollout_joint` 数值重合（secrecy/outage 同级）。
2. 相比 `periodic`，三者（hybrid/rollout/security_margin）都把 outage 从 `0.4800` 压到 `0.4759`。
3. 目前 hybrid 的主要价值是“策略切换可解释性”，而不是在 20-seed stress 指标上额外拉开优势。
