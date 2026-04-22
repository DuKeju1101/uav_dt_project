# 方案 C 重跑结果（2026-04-22）

## 1. 运行设置

1. 改动口径：全部 P0 + 全部 P1。
2. 关键机制：Kalman twin、conformal certificate、adaptive Eve、概率 LoS/NLoS 信道、连续带宽同步、扩展动作空间。
3. 主表场景：`paper_base`、`paper_hard`、`scenario_stress`。
4. 主表方法：`periodic`、`security_risk`、`security_margin`、`rollout_joint`、`risk_adaptive_hybrid_rollout`。
5. 验证 seed：`62-81`。

结果文件：
1. [summary.csv](../results/scheme_c_readiness_20seed_2026-04-22/summary.csv)
2. [main_table.csv](../results/scheme_c_readiness_20seed_2026-04-22/main_table.csv)
3. [all_runs.csv](../results/scheme_c_readiness_20seed_2026-04-22/all_runs.csv)
4. [paired_comparisons_rollout_joint.csv](../results/scheme_c_readiness_20seed_2026-04-22/paired_comparisons_rollout_joint.csv)
5. [holdout_summary.csv](../results/scheme_c_holdout_2026-04-22/holdout_summary.csv)
6. [small_mdp summary.csv](../results/scheme_c_small_mdp_toy_2026-04-22/summary.csv)

## 2. 主表

| scenario | method | num_runs | avg_secrecy_rate_mean | avg_secrecy_rate_ci95 | outage_prob_mean | outage_prob_ci95 | avg_sync_cost_mean | certificate_cover_rate_mean | runtime_per_slot_ms_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| paper_base_holdoutfit | periodic | 20 | 1.6315 | 0.0100 | 0.8879 | 0.0038 | 0.1500 | 1.0000 | 101.94 |
| paper_base_holdoutfit | risk_adaptive_hybrid_rollout | 20 | 1.5680 | 0.0172 | 0.8975 | 0.0034 | 0.1648 | 0.5521 | 165.16 |
| paper_base_holdoutfit | security_risk | 20 | 1.5096 | 0.0257 | 0.8875 | 0.0037 | 0.0375 | 0.9996 | 101.22 |
| paper_base_holdoutfit | rollout_joint | 20 | 0.9928 | 0.0062 | 0.8871 | 0.0034 | 0.0000 | 1.0000 | 160.99 |
| paper_base_holdoutfit | security_margin | 20 | 0.7991 | 0.0484 | 0.8962 | 0.0036 | 0.2331 | 0.8125 | 100.21 |
| paper_hard_holdoutfit | risk_adaptive_hybrid_rollout | 20 | 1.3901 | 0.0133 | 0.9561 | 0.0045 | 0.1310 | 0.6821 | 160.65 |
| paper_hard_holdoutfit | periodic | 20 | 1.2948 | 0.0095 | 0.9482 | 0.0044 | 0.1571 | 1.0000 | 101.78 |
| paper_hard_holdoutfit | security_risk | 20 | 1.2435 | 0.0363 | 0.9432 | 0.0036 | 0.0362 | 0.9911 | 100.96 |
| paper_hard_holdoutfit | rollout_joint | 20 | 0.7872 | 0.0052 | 0.9450 | 0.0027 | 0.0000 | 1.0000 | 158.98 |
| paper_hard_holdoutfit | security_margin | 20 | 0.5668 | 0.0537 | 0.9557 | 0.0044 | 0.1570 | 0.9046 | 101.59 |
| scenario_stress_holdoutfit | periodic | 20 | 0.9887 | 0.0212 | 1.0000 | 0.0000 | 0.1187 | 0.9981 | 99.39 |
| scenario_stress_holdoutfit | security_risk | 20 | 0.9646 | 0.0304 | 1.0000 | 0.0000 | 0.0395 | 0.9925 | 117.62 |
| scenario_stress_holdoutfit | risk_adaptive_hybrid_rollout | 20 | 0.7806 | 0.0428 | 1.0000 | 0.0000 | 0.1187 | 0.7206 | 402.09 |
| scenario_stress_holdoutfit | rollout_joint | 20 | 0.7775 | 0.0318 | 1.0000 | 0.0000 | 0.1187 | 0.7003 | 215.66 |
| scenario_stress_holdoutfit | security_margin | 20 | 0.3217 | 0.0063 | 1.0000 | 0.0000 | 0.1185 | 0.9166 | 112.02 |

## 3. Holdout 证书覆盖

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

## 4. 配对比较

| scenario | baseline | target | n | mean_secrecy_gain | mean_outage_gain | mean_runtime_delta_ms | paired_t_stat | paired_t_pvalue_approx | secrecy_win_seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| paper_base_holdoutfit | periodic | rollout_joint | 20 | -0.6387 | 0.0008 | 59.0487 | -151.4987 | 0.0000 | 0 |
| paper_base_holdoutfit | security_risk | rollout_joint | 20 | -0.5168 | 0.0004 | 59.7685 | -40.5168 | 0.0000 | 0 |
| paper_base_holdoutfit | security_margin | rollout_joint | 20 | 0.1938 | 0.0092 | 60.7761 | 8.0434 | 0.0000 | 19 |
| paper_hard_holdoutfit | periodic | rollout_joint | 20 | -0.5076 | 0.0032 | 57.1955 | -103.4949 | 0.0000 | 0 |
| paper_hard_holdoutfit | security_risk | rollout_joint | 20 | -0.4563 | -0.0018 | 58.0132 | -24.9295 | 0.0000 | 0 |
| paper_hard_holdoutfit | security_margin | rollout_joint | 20 | 0.2204 | 0.0107 | 57.3855 | 8.1980 | 0.0000 | 18 |
| scenario_stress_holdoutfit | periodic | rollout_joint | 20 | -0.2112 | 0.0000 | 116.2677 | -11.9467 | 0.0000 | 0 |
| scenario_stress_holdoutfit | security_risk | rollout_joint | 20 | -0.1871 | 0.0000 | 98.0368 | -7.7405 | 0.0000 | 0 |
| scenario_stress_holdoutfit | security_margin | rollout_joint | 20 | 0.4558 | 0.0000 | 103.6412 | 27.1706 | 0.0000 | 20 |

## 5. 小场景理论上界

| config | seed | episode_length | optimal_cumulative_secrecy | optimal_avg_secrecy | num_states_evaluated | num_actions | state_abstraction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| configs/small_mdp_bound_toy.yaml | 42 | 4 | 10.1747 | 2.5437 | 12502 | 72 | rounded_state_dp(pos=0.1,twin=0.01,cov=0.01) |

## 6. 结论摘要

1. `paper_base_holdoutfit`: 最高 secrecy 是 `periodic` (1.6315)，最低 outage 是 `rollout_joint` (0.8871)，最快方法是 `security_margin` (100.21 ms/slot)。
1. `paper_hard_holdoutfit`: 最高 secrecy 是 `risk_adaptive_hybrid_rollout` (1.3901)，最低 outage 是 `security_risk` (0.9432)，最快方法是 `security_risk` (100.96 ms/slot)。
1. `scenario_stress_holdoutfit`: 最高 secrecy 是 `periodic` (0.9887)，最低 outage 是 `periodic` (1.0000)，最快方法是 `periodic` (99.39 ms/slot)。
2. 如果 `rollout_joint` 在某些场景 secrecy 最优但 outage 不是最优，这说明方案 C 更适合写成性能-成本-鲁棒性 tradeoff 叙事。
3. 如果 holdout `cover_rate` 接近设定覆盖率以上，conformal certificate 的统计保证叙事可以保留到论文正文。

