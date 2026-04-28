# UAV-DT 项目详细介绍与论文写作支撑文档（2026-04-22）

## 1. 文档用途

这份文档基于 **2026-04-22 当前代码口径** 重新整理项目内容，目标是为后续论文写作提供统一、可直接引用的中文基础材料。  
它覆盖以下内容：

1. 项目研究问题与方法框架
2. 本轮实际完成的实验内容
3. 主实验结果与补充实验结果
4. 当前项目是否具备论文发表条件
5. 相比常见同类工作的优势、创新点与不足

本次结果以以下目录为准：

1. [20-seed 主实验](../results/scheme_c_readiness_20seed_2026-04-22/main_table.csv)
2. [Holdout 证书验证](../results/scheme_c_holdout_2026-04-22/holdout_summary.csv)
3. [配对比较](../results/scheme_c_readiness_20seed_2026-04-22/paired_comparisons_rollout_joint.csv)
4. [Toy DP benchmark](../results/scheme_c_small_mdp_toy_2026-04-22/summary.csv)
5. [Toy benchmark baseline 对比](../results/scheme_c_small_mdp_toy_baselines_2026-04-22/summary_agg_methods.csv)

---

## 2. 项目研究内容

### 2.1 研究问题

本项目研究的是一个 **数字孪生驱动的 UAV 安全通信协同优化问题**。系统在离散时隙下同时面临三类约束：

1. **数字孪生会老化**
   如果不更新孪生，Eve 位置估计会偏离真实状态，AoI 与不确定度会不断增大。
2. **同步资源有限**
   同步并非免费动作，存在预算、带宽、时延与失败概率。
3. **安全通信与轨迹/功率控制耦合**
   UAV 的移动与发射功率会同时影响合法链路质量、窃听链路质量以及同步收益。

因此，项目优化目标并不是单一 secrecy rate，而是一个三元耦合目标：

1. 平均保密速率 `avg_secrecy_rate`
2. 中断概率 `outage_prob`
3. 同步成本与运行时 `avg_sync_cost` / `runtime_per_slot_ms`

### 2.2 场景组成

当前主实验场景为一个小规模 UAV 安全通信环境：

1. 1 个 BS / 边缘节点
2. 2 架合法 UAV
   `UAV-1` 负责服务传输，`UAV-2` 负责干扰
3. 1 个 Eve
4. 多个地面用户
5. 2D 平面离散时隙演化

### 2.3 当前版本的重要变化

相较于旧版本，本轮代码并不是小修，而是一次明显的实验口径升级，主要变化包括：

1. Eve 从简单移动改为 `adaptive_mobile`
2. 同步从二值触发扩展为 **连续带宽同步**
3. 数字孪生从简单误差半径演化为 **Kalman twin**
4. 信道从简化路径损耗扩展为 **概率 LoS/NLoS**
5. 动作空间从 5 向移动扩展为含对角动作的更大空间
6. `rollout_joint` 重新设计为带证书、风险与 backlog 惩罚的前瞻式联合控制
7. 证书模型使用 **split conformal upper bound + holdout 验证**

这些变化使得旧结果已不能代表当前版本，因此本次文档完全以新跑结果为准。

---

## 3. 方法体系

### 3.1 环境与状态估计方法

项目底层并不是深度学习黑盒，而是模型驱动的可解释框架，核心模块包括：

1. **Kalman twin**
   用状态向量与协方差联合估计 Eve 位置/速度。
2. **连续带宽同步**
   同步不再只是“同步/不同步”，而是按带宽大小消耗预算并影响测量精度。
3. **自适应 Eve**
   Eve 会根据 UAV 相对位置选择更有利于窃听的机动方向。
4. **概率 LoS/NLoS 信道**
   合法链路与窃听链路都受到更现实的信道衰落影响。
5. **经验型安全证书**
   用特征回归 + conformal buffer 估计 secrecy loss upper bound。

### 3.2 对比方法

20-seed 主实验采用以下 4 个方法：

1. `periodic`
2. `security_risk`
3. `security_margin`
4. `rollout_joint`

其方法含义可概括为：

1. `periodic`
   固定周期同步，是最直接、最强势的经典基线。
2. `security_risk`
   根据 AoI、误差半径、sigma 和安全缺口构造风险指标，再决定同步。
3. `security_margin`
   根据证书是否满足 required margin 决定是否同步。
4. `rollout_joint`
   在同步、轨迹和功率空间里做短视界联合前瞻搜索。

### 3.3 论文中可强调的方法主线

从方法设计看，本项目最适合写成如下技术主线：

1. **数字孪生不确定性建模**
2. **安全感知同步决策**
3. **同步-轨迹-功率联合优化**
4. **基于 holdout 的证书统计校准**

这条主线在方法上是成立的，关键问题主要出在“最终实验结果是否足够支撑主方法优势”。

---

## 4. 本次实际完成的实验内容

本次并非只做文档整理，而是实际重跑了当前版本的重要实验链条。

### 4.1 已完成实验

1. `fit_certificate_holdout`
   重新拟合并验证当前版本的 conformal certificate。
2. `run_readiness_multiseed`
   完成 `paper_base / paper_hard / scenario_stress` 三场景、五方法、20 seeds 的主实验。
3. `paired comparison`
   计算 `rollout_joint` 相对多个 baseline 的逐 seed 配对比较。
4. `toy DP benchmark`
   在更小的 toy 场景上完成离散状态抽象下的 DP 上界求解。
5. `toy benchmark baselines`
   在 toy 场景上补跑 baseline / rollout / oracle 对比。

### 4.2 未完全完成部分

原计划中的 `configs/small_mdp_bound.yaml` 精细版 DP 在当前代码口径下出现了资源问题，运行时被系统以 `SIGKILL` 中止。  
因此，本轮文档里保留的是一个 **透明标注的 toy DP benchmark**，用于提供补充性的上界 sanity-check，而不把它作为主结论来源。

这意味着：

1. **主表和 holdout 结论是完整且正式的**
2. **小场景理论上界只完成了 toy 抽象版本**

---

## 5. 主实验结果

### 5.1 paper_base

| method | avg_secrecy_rate_mean | avg_secrecy_rate_ci95 | outage_prob_mean | outage_prob_ci95 | avg_sync_cost_mean | certificate_cover_rate_mean | runtime_per_slot_ms_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| periodic | 1.6315 | 0.0100 | 0.8879 | 0.0038 | 0.1500 | 1.0000 | 101.94 |
| security_risk | 1.5096 | 0.0257 | 0.8875 | 0.0037 | 0.0375 | 0.9996 | 101.22 |
| rollout_joint | 0.9928 | 0.0062 | 0.8871 | 0.0034 | 0.0000 | 1.0000 | 160.99 |
| security_margin | 0.7991 | 0.0484 | 0.8962 | 0.0036 | 0.2331 | 0.8125 | 100.21 |

结论：

1. `periodic` 在 secrecy 上反而是本场景最优。
2. `rollout_joint` 的 outage 最低，但 secrecy 大幅落后。
3. `security_risk` 在极低同步成本下，保持了接近 `periodic` 的 outage。

### 5.2 paper_hard

| method | avg_secrecy_rate_mean | avg_secrecy_rate_ci95 | outage_prob_mean | outage_prob_ci95 | avg_sync_cost_mean | certificate_cover_rate_mean | runtime_per_slot_ms_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| periodic | 1.2948 | 0.0095 | 0.9482 | 0.0044 | 0.1571 | 1.0000 | 101.78 |
| security_risk | 1.2435 | 0.0363 | 0.9432 | 0.0036 | 0.0362 | 0.9911 | 100.96 |
| rollout_joint | 0.7872 | 0.0052 | 0.9450 | 0.0027 | 0.0000 | 1.0000 | 158.98 |
| security_margin | 0.5668 | 0.0537 | 0.9557 | 0.0044 | 0.1570 | 0.9046 | 101.59 |

结论：

1. `periodic` 在该场景 secrecy 最强。
2. `security_risk` 在 outage 上最好，并且同步成本最低。
3. `rollout_joint` 仍未表现出对强基线的统治优势。

### 5.3 scenario_stress

| method | avg_secrecy_rate_mean | avg_secrecy_rate_ci95 | outage_prob_mean | outage_prob_ci95 | avg_sync_cost_mean | certificate_cover_rate_mean | runtime_per_slot_ms_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| periodic | 0.9887 | 0.0212 | 1.0000 | 0.0000 | 0.1187 | 0.9981 | 99.39 |
| security_risk | 0.9646 | 0.0304 | 1.0000 | 0.0000 | 0.0395 | 0.9925 | 117.62 |
| rollout_joint | 0.7775 | 0.0318 | 1.0000 | 0.0000 | 0.1187 | 0.7003 | 215.66 |
| security_margin | 0.3217 | 0.0063 | 1.0000 | 0.0000 | 0.1185 | 0.9166 | 112.02 |

结论：

1. 本场景所有方法的 `outage_prob_mean` 都为 `1.0000`，说明 stress 设置已非常苛刻。
2. `periodic` 在 stress 下仍是 secrecy 最优。
3. `rollout_joint` 在最难场景下并未形成优势，且运行时明显更高。

### 5.4 主实验整体结论

本轮主实验给出的信息非常明确：

1. **当前版本最稳的强基线是 `periodic` 与 `security_risk`**
2. **`rollout_joint` 没有成为当前口径下的最佳主方法**
3. **`security_margin` 当前不适合作为主方法，只适合作为补充基线**

这与旧版本文档中的乐观判断已经明显不同，论文叙事必须据此调整。

---

## 6. Holdout 证书结果

| split | scenario | cover_rate | mean_upper_minus_loss | p90_upper_minus_loss | avg_realized_loss |
| --- | --- | --- | --- | --- | --- |
| train | all | 0.9968 | 2.0314 | 5.0590 | 0.7817 |
| train | base | 1.0000 | 0.8025 | 1.4749 | 0.2764 |
| train | scenario_hard | 1.0000 | 2.2516 | 6.3660 | 0.9037 |
| train | scenario_stress | 0.9917 | 2.7603 | 9.1075 | 1.0539 |
| validation | all | 0.8710 | 5.0971 | 17.8447 | 1.0437 |
| validation | paper_base | 0.8800 | 4.3920 | 15.9939 | 0.8763 |
| validation | paper_hard | 0.9100 | 6.0241 | 21.9968 | 0.8988 |
| validation | scenario_stress | 0.8300 | 4.8148 | 15.7333 | 1.2960 |

结论：

1. 训练集覆盖率很高，但这并不代表泛化已经足够好。
2. 验证集整体覆盖率只有 `0.8710`，明显低于理想的 `1 - alpha = 0.95` 附近水平。
3. `scenario_stress` 的 holdout 覆盖率只有 `0.8300`，说明证书在最难场景下泛化不足。
4. `mean_upper_minus_loss` 和 `p90_upper_minus_loss` 很大，说明证书仍然偏松、且不稳定。

论文含义：

1. 当前证书线 **可以写**，但不能再写成“已经很稳的统计保证”。
2. 更合理的表述应是：
   `当前证书提供了经验性的保守上界尝试，但其跨场景泛化与覆盖率仍有待进一步加强。`

---

## 7. 配对比较结果

`rollout_joint` 对三类重要 baseline 的逐 seed 配对比较结果如下：

1. 相对 `periodic`
   在三个场景下 secrecy 增益全部为负。
2. 相对 `security_risk`
   在三个场景下 secrecy 增益也全部为负。
3. 相对 `security_margin`
   secrecy 虽然显著更高，但这只能说明 `security_margin` 当前更弱，并不能说明 `rollout_joint` 已经足够强。

换言之，当前 `rollout_joint` 的主要问题不是“略输一点”，而是：

1. 对真正强基线没有优势
2. 运行时更高
3. 在 stress 场景下表现仍然不稳

这会直接影响论文主方法的定位。

---

## 8. Toy DP Benchmark

### 8.1 toy DP 上界结果

| config | seed | episode_length | optimal_cumulative_secrecy | optimal_avg_secrecy | num_states_evaluated | num_actions | state_abstraction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| configs/small_mdp_bound_toy.yaml | 42 | 4 | 10.1747 | 2.5437 | 12502 | 72 | rounded_state_dp(pos=0.1,twin=0.01,cov=0.01) |

### 8.2 toy 场景 baseline 对比

| method | avg_secrecy_rate_mean | avg_sync_cost_mean | certificate_cover_rate_mean | runtime_per_slot_ms_mean |
| --- | --- | --- | --- | --- |
| aoi_only | 2.5437 | 0.2500 | 1.0000 | 18.83 |
| decoupled | 2.5437 | 0.5000 | 0.7500 | 19.76 |
| full | 2.5437 | 0.5000 | 0.7500 | 18.45 |
| oracle_sync | 2.5437 | 0.2500 | 1.0000 | 122.54 |
| periodic | 2.5437 | 0.5000 | 0.7500 | 19.02 |
| random_budgeted | 1.4822 | 0.0000 | 1.0000 | 1.39 |
| rollout_joint | 2.5437 | 0.0000 | 1.0000 | 127.27 |
| security_margin | 2.5437 | 0.0000 | 1.0000 | 19.73 |
| security_risk | 2.5437 | 0.0000 | 1.0000 | 18.41 |

解读：

1. toy 场景过于简单时，多种结构化方法都能达到同一最优水平。
2. 该结果只能说明“在非常小的抽象问题上，项目方法并不违背直觉上界”，不能外推为主场景优势。
3. 这部分更适合作为附录中的 sanity-check，而不是正文主证据。

---

## 9. 当前是否具备论文发表条件

### 9.1 可以得出的务实结论

如果以 **“是否已经具备论文雏形与完整实验框架”** 为标准，答案是：

1. **具备**

如果以 **“是否已经具备一篇稳妥投稿的主结果质量”** 为标准，答案是：

1. **具备技术报告 / 初稿条件**
2. **暂不建议直接按当前主结果投稿正式论文**

### 9.2 原因

当前项目具备发表潜力的部分：

1. 问题定义清晰
2. 方法链条完整
3. 实验脚本齐全
4. 有 20-seed 主表
5. 有 holdout 证书验证
6. 有 toy benchmark 补充验证

但当前不宜直接投稿的关键原因也很明确：

1. `rollout_joint` 没有打赢 `periodic` / `security_risk`
2. `hybrid` 只在一个场景 secrecy 上领先，且覆盖率偏低
3. holdout 覆盖率不够稳，尤其在 stress 场景偏低
4. stress 场景全部 outage=1，说明场景已经把区分能力压扁
5. 论文主方法的“性能优势”与“统计保证”都还不够硬

### 9.3 当前最准确的发表判断

更准确的说法应当是：

1. **当前项目已经具备写一篇完整论文初稿的条件**
2. **但离“可以较稳投稿”的状态还有一段距离**
3. **若直接投稿，审稿人最容易质疑的是：主方法不够强、证书不够稳、stress 结果区分度不足**

---

## 10. 相比常见同类工作的优势

虽然当前结果不够强，但本项目的研究设计本身仍有明显优势。

### 10.1 问题建模更完整

很多 UAV 安全通信 / 数字孪生相关工作通常采用以下简化假设：

1. Eve 轨迹固定或完全已知
2. 同步是无成本或固定成本
3. 同步决策与轨迹控制分开做
4. 证书只停留在解析上界，没有单独验证
5. 信道采用更理想化的固定模型

本项目相对更完整地联合考虑了：

1. 自适应 Eve
2. 连续带宽同步
3. Kalman twin 不确定性
4. 概率 LoS/NLoS 信道
5. 同步-轨迹-功率联合决策
6. 证书 holdout 验证

### 10.2 实验口径更像“系统论文”

本项目不是只给一个主表，而是已有：

1. 主表
2. holdout 证书实验
3. 配对比较
4. toy benchmark
5. 多场景、多 seed 实验

这使它比“只做一个优化模型、只报单次结果”的工作更接近完整系统论文结构。

### 10.3 方法可解释性强

本项目的控制器并不是难以解释的深度强化学习黑盒，而是：

1. 风险可分解
2. 证书项可解释
3. 同步预算可追踪
4. runtime 可测量

这对应用类和系统类论文是明显优势。

---

## 11. 当前最值得强调的创新点

如果后续写论文，当前最有价值的创新点建议概括为以下 4 点。

### 11.1 连续带宽同步而非二值同步

这是一个比较实在的创新点。  
很多工作只研究“是否同步”，而本项目进一步研究“同步多少带宽、消耗多少预算、测量精度如何变化”。

### 11.2 Kalman twin + adaptive Eve 的耦合建模

项目不是简单把数字孪生当成误差噪声，而是显式建模：

1. Eve 运动
2. twin 预测
3. 协方差演化
4. 同步后的测量校正

这一点比纯启发式 AoI 同步更强。

### 11.3 证书驱动的安全同步决策

即使当前证书泛化还不够强，它仍然构成了一个很有研究价值的方向：

1. 把 `secrecy loss upper bound` 引入同步决策
2. 用 holdout 数据验证证书是否真的覆盖真实损失

这比“只凭阈值经验触发同步”更有论文价值。

### 11.4 同步-轨迹-功率联合控制框架

项目的核心思想不是单点小技巧，而是一个统一框架：

1. 同步决策
2. UAV 移动
3. 发射功率
4. 风险与证书惩罚

这类联合建模本身就是可发表的方向。

---

## 12. 当前主要不足

论文写作时不应回避以下不足：

1. 主方法 `rollout_joint` 当前表现不够强
2. holdout 覆盖率明显低于理想目标
3. stress 场景过难，导致所有方法 outage=1
4. full small-MDP exact DP 未在当前资源内完成

这些不足必须在后续实验里解决，否则论文主结果会比较脆弱。

---

## 13. 论文下一步建议

若目标是把项目推进到可投稿水平，建议优先做以下 4 件事：

1. **重调主方法**
   让 `rollout_joint` 或 hybrid 至少在 `paper_base / paper_hard` 两个场景里稳定超过 `periodic` 或 `security_risk`。
2. **重做证书拟合**
   目标是把 validation cover rate 提升到更接近 `0.95`，尤其提高 stress 场景覆盖率。
3. **重设 stress 场景**
   避免所有方法 outage 全为 `1.0`，否则场景失去比较价值。
4. **保留 toy DP，弱化 full DP**
   正文不要强求 full exact MDP，上界参考可作为补充 sanity-check 使用。

---

## 14. 一句话总结

这次大改之后，项目的**方法设计与实验框架更像一篇正式论文**，但**当前新结果并不支持“主方法已经显著优于强基线”的结论**。  
因此，项目现在最适合的定位是：

1. **已经具备完整论文初稿条件**
2. **具备明确创新点和研究价值**
3. **但还需要一轮针对性重调，才能进入更稳妥的投稿状态**
