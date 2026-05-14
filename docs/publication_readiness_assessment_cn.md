# 论文可发表性评估与最终实验结论

本文基于 `results/final_2026-05-12/` 的最终结果，评估当前项目是否已经具备发表论文的条件。

## 1. 结论先行

当前项目已经具备写成论文并投稿的基础。相比补跑前，现在最大的短板之一已经解决：stress 场景下的 SCA、PPO、strengthening suite 已经使用同一个 holdout-fitted 配置重新补跑，因此主表、baseline 和消融实验的口径可以统一。

综合判断：

1. 若目标是 workshop、普通会议或应用型会议：当前实验支撑已经比较充分。
2. 若目标是较强会议或正式期刊：可以进入论文写作阶段，但仍建议在写作中主动承认 runtime、certificate 泛化边界和 PPO 训练预算限制。
3. 当前最适合的论文定位是：模型驱动、可解释、数字孪生感知的 UAV 安全通信联合同步与控制方法。

## 2. 推荐收束后的论文贡献点

建议把贡献收束成四条，不要把所有工程模块都写成贡献。

### 贡献 1：数字孪生感知的 UAV 安全通信联合控制框架

本文建模了一个包含 UAV、Eve、地面用户、同步预算和数字孪生误差的安全通信环境。问题重点不是传统“完美状态已知”控制，而是在 Eve 位置估计会老化、同步有代价的条件下，联合考虑安全通信与状态同步。

### 贡献 2：`rollout_joint` 前瞻式联合策略

`rollout_joint` 同时决定：

1. 是否同步；
2. 同步带宽；
3. 两架 UAV 的运动；
4. 发射功率与干扰功率；
5. 当前动作对未来几步安全速率、outage、certificate 风险和孪生状态的影响。

这比 `periodic`、`security_risk`、`security_margin` 等规则型方法更完整。

### 贡献 3：holdout-fitted empirical secrecy-loss certificate

项目用 holdout/validation 方式拟合并验证 conservative secrecy-loss certificate。验证覆盖率高于 0.95 目标：

| split | 场景 | cover_rate |
| --- | --- | ---: |
| validation | `paper_base` | 0.9873 |
| validation | `paper_hard` | 1.0000 |
| validation | `scenario_stress` | 1.0000 |
| validation | all | 0.9964 |

这支持把 certificate 写成当前策略分布下经过验证的保守风险估计模块。

### 贡献 4：多 seed 实验证明 stress 场景下同时提升 secrecy-rate 并降低 outage

在 20-seed 主实验中，`rollout_joint` 在三个主场景中都提高平均安全通信速率，并且在校准后的 stress 场景中明显降低 outage。

| 场景 | rollout_joint secrecy | periodic secrecy | secrecy 增益 | rollout_joint outage | periodic outage | outage 改善 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `paper_base_holdoutfit` | 1.6429 | 1.6115 | +0.0314 | 0.8913 | 0.8913 | 0.0000 |
| `paper_hard_holdoutfit` | 1.4429 | 1.2803 | +0.1626 | 0.9482 | 0.9496 | +0.0014 |
| `scenario_stress_holdoutfit` | 1.2540 | 0.9858 | +0.2683 | 0.4294 | 0.6434 | +0.2141 |

其中 `scenario_stress_holdoutfit` 是最强结果：主方法同时提升 secrecy-rate 和降低 outage。

## 3. 统一口径补跑后的最终实验结果

统一口径补跑使用：

`results/final_2026-05-12/scheme_c_holdout/configs/scenario_stress_holdoutfit.yaml`

因此它们可以和 20-seed 主表一起作为投稿主实验支撑。

### 3.1 SCA baseline

结果目录：

`results/final_2026-05-12/sca_baselines_5seed_stress_holdoutfit/`

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.2558 | 0.4200 | 1316.34 |
| `sca_oracle` | 1.2126 | 0.8125 | 246.50 |
| `periodic` | 0.9955 | 0.6563 | 99.63 |
| `sca_twin` | 0.4677 | 0.8225 | 252.27 |

解释：`rollout_joint` 在 5 个 seed 中均优于 `periodic`、`sca_twin` 和 `sca_oracle`。这说明局部 SCA 优化即使使用 oracle 状态，也不一定能替代前瞻式联合同步控制。

### 3.2 PPO baseline

结果目录：

`results/final_2026-05-12/drl_ppo_200ep_5seed_stress_holdoutfit/`

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.2558 | 0.4200 | 1318.07 |
| `periodic` | 0.9955 | 0.6563 | 98.85 |
| `ppo_baseline` | 0.3442 | 0.8463 | 6.33 |

解释：PPO 推理很快，但在 200 episodes 的轻量训练预算下表现明显弱于模型驱动方法。论文中应把它写成 lightweight DRL baseline，而不是强 DRL baseline。

### 3.3 Strengthening suite

结果目录：

`results/final_2026-05-12/strengthening_suite_3seed_stress_holdoutfit/`

| method | secrecy | outage | 说明 |
| --- | ---: | ---: | --- |
| `oracle_sync` | 1.3121 | 0.0292 | oracle 上界参考 |
| `rollout_joint` | 1.2550 | 0.4083 | 提案方法 |
| `rollout_fixed_periodic` | 1.2142 | 0.5396 | 固定同步 rollout |
| `periodic` | 1.0210 | 0.6417 | 规则同步对照 |
| `no_twin` | 0.9597 | 0.7021 | 移除 twin |
| `rollout_no_sync` | 0.6670 | 0.8229 | 移除同步 |

解释：

1. `oracle_sync` 仍是上界参考，说明真实 Eve 状态仍然有额外价值。
2. `rollout_joint` 明显优于 `rollout_fixed_periodic`，说明自适应同步决策有贡献。
3. `rollout_joint` 明显优于 `no_twin`，说明数字孪生预测有贡献。
4. `rollout_joint` 明显优于 `rollout_no_sync`，说明同步机制有贡献。

## 4. 当前是否具备发表条件

我的判断是：已经具备投稿型论文的核心条件。

理由如下。

第一，研究问题清楚。项目围绕数字孪生老化、同步预算有限、Eve 移动和安全通信性能之间的耦合展开，不是简单堆 baseline。

第二，方法有明确创新点。`rollout_joint` 把同步、轨迹、功率、干扰和 certificate-aware 风险控制放在一个前瞻式联合决策框架中。

第三，实验结果支持主 claim。20-seed 主表中，`rollout_joint` 在三个场景都提高 secrecy-rate；stress 场景同时降低 outage。

第四，baseline 和消融已经比较完整。现在已有 `periodic`、`security_risk`、`security_margin`、PPO、SCA、`no_twin`、`rollout_no_sync`、`rollout_fixed_periodic`、`oracle_sync` 和 small MDP sanity check。

第五，之前的口径不一致问题已经补强。stress 场景的 SCA/PPO/strengthening 现在已有 holdout-fitted 统一口径版本。

## 5. 仍需主动承认的局限

### 5.1 runtime 较高

`rollout_joint` 通常约 1.2 到 1.3 秒/slot，而 `periodic` 约 0.1 秒/slot。论文中不能声称主方法轻量或实时性最好。

推荐写法：

> The proposed rollout controller trades computational cost for improved secrecy and outage performance. It is currently more suitable for edge-assisted planning or moderate-timescale control than ultra-low-latency onboard execution.

### 5.2 certificate 是 empirical / in-policy

当前 certificate 是 holdout 验证的经验保守上界，不是任意未知环境下的严格数学保证。

推荐写法：

> The certificate should be interpreted as a holdout-validated in-policy secrecy-loss upper bound, rather than a universal out-of-distribution safety guarantee.

### 5.3 PPO baseline 训练预算有限

PPO 结果可以作为 lightweight DRL baseline，但不能用来否定所有 DRL 方法。

推荐写法：

> The PPO baseline is evaluated under a lightweight training budget. Stronger DRL baselines with larger training budgets and tuned architectures are left for future work.

## 6. 投稿前建议补充的最小工作

当前实验已经够支撑论文，但投稿前建议再做三件小事：

1. 把论文主表、SCA/PPO/strengthening holdoutfit 表统一整理成 paper-ready 表格。
2. 在方法章节明确 `rollout_joint` 的计算复杂度来源，并给出候选动作数量、rollout horizon 等关键参数。
3. 在 Discussion 里主动写清楚 runtime、certificate 和 PPO baseline 的边界。

这些不一定需要继续大规模跑实验，主要是论文组织和表格整理工作。

## 7. 最终判断

当前阶段已经从“实验探索阶段”进入“论文成稿阶段”。

可以给出如下结论：

> The project is experimentally ready for paper drafting. The main claims are supported by multi-seed results, holdout-validated certificates, consistent stress-scenario baselines, and ablation studies. The remaining work is primarily paper framing, table polishing, and transparent discussion of computational and generalization limitations.

中文概括：

> 当前实验已经具备发表论文的基本条件。若目标是普通会议或应用型论文，可以开始组织投稿；若目标是更强会议或期刊，建议重点打磨论文叙事、复杂度分析和局限讨论，而不是再盲目增加实验数量。
