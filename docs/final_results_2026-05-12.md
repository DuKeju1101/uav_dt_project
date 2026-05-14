# 最终实验结果（2026-05-12）

## 输出目录

本轮结果位于 `results/final_2026-05-12/`。其中 holdout 与 20-seed 主表在 2026-05-12 已完成，断电后缺失的后续结果已在 2026-05-13 补跑完成。

1. `scheme_c_holdout`：holdout 证书拟合与验证结果。
2. `scheme_c_readiness_20seed`：论文主表，20 个 seed。
3. `small_mdp_bound`：缩小动作空间后的 exact-DP sanity check。
4. `sca_baselines_5seed_stress`：校准后 `scenario_stress` 的 SCA baseline 补跑。
5. `drl_ppo_200ep_5seed_stress`：校准后 `scenario_stress` 的 PPO baseline 补跑。
6. `strengthening_suite_3seed_stress`：校准后 `scenario_stress` 的 baseline 完整性与消融补跑。
7. `sca_baselines_5seed_stress_holdoutfit`：统一 holdout-fitted 口径下的 SCA baseline。
8. `drl_ppo_200ep_5seed_stress_holdoutfit`：统一 holdout-fitted 口径下的 PPO baseline。
9. `strengthening_suite_3seed_stress_holdoutfit`：统一 holdout-fitted 口径下的 baseline 完整性与消融。

## 20-seed 主实验结果

校准后的 `scenario_stress` 已不再是全 outage，`rollout_joint` 在三个主场景中均保持最高 secrecy-rate。

| 场景 | rollout_joint secrecy | periodic secrecy | secrecy 增益 | rollout_joint outage | periodic outage | outage 改善 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `paper_base_holdoutfit` | 1.6429 | 1.6115 | +0.0314 | 0.8913 | 0.8913 | 0.0000 |
| `paper_hard_holdoutfit` | 1.4429 | 1.2803 | +0.1626 | 0.9482 | 0.9496 | +0.0014 |
| `scenario_stress_holdoutfit` | 1.2540 | 0.9858 | +0.2683 | 0.4294 | 0.6434 | +0.2141 |

主表文件：

1. `results/final_2026-05-12/scheme_c_readiness_20seed/main_table.csv`
2. `results/final_2026-05-12/scheme_c_readiness_20seed/all_runs.csv`
3. `results/final_2026-05-12/scheme_c_readiness_20seed/paired_comparisons_rollout_joint.csv`

## Holdout 证书覆盖

validation 覆盖率仍高于 0.95 目标。

| split | 场景 | cover_rate |
| --- | --- | ---: |
| validation | `paper_base` | 0.9873 |
| validation | `paper_hard` | 1.0000 |
| validation | `scenario_stress` | 1.0000 |
| validation | all | 0.9964 |

解释边界：主表中的 certificate cover 指标是 controller 与 certificate 耦合后的 in-policy 覆盖/合规指标；若要表述 out-of-distribution 泛化能力，需要额外的去耦验证。

## Stress Baseline 补跑

### 统一 holdout-fitted 口径结果（推荐论文引用）

投稿主结果建议优先引用这组三个目录，因为它们与 20-seed 主表一样使用 `scenario_stress_holdoutfit.yaml`。

SCA baseline：

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.2558 | 0.4200 | 1316.34 |
| `sca_oracle` | 1.2126 | 0.8125 | 246.50 |
| `periodic` | 0.9955 | 0.6563 | 99.63 |
| `sca_twin` | 0.4677 | 0.8225 | 252.27 |

PPO baseline：

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.2558 | 0.4200 | 1318.07 |
| `periodic` | 0.9955 | 0.6563 | 98.85 |
| `ppo_baseline` | 0.3442 | 0.8463 | 6.33 |

Strengthening suite：

| method | secrecy | outage | 说明 |
| --- | ---: | ---: | --- |
| `oracle_sync` | 1.3121 | 0.0292 | oracle 上界参考 |
| `rollout_joint` | 1.2550 | 0.4083 | 提案方法 |
| `rollout_fixed_periodic` | 1.2142 | 0.5396 | 固定同步的 rollout |
| `periodic` | 1.0210 | 0.6417 | 规则同步对照 |
| `no_twin` | 0.9597 | 0.7021 | 移除 twin 后下降 |
| `rollout_no_sync` | 0.6670 | 0.8229 | 移除同步后下降 |

统一口径补跑显示：`rollout_joint` 在 holdout-fitted stress 场景中不仅优于 `periodic`、PPO 和 `sca_twin`，也在 5-seed SCA baseline 中超过 `sca_oracle` 的平均 secrecy-rate，并显著降低 outage。Strengthening suite 中，`rollout_joint` 仍低于 `oracle_sync` 上界，但明显优于 `no_twin` 和 `rollout_no_sync`，说明 twin、同步与联合前瞻控制共同贡献了性能提升。

文件：

1. `results/final_2026-05-12/sca_baselines_5seed_stress_holdoutfit/main_table.csv`
2. `results/final_2026-05-12/drl_ppo_200ep_5seed_stress_holdoutfit/main_table.csv`
3. `results/final_2026-05-12/strengthening_suite_3seed_stress_holdoutfit/main_table.csv`

### 原始 calibrated stress 诊断结果

以下三组结果使用 `configs/scenario_stress.yaml`，主要作为诊断与一致性参考；投稿主文建议优先引用上面的 holdout-fitted 统一口径结果。

### SCA baseline

`sca_oracle` 在 secrecy-rate 上略高于 `rollout_joint`，但 outage 明显更差；`sca_twin` 在该压力场景下退化明显。

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `sca_oracle` | 1.2100 | 0.8125 | 250.51 |
| `rollout_joint` | 1.1699 | 0.4975 | 1303.68 |
| `periodic` | 1.0069 | 0.6675 | 104.06 |
| `sca_twin` | 0.4670 | 0.8225 | 253.84 |

文件：`results/final_2026-05-12/sca_baselines_5seed_stress/main_table.csv`

### PPO baseline

PPO baseline 训练 200 episodes，并在 5 个 seed 上评估。结果仍明显弱于 `periodic` 与 `rollout_joint`。

| method | secrecy | outage | runtime ms/slot |
| --- | ---: | ---: | ---: |
| `rollout_joint` | 1.1699 | 0.4975 | 1245.49 |
| `periodic` | 1.0069 | 0.6675 | 96.72 |
| `ppo_baseline` | 0.3002 | 0.8538 | 6.17 |

文件：`results/final_2026-05-12/drl_ppo_200ep_5seed_stress/main_table.csv`

### Strengthening suite

3-seed 消融补跑支持两个结论：`rollout_joint` 显著优于不使用 twin 或不同步的 rollout 变体；`oracle_sync` 仍是上界参考。

| method | secrecy | outage | 说明 |
| --- | ---: | ---: | --- |
| `oracle_sync` | 1.3150 | 0.0271 | oracle 上界参考 |
| `rollout_fixed_periodic` | 1.2193 | 0.5021 | 固定同步的 rollout |
| `rollout_joint` | 1.1766 | 0.4917 | 提案方法 |
| `periodic` | 1.0223 | 0.6521 | rule-based 对照 |
| `no_twin` | 0.9462 | 0.7479 | 移除 twin 后下降 |
| `rollout_no_sync` | 0.6668 | 0.8229 | 移除同步后下降 |

文件：`results/final_2026-05-12/strengthening_suite_3seed_stress/main_table.csv`

## 小 MDP 上界

使用 `configs/small_mdp_bound_final.yaml` 完成 exact-DP sanity check。

| config | episode_length | optimal_avg_secrecy | num_states_evaluated | num_actions |
| --- | ---: | ---: | ---: | ---: |
| `configs/small_mdp_bound_final.yaml` | 4 | 2.3783 | 56,784 | 72 |

该结果只用于验证 exact-DP 求解链路可运行，不应直接与三个论文尺度场景做数值比较。

## 完整性核对

1. `scheme_c_readiness_20seed/all_runs.csv`：240 条实验记录。
2. `sca_baselines_5seed_stress/all_runs.csv`：20 条实验记录。
3. `drl_ppo_200ep_5seed_stress/all_runs.csv`：15 条实验记录。
4. `strengthening_suite_3seed_stress/all_runs.csv`：45 条实验记录。
5. `small_mdp_bound/summary.csv`：1 条 summary。

至此，2026-05-12 校准后要求补跑的 holdout、20-seed 主表、small MDP、PPO/SCA/strengthening stress 结果均已生成。
