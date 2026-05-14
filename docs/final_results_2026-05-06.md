# 最终实验结果（2026-05-06）

## 输出目录

本轮保留的全部实验输出都位于 `results/final_2026-05-06/`。

1. `scheme_c_holdout`：holdout 证书拟合与验证结果。
2. `scheme_c_readiness_20seed`：论文主表，20 个 seed。
3. `drl_ppo_200ep_5seed`：PPO baseline 实验线。
4. `sca_baselines_5seed`：SCA-twin 与 SCA-oracle baseline 实验线。
5. `strengthening_suite_3seed`：baseline 完整性与消融对照。
6. `small_mdp_bound_final`：缩小动作空间后的 exact-DP sanity check。

2026-05-09 修订说明：本文档保留 2026-05-06 已生成数值，但修正投稿解释口径。`scheme_c_holdout` 当时使用的 certificate train/eval 方法集合不同，因此其 cover_rate 只作为诊断结果；投稿前应使用已修正的 pipeline 重新生成 holdout，其中 train/eval 方法集合均为 `periodic`、`security_risk`、`security_margin`、`rollout_joint`。

## 20-seed 主实验结果

`rollout_joint` 是三个主场景中表现最好的非 oracle 方法。

| 场景 | rollout_joint secrecy | periodic secrecy | 增益 |
| --- | ---: | ---: | ---: |
| paper_base_holdoutfit | 1.6421 | 1.6141 | +0.0281 |
| paper_hard_holdoutfit | 1.4426 | 1.2804 | +0.1621 |
| scenario_stress_holdoutfit | 1.2533 | 0.9826 | +0.2707 |

配对统计检验支持上述增益。以 `periodic` 为对照时，`rollout_joint` 在 `paper_base_holdoutfit` 中 19/20 个 seed 胜出，在 `paper_hard_holdoutfit` 和 `scenario_stress_holdoutfit` 中均为 20/20 个 seed 胜出；Holm 校正后仍显著。

解释重点需要分场景处理。`paper_base_holdoutfit` 是低压力场景，`rollout_joint` 相对 `periodic` 的 secrecy gain 为 `+0.0281`，但 runtime 约为 `12.7x`，因此应写成性能-计算成本 tradeoff，而不是主要收益场景。`scenario_stress_holdoutfit` 这组旧结果使用 `r_min = 2.82`，该门限经 2026-05-12 诊断确认高于 stress 场景的可达时隙保密速率，因此所有主方法的 outage 都为 `1.0000`。旧表不能声称降低 outage，只能强调 secrecy-rate 提升；投稿版应使用已校准的 `configs/scenario_stress.yaml`（`r_min = 1.10`）重新生成 holdout 与主表。

## 证书覆盖率

Holdout validation 的覆盖率均高于 0.95 目标。

| split | 场景 | cover_rate |
| --- | --- | ---: |
| validation | paper_base | 1.0000 |
| validation | paper_hard | 1.0000 |
| validation | scenario_stress | 0.9843 |
| validation | all | 0.9940 |

解释边界：旧表里的 `certificate_cover_rate` 对应后续代码中的 `certificate_in_policy_cover_rate`，是 controller 与 certificate 耦合后的 in-policy 覆盖/合规指标，因为 certificate slack 同时进入控制器打分。它不能单独表述为 out-of-distribution certificate 泛化能力。2026-05-06 的 holdout 结果还受到 train/eval 方法集合不一致影响，投稿版应以修正后重跑的 holdout 表为准。

## DRL/PPO 实验线

PPO baseline 每个场景训练 200 episodes，并在 5 个 seed 上评估。它的推理速度很快，但在当前训练预算下明显弱于 `periodic` 与 `rollout_joint`。

| 场景 | PPO secrecy | periodic secrecy | rollout_joint secrecy |
| --- | ---: | ---: | ---: |
| paper_base | 0.7853 | 1.6056 | 1.6455 |
| paper_hard | 0.5029 | 1.2951 | 1.4490 |
| scenario_stress | 0.2343 | 0.9970 | 1.2542 |

## SCA 实验线

SCA-oracle 可作为有用的上界参考；SCA-twin 在 `paper_base` 与 `paper_hard` 中具有竞争力，但在 `scenario_stress` 下明显退化。

| 场景 | SCA-oracle | SCA-twin | rollout_joint |
| --- | ---: | ---: | ---: |
| paper_base | 1.6708 | 1.6224 | 1.6455 |
| paper_hard | 1.4879 | 1.4442 | 1.4490 |
| scenario_stress | 1.2150 | 0.4652 | 1.2542 |

## Baseline 完整性

3-seed strengthening suite 覆盖了 rule-based、stochastic、no-sync、no-twin、SCA、oracle 与 rollout 变体。结果支持主叙事：`rollout_joint` 在各场景中稳定较强，`oracle_sync` 是上界参考，而 `no_twin` 与 `rollout_no_sync` 说明维护并使用 twin 对性能有实际价值。

## 小 MDP 上界

原始 exact-DP 配置动作空间过大，不适合同步纳入本轮最终重跑。因此本轮使用缩小动作空间的 exact-DP sanity check，完成了 72 个动作、56,784 个抽象状态的求解。

| config | episode_length | optimal_avg_secrecy | num_states_evaluated |
| --- | ---: | ---: | ---: |
| configs/small_mdp_bound_final.yaml | 4 | 2.3783 | 56784 |

该结果只用于验证 exact-DP 求解链路可运行，不应直接与三个论文尺度场景做数值比较。
