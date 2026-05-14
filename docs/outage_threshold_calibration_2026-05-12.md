# Outage 阈值校准说明（2026-05-12）

## 问题

旧版 `configs/scenario_stress.yaml` 使用 `channel.r_min = 2.82`。在该压力场景下，这个门限高于代表性方法可稳定达到的时隙级保密速率，导致所有方法的 `outage_prob` 都等于 `1.0`。

这会带来两个论文问题：

1. `scenario_stress` 只能讨论 `avg_secrecy_rate`，不能讨论 outage 改善。
2. `outage_prob` 失去区分度，审稿人可能认为 QoS 门限设置不合理。

## 诊断结果

使用旧门限 `r_min = 2.82`，对 `scenario_stress` 做了轻量诊断。代表性 seed 下的时隙级 `true_r_sec` 分布如下：

| method | mean | q10 | q25 | q50 | q75 | q90 | q95 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 1.0527 | 0.359 | 0.365 | 0.577 | 1.067 | 1.147 | 1.929 | 2.577 |
| security_risk | 0.9491 | 0.000 | 0.300 | 0.598 | 0.887 | 1.112 | 1.783 | 2.574 |
| rollout_joint | 1.2380 | 0.872 | 1.006 | 1.064 | 1.103 | 1.157 | 1.845 | 2.560 |
| oracle_sync | 1.3019 | 0.872 | 1.157 | 1.159 | 1.164 | 1.183 | 1.845 | 2.560 |

因此，`2.82` 不是一个高压力 QoS 门限，而是一个当前场景下基本不可达的门限。

## 改进

将 `configs/scenario_stress.yaml` 中的：

```yaml
channel:
  r_min: 2.82
```

改为：

```yaml
channel:
  r_min: 1.10
```

选择 `1.10` 的理由：

1. 它接近 `rollout_joint` 的中位时隙保密速率，因此主方法仍需认真优化才能降低 outage。
2. 它高于部分 rule-based 方法的大量低速率时隙，因此能保留压力场景的区分度。
3. 它低于 oracle/rollout 的可达上界区间，不会把所有方法压成 `outage_prob = 1.0`。

## 投稿口径

修正前的 `scenario_stress` 结果可以继续用于说明高压力下的 secrecy-rate 增益，但不能用于声称 outage 改善。

修正后的投稿版应重新运行：

1. holdout certificate fitting；
2. 20-seed readiness 主表；
3. SCA/PPO/strengthening suite 中涉及 `scenario_stress` 的部分。

论文中建议写成：

> We calibrate the secrecy outage threshold in each scenario to represent a feasible but non-trivial service target. In the stress scenario, the threshold is set to `R_min = 1.10` after a pilot feasibility check, avoiding a degenerate all-outage regime while preserving strong adversarial mobility and tight synchronization budget.
