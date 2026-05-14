# 最终实验结果详细分析（面向非领域读者）

本文解释 `results/final_2026-05-12/` 中的最终实验结果。写作目标是让不熟悉无人机通信、数字孪生或物理层安全的人，也能看懂这些表格在比较什么、每个指标代表什么、以及哪些结论可以放心写进论文。

## 1. 这个实验到底在研究什么

可以先把系统想象成一个“安全通信任务”：

1. 两架合法无人机要帮助地面用户通信。
2. 一名窃听者 Eve 会移动，并试图偷听通信。
3. 系统并不总是知道 Eve 的真实位置，只维护一个“数字孪生”估计。
4. 如果系统花费同步资源，就能让数字孪生更接近真实世界。
5. 但同步有预算，不能一直同步。

所以核心问题是：

> 在同步资源有限、Eve 会移动、数字孪生会变旧的情况下，系统应该什么时候同步、无人机应该怎么移动和分配功率，才能让合法通信更安全？

这个项目的主方法是 `rollout_joint`。它不是只看当前一步，而是把同步、运动、发射功率、干扰功率和未来几步可能收益放在一起做近似前瞻决策。

## 2. 读结果前必须理解的指标

### 2.1 `avg_secrecy_rate`

这是最重要的性能指标之一，可以理解为“平均安全通信速率”。

如果合法用户收到的通信质量比窃听者好，系统就有正的安全通信能力；如果窃听者太强，安全通信能力就会下降。`avg_secrecy_rate` 越高，说明平均每个时隙里可安全传输的信息越多。

白话理解：

- 高：合法通信比窃听链路更占优势。
- 低：Eve 更容易偷听，安全通信空间小。
- 这是本文最主要的“性能收益”指标。

### 2.2 `outage_prob`

`outage` 可以理解为“服务不达标”。项目里会设定一个最低安全速率门槛 `r_min`，如果某个时隙的真实安全速率低于这个门槛，就记为 outage。

`outage_prob` 是所有时隙中 outage 的比例，越低越好。

白话理解：

- `outage_prob = 0.20`：大约 20% 的时隙没有达到最低安全服务要求。
- `outage_prob = 1.00`：所有时隙都不达标。
- `outage_prob = 0.00`：所有时隙都达标。

在 2026-05-12 之前，`scenario_stress` 的 `r_min` 设得过高，导致几乎所有方法都是全 outage。后来把该场景的门槛校准为 `r_min = 1.10`，这个指标才重新有区分度。

### 2.3 `avg_sync_cost`

这是平均同步开销。同步能让数字孪生更准，但会消耗预算。

白话理解：

- 高：系统更频繁或更高带宽地同步，状态认知更好，但资源消耗更大。
- 低：系统更节省同步资源，但数字孪生可能变旧。

这个指标不是越低越好，而是要和 `avg_secrecy_rate`、`outage_prob` 一起看。如果一个方法几乎不同步但安全速率很差，那不是好方法；如果一个方法同步很多但收益不明显，也不是好方法。

### 2.4 `certificate_in_policy_cover_rate`

项目里有一个“证书”模型，用来估计数字孪生不准时可能造成多大的 secrecy loss。可以把它理解成一个保守安全垫：

> 如果我只知道一个有误差的 Eve 位置估计，那么我需要预留多少 margin，才能比较稳妥地说真实安全速率不会太糟？

`certificate_in_policy_cover_rate` 表示这个安全垫在策略实际运行轨迹上覆盖真实损失的比例。

白话理解：

- 高：证书给出的上界通常够保守。
- 低：证书经常低估风险，不可靠。

需要注意：这个指标是 controller 与 certificate 耦合后的 in-policy 指标。也就是说，它说明“在当前策略实际访问到的状态分布里，证书表现如何”。它不能直接被写成“对所有未知场景都有泛化保证”。

### 2.5 `certificate_empirical_cover_rate` 和 `certificate_margin_cover_rate`

这两个也是证书覆盖类指标。它们从不同角度检查证书是否覆盖了真实损失或 margin 风险。

在本文实验里，它们主要用于诊断证书是否足够保守。读者不需要记住公式，只需要知道：

- 接近 1：证书很保守，风险估计基本覆盖真实情况。
- 明显低于目标覆盖率：证书可能不够可靠。

### 2.6 `runtime_per_slot_ms`

这是每个时隙平均需要多少毫秒计算决策。越低越快。

白话理解：

- `periodic` 这类规则方法通常很快。
- `rollout_joint` 需要向前看、枚举候选动作，所以慢很多。
- PPO 推理很快，但本项目当前训练预算下性能不够强。

因此，`rollout_joint` 的优势不是速度，而是安全通信性能和鲁棒性。论文里应明确写成“性能-计算成本 tradeoff”。

### 2.7 `ci95`、配对比较和 `win_pairs`

表里的 `ci95` 是 95% 置信区间，用来描述多 seed 重复实验下结果的波动范围。直观理解：如果置信区间很窄，说明结果稳定；如果很宽，说明不同 seed 之间波动大。

配对比较会把相同 seed 下的两个方法成对相减，例如：

> seed 62 下 `rollout_joint` 比 `periodic` 高多少，seed 63 下高多少，依此类推。

`win_pairs` 表示 target 方法赢了多少个 seed。比如 `20 / 20` 表示 20 个 seed 全赢，这是很强的稳定性证据。

## 3. 实验场景怎么理解

主实验有三个场景：

### 3.1 `paper_base_holdoutfit`

这是较基础的论文场景。环境压力相对低，简单方法已经可以做得不错。因此主方法的提升会比较小。

这个场景适合说明：

- `rollout_joint` 在简单场景仍有收益。
- 但收益不大，且计算成本明显更高。
- 不应把它写成主方法最有说服力的收益场景。

### 3.2 `paper_hard_holdoutfit`

这是更困难的论文场景。Eve 行为、通信环境或同步限制让简单方法更吃力。

这个场景适合说明：

- 随着问题变难，联合前瞻控制的优势变明显。
- `rollout_joint` 对 secrecy-rate 的提升比 base 场景更大。

### 3.3 `scenario_stress_holdoutfit`

这是压力场景，也是本轮校准后最关键的结果。

旧门槛下这个场景几乎全 outage，无法比较不同方法的 outage。现在校准后，`outage_prob` 重新有了意义。

这个场景适合说明：

- `rollout_joint` 不仅提高 secrecy-rate，还能明显降低 outage。
- 同步、数字孪生、前瞻控制的耦合价值在高压力场景最清楚。

## 4. 主实验结果分析

主表来自：

- `results/final_2026-05-12/scheme_c_readiness_20seed/main_table.csv`
- `results/final_2026-05-12/scheme_c_readiness_20seed/paired_comparisons_rollout_joint.csv`

每个场景跑 20 个 seed，每个 seed 可以看成一次随机条件不同的重复试验。

| 场景 | rollout_joint secrecy | periodic secrecy | secrecy 增益 | rollout_joint outage | periodic outage | outage 改善 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `paper_base_holdoutfit` | 1.6429 | 1.6115 | +0.0314 | 0.8913 | 0.8913 | 0.0000 |
| `paper_hard_holdoutfit` | 1.4429 | 1.2803 | +0.1626 | 0.9482 | 0.9496 | +0.0014 |
| `scenario_stress_holdoutfit` | 1.2540 | 0.9858 | +0.2683 | 0.4294 | 0.6434 | +0.2141 |

### 4.1 base 场景：收益存在，但不是最强叙事点

在 `paper_base_holdoutfit` 中，`rollout_joint` 的平均安全速率是 `1.6429`，`periodic` 是 `1.6115`，提升 `+0.0314`。

配对统计显示，`rollout_joint` 在 20 个 seed 中赢了 19 个 seed，说明这个小幅提升不是偶然的。

但 outage 几乎没有改善，两者都是约 `0.8913`。这说明 base 场景中，主方法主要改善 secrecy-rate，而不是 outage。

写作建议：

> 在低压力场景中，`rollout_joint` 仍能稳定提升 secrecy-rate，但由于 baseline 已经较强，收益幅度有限；该场景应作为一致性证据，而不是最主要卖点。

### 4.2 hard 场景：secrecy-rate 提升明显

在 `paper_hard_holdoutfit` 中，`rollout_joint` 从 `periodic` 的 `1.2803` 提高到 `1.4429`，提升 `+0.1626`。

配对统计中，`rollout_joint` 对 `periodic` 是 20/20 seed 全胜。相比 base 场景，这里的提升已经很明显。

outage 方面，`rollout_joint` 是 `0.9482`，`periodic` 是 `0.9496`，只改善 `+0.0014`。这说明该场景的最低服务门槛仍然很难，大多数时隙仍达不到 outage 门槛。

写作建议：

> 在更困难的场景中，主方法对平均 secrecy-rate 的收益显著扩大，但 outage 仍受高压力门槛约束，改善幅度有限。

### 4.3 stress 场景：本轮最有说服力的结果

在 `scenario_stress_holdoutfit` 中，`rollout_joint` 的平均安全速率是 `1.2540`，`periodic` 是 `0.9858`，提升 `+0.2683`。

更重要的是 outage：

- `rollout_joint`: `0.4294`
- `periodic`: `0.6434`
- 改善：`+0.2141`

这意味着在压力场景中，`rollout_joint` 不只是让平均安全速率变高，还把“不达标时隙”的比例显著压低。

配对统计也很强：对 `periodic`、`security_risk`、`security_margin` 都是 20/20 seed 全胜。

写作建议：

> 在校准后的 stress 场景中，`rollout_joint` 同时带来 secrecy-rate 提升和 outage 降低，说明前瞻式联合同步与控制在高压力安全通信环境中最有价值。

## 5. 为什么 `rollout_joint` 会更好

简单方法通常只回答一个问题：

> 现在要不要同步？

而 `rollout_joint` 同时回答多个问题：

1. 现在要不要同步？
2. 如果同步，用多少带宽？
3. 两架 UAV 分别怎么移动？
4. 传输功率和干扰功率怎么选？
5. 这个动作对未来几步的状态和安全速率有什么影响？

因此它能避免一些短视决策。例如：

- 不是看到孪生变差就马上同步，而是判断同步是否真的能换来安全收益。
- 不是只追求当前时隙 secrecy-rate，而是考虑未来几步的 Eve 位置、孪生质量和 outage 风险。
- 不是把同步和轨迹控制分开做，而是联合决策。

这解释了为什么压力越大，`rollout_joint` 的优势越明显。

## 6. Holdout 证书结果分析

证书结果来自：

- `results/final_2026-05-12/scheme_c_holdout/holdout_summary.csv`

validation 覆盖率如下：

| split | 场景 | cover_rate |
| --- | --- | ---: |
| validation | `paper_base` | 0.9873 |
| validation | `paper_hard` | 1.0000 |
| validation | `scenario_stress` | 1.0000 |
| validation | all | 0.9964 |

这些数值都高于目标覆盖率 0.95，说明 holdout-fitted certificate 在验证轨迹上是足够保守的。

但要注意两个边界：

1. 覆盖率高不等于证书很紧。它可能很保守，也就是给了比较大的安全垫。
2. 这个证书目前主要支持当前策略分布下的安全解释，不能直接声称对所有未知场景都有严格理论泛化保证。

适合写进论文的表述是：

> The holdout-fitted certificate achieves validation cover rates above the target level, supporting its use as a conservative in-policy secrecy-loss upper bound.

不建议写成：

> The certificate guarantees safety under arbitrary unseen environments.

## 7. Stress Holdoutfit Baseline 补跑分析

本轮进一步补跑了统一口径的 `scenario_stress_holdoutfit` 下 PPO、SCA 和 strengthening suite。它们使用同一个 holdout-fitted 配置：

`results/final_2026-05-12/scheme_c_holdout/configs/scenario_stress_holdoutfit.yaml`

因此，这组三个补跑结果可以和 20-seed 主表放在同一实验口径下解释。此前使用 `configs/scenario_stress.yaml` 的补跑结果仍可保留为诊断结果，但投稿主文建议优先引用 holdout-fitted 版本。

### 7.1 SCA baseline

结果来自：

- `results/final_2026-05-12/sca_baselines_5seed_stress_holdoutfit/main_table.csv`

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.2558 | 0.4200 | 1316.34 |
| `sca_oracle` | 1.2126 | 0.8125 | 246.50 |
| `periodic` | 0.9955 | 0.6563 | 99.63 |
| `sca_twin` | 0.4677 | 0.8225 | 252.27 |

统一口径后，`rollout_joint` 的 secrecy-rate 也超过了 `sca_oracle`，同时 outage 明显更低。这说明在 holdout-fitted stress 场景中，主方法不是只靠平均值取胜，而是在“平均安全速率”和“达标稳定性”两方面都更强。

`sca_oracle` 使用真实 Eve 状态进行局部 SCA 评分，因此是一个很强的局部优化参考。但它仍然不是前瞻式联合同步控制：它不一定能像 `rollout_joint` 那样同时考虑同步预算、未来几步状态演化和 outage 风险。因此它的平均 secrecy-rate 低于 `rollout_joint`，outage 也明显更差。

`sca_twin` 表现很差，说明在压力场景中，如果优化器依赖不完美的 twin 状态，容易被错误状态估计误导。

### 7.2 PPO baseline

结果来自：

- `results/final_2026-05-12/drl_ppo_200ep_5seed_stress_holdoutfit/main_table.csv`

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.2558 | 0.4200 | 1318.07 |
| `periodic` | 0.9955 | 0.6563 | 98.85 |
| `ppo_baseline` | 0.3442 | 0.8463 | 6.33 |

PPO 的推理速度很快，但当前训练预算下性能明显弱于 `periodic` 和 `rollout_joint`。

这不能说明深度强化学习在这个问题上一定不可行，只能说明：

1. 在当前特征、动作空间和 200 episodes 训练预算下，PPO baseline 没有学到足够强的策略。
2. 模型驱动的前瞻式控制在小规模安全通信仿真中更样本高效。
3. 如果要把 PPO 写成强 baseline，需要更多训练预算、调参或更适合的策略结构。

### 7.3 Strengthening suite

结果来自：

- `results/final_2026-05-12/strengthening_suite_3seed_stress_holdoutfit/main_table.csv`

| method | secrecy | outage | 说明 |
| --- | ---: | ---: | --- |
| `oracle_sync` | 1.3121 | 0.0292 | oracle 上界参考 |
| `rollout_joint` | 1.2550 | 0.4083 | 提案方法 |
| `rollout_fixed_periodic` | 1.2142 | 0.5396 | 固定同步的 rollout |
| `periodic` | 1.0210 | 0.6417 | 规则同步对照 |
| `no_twin` | 0.9597 | 0.7021 | 移除 twin 后下降 |
| `rollout_no_sync` | 0.6670 | 0.8229 | 移除同步后下降 |

这组实验用于回答“主方法到底靠什么变强”。

结论一：数字孪生有价值。

`no_twin` 的 secrecy-rate 是 `0.9597`，低于 `rollout_joint` 的 `1.2550`。这说明如果不用 twin 预测 Eve 状态，rollout 的前瞻能力会明显下降。

结论二：同步有价值。

`rollout_no_sync` 的 secrecy-rate 只有 `0.6670`，outage 高达 `0.8229`。这说明只做前瞻轨迹/功率控制但不同步，无法在压力场景中维持可靠安全通信。

结论三：oracle 仍然是上界参考。

`oracle_sync` 的 secrecy-rate 和 outage 都明显优于可实现方法，因为它能使用真实 Eve 状态。这说明当前主方法和理想上界之间仍有空间，也为后续工作留下方向。

结论四：固定同步 rollout 与 joint rollout 各有取舍。

`rollout_fixed_periodic` 的 secrecy-rate 低于 `rollout_joint`，outage 也更差。这说明统一 holdout-fitted 口径下，固定同步 rollout 无法替代真正的联合同步决策；主方法的收益来自“rollout 控制”和“自适应同步”两者的组合。

## 8. 小 MDP 上界实验怎么理解

结果来自：

- `results/final_2026-05-12/small_mdp_bound/summary.csv`

| config | episode_length | optimal_avg_secrecy | num_states_evaluated | num_actions |
| --- | ---: | ---: | ---: | ---: |
| `configs/small_mdp_bound_final.yaml` | 4 | 2.3783 | 56,784 | 72 |

这个实验不是主场景实验，而是 sanity check。它把问题缩小到一个很小的 MDP，然后用 exact-DP 求最优值。

它的意义是：

1. 验证求解链路可运行。
2. 给一个小规模问题上的理论最优参考。
3. 说明在简化问题中，确实存在比启发式方法更高的上界。

它不应该直接和 `paper_base`、`paper_hard`、`scenario_stress` 的结果做数值比较，因为场景规模、动作空间和 episode length 都不同。

## 9. 计算成本分析

`rollout_joint` 的主要代价是慢。

例如 20-seed 主表中：

- `paper_base_holdoutfit`: `rollout_joint` 约 1265.75 ms/slot，`periodic` 约 99.65 ms/slot。
- `paper_hard_holdoutfit`: `rollout_joint` 约 1262.04 ms/slot，`periodic` 约 97.89 ms/slot。
- `scenario_stress_holdoutfit`: `rollout_joint` 约 1295.63 ms/slot，`periodic` 约 98.54 ms/slot。

也就是说，`rollout_joint` 通常比简单规则方法慢一个数量级以上。

这并不推翻主方法价值，但决定了论文叙事要诚实：

- 不能说 `rollout_joint` 是最快方法。
- 可以说它以更高计算成本换来了更高 secrecy-rate 和 stress 场景下更低 outage。
- 可以把未来工作写成减少候选动作、剪枝、学习辅助 rollout 或并行化加速。

## 10. 总体结论

综合所有结果，可以得到以下结论。

第一，`rollout_joint` 在三个主场景中都稳定提高平均安全通信速率。尤其在 `paper_hard_holdoutfit` 和 `scenario_stress_holdoutfit` 中，提升幅度明显。

第二，校准后的 `scenario_stress` 是最有说服力的场景。`rollout_joint` 不仅把 secrecy-rate 从 `0.9858` 提高到 `1.2540`，还把 outage 从 `0.6434` 降到 `0.4294`。

第三，配对统计支持主结论。`rollout_joint` 在 stress 主表中对 `periodic`、`security_risk`、`security_margin` 都是 20/20 seed 全胜；在统一 holdout-fitted SCA baseline 中，对 `periodic`、`sca_twin`、`sca_oracle` 也是 5/5 seed 全胜；在 strengthening suite 中，对除 `oracle_sync` 外的主要可实现方法也是 3/3 seed 全胜。

第四，证书模型的 holdout 覆盖率高于 0.95 目标，支持把它作为当前策略分布下的保守 secrecy-loss 上界使用。

第五，消融实验说明主方法的收益来自组合效应：只做同步规则不够，只做 rollout 但不同步也不够，移除 twin 会下降；同步、twin 和前瞻控制需要联合起来。

第六，`rollout_joint` 的短板是计算成本高。论文应把它定位为高性能、可解释、模型驱动的前瞻控制方法，而不是低延迟轻量 baseline。

## 11. 推荐论文写法

可以这样组织实验叙事：

1. 先用 20-seed 主表说明 `rollout_joint` 在三个场景中稳定提高 secrecy-rate。
2. 再强调校准后的 stress 场景：同时提升 secrecy-rate 和降低 outage，这是最强结果。
3. 用 holdout 证书结果说明 certificate 是保守且经过验证的。
4. 用 PPO/SCA baseline 说明简单学习 baseline 和局部优化 baseline 在压力场景下不足。
5. 用 strengthening suite 说明 twin、同步和联合前瞻控制都不可缺。
6. 最后承认 runtime tradeoff，并给出加速作为未来工作。

## 12. 推荐避免的表述

不建议写：

1. `rollout_joint` 全面优于所有方法。
2. 证书对任意未知场景提供严格理论保证。
3. PPO 方法本质上无效。
4. small MDP 的 optimal value 可以直接作为主场景上界。
5. base 场景中 outage 被显著改善。

更稳妥的写法是：

1. `rollout_joint` 在主实验中稳定提高 secrecy-rate，并在校准后的 stress 场景显著降低 outage。
2. holdout-fitted certificate 在验证轨迹上达到目标覆盖率，可作为 in-policy 保守风险估计。
3. PPO baseline 在当前训练预算下弱于模型驱动方法。
4. small MDP exact-DP 结果用于 sanity check，不直接参与主场景数值比较。
5. 主方法以更高计算成本换取更好的安全通信表现。
