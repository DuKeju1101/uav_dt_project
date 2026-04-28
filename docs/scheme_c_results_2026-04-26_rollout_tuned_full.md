# 方案 C 调优后完整重跑结果（2026-04-26）

## 1. 运行设置

本次实验使用当前调优后的三个主场景配置重新生成 holdout-fit 配置，并重新跑完整 `20-seed` 主实验。

关键口径：

1. 场景：`paper_base`、`paper_hard`、`scenario_stress`
2. 方法：`periodic`、`security_risk`、`security_margin`、`rollout_joint`
3. seeds：`62-81`
4. 记录数：`3 场景 × 4 方法 × 20 seeds = 240`
5. 主方法：`rollout_joint`

结果目录：

1. [holdout-fit 目录](../results/scheme_c_holdout_2026-04-26_rollout_tuned_full)
2. [12 个分块目录](../results/scheme_c_readiness_parallel_2026-04-26_rollout_tuned_full)
3. [合并总目录](../results/scheme_c_readiness_20seed_2026-04-26_rollout_tuned_full_merged)
4. [main_table.csv](../results/scheme_c_readiness_20seed_2026-04-26_rollout_tuned_full_merged/main_table.csv)
5. [all_runs.csv](../results/scheme_c_readiness_20seed_2026-04-26_rollout_tuned_full_merged/all_runs.csv)

## 2. 完成性检查

本次合并共读取 `12` 个分块，每个 `scenario × method` 都有 `20` 个 seed。

| scenario | methods | seeds per method | status |
| --- | ---: | ---: | --- |
| `paper_base_holdoutfit` | 4 | 20 | complete |
| `paper_hard_holdoutfit` | 4 | 20 | complete |
| `scenario_stress_holdoutfit` | 4 | 20 | complete |

## 3. 主表结果

| scenario | method | num_runs | avg_secrecy_rate_mean | avg_secrecy_rate_ci95 | outage_prob_mean | outage_prob_ci95 | avg_sync_cost_mean | certificate_cover_rate_mean | runtime_per_slot_ms_mean | secrecy_gain_vs_periodic |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `paper_base_holdoutfit` | `rollout_joint` | 20 | 1.6522 | 0.0050 | 0.8854 | 0.0033 | 0.1988 | 0.9992 | 419.04 | 0.0208 |
| `paper_base_holdoutfit` | `periodic` | 20 | 1.6313 | 0.0110 | 0.8871 | 0.0042 | 0.1500 | 1.0000 | 165.16 | 0.0000 |
| `paper_base_holdoutfit` | `security_risk` | 20 | 1.5147 | 0.0139 | 0.8904 | 0.0043 | 0.0369 | 1.0000 | 165.00 | -0.1166 |
| `paper_base_holdoutfit` | `security_margin` | 20 | 0.7672 | 0.0348 | 0.8962 | 0.0036 | 0.2333 | 0.8354 | 168.04 | -0.8641 |
| `paper_hard_holdoutfit` | `rollout_joint` | 20 | 1.4627 | 0.0067 | 0.9461 | 0.0042 | 0.1031 | 1.0000 | 1763.40 | 0.1676 |
| `paper_hard_holdoutfit` | `periodic` | 20 | 1.2951 | 0.0117 | 0.9475 | 0.0046 | 0.1571 | 1.0000 | 130.25 | 0.0000 |
| `paper_hard_holdoutfit` | `security_risk` | 20 | 1.2770 | 0.0151 | 0.9432 | 0.0034 | 0.0377 | 0.9996 | 129.09 | -0.0182 |
| `paper_hard_holdoutfit` | `security_margin` | 20 | 0.5261 | 0.0189 | 0.9554 | 0.0044 | 0.1570 | 0.9061 | 129.66 | -0.7691 |
| `scenario_stress_holdoutfit` | `rollout_joint` | 20 | 1.2670 | 0.0042 | 1.0000 | 0.0000 | 0.0862 | 1.0000 | 399.04 | 0.2695 |
| `scenario_stress_holdoutfit` | `periodic` | 20 | 0.9975 | 0.0194 | 1.0000 | 0.0000 | 0.1187 | 1.0000 | 163.23 | 0.0000 |
| `scenario_stress_holdoutfit` | `security_risk` | 20 | 0.9801 | 0.0313 | 1.0000 | 0.0000 | 0.0391 | 0.9994 | 158.92 | -0.0175 |
| `scenario_stress_holdoutfit` | `security_margin` | 20 | 0.3228 | 0.0075 | 1.0000 | 0.0000 | 0.1186 | 0.9269 | 157.73 | -0.6747 |

## 4. 主方法配对比较

`rollout_joint` 相对 `periodic` 的配对 seed 比较如下。

| scenario | mean secrecy gain | win seeds | min gain | max gain |
| --- | ---: | ---: | ---: | ---: |
| `paper_base_holdoutfit` | 0.0208 | 17 / 20 | -0.0162 | 0.0657 |
| `paper_hard_holdoutfit` | 0.1676 | 20 / 20 | 0.1058 | 0.2200 |
| `scenario_stress_holdoutfit` | 0.2695 | 20 / 20 | 0.2050 | 0.3735 |

## 5. Holdout 证书覆盖

新的 holdout-fit 配置保留了当前调优后的控制参数。其中 `paper_base_holdoutfit` 已保留 `rollout_horizon=1`、`rollout_force_sync_if_unsafe=false`、`lambda_sync_voi=0.18`、`lambda_sync_request=0.02`、`lambda_sync_low_bandwidth=0.025`、`rollout_resync_cooldown_aoi=2`。

| split | scenario | cover_rate | mean_upper_minus_loss | p90_upper_minus_loss | avg_realized_loss |
| --- | --- | ---: | ---: | ---: | ---: |
| train | all | 1.0000 | 2.4686 | 6.1184 | 0.7842 |
| train | base | 1.0000 | 0.9425 | 1.7860 | 0.2550 |
| train | scenario_hard | 1.0000 | 2.7249 | 7.9230 | 0.8967 |
| train | scenario_stress | 1.0000 | 3.3890 | 11.1485 | 1.0826 |
| validation | all | 0.9081 | 3.6139 | 12.0230 | 0.7151 |
| validation | paper_base | 0.9000 | 2.0055 | 3.7367 | 0.4922 |
| validation | paper_hard | 0.9114 | 3.1171 | 9.4543 | 0.5861 |
| validation | scenario_stress | 0.9113 | 5.2550 | 18.4230 | 0.9951 |

## 6. 结论摘要

1. `rollout_joint` 在三个场景的 secrecy rate 均为第一。
2. `paper_base_holdoutfit` 中，主方法相对 `periodic` 的平均 secrecy 增益为 `+0.0208`，配对胜出 `17/20` seeds，说明 base 场景已从旧主表中的劣势恢复为正增益。
3. `paper_hard_holdoutfit` 中，主方法相对 `periodic` 平均增益为 `+0.1676`，配对胜出 `20/20` seeds，是最稳定的优势场景之一。
4. `scenario_stress_holdoutfit` 中，主方法相对 `periodic` 平均增益为 `+0.2695`，配对胜出 `20/20` seeds，说明压力场景下前瞻联合控制优势最明显。
5. 本次结果支持论文主叙事：调优后的 `rollout_joint` 在简单、困难、压力三类场景中均取得最高 secrecy rate，且场景越困难，相对固定同步策略的优势越大。

## 7. 指标、实验口径与外部可比性

### 7.1 为什么不能和其他论文直接横比绝对数值

本项目的指标名称与 UAV 物理层安全、轨迹优化、数字孪生同步类论文有较多重合，例如 `secrecy rate`、`outage probability`、同步/能耗开销、运行时间等。但是，不同论文通常采用不同的环境规模、信道模型、动作空间、功率范围、Eve 行为、同步机制和安全阈值。因此，本文结果中的绝对数值不应直接与其他论文的表格数值做横向优劣判断。

更合理的比较方式是：

1. **同环境内比较**：在本项目环境下比较 `rollout_joint` 与 `periodic`、`security_risk`、`security_margin`。
2. **同类指标趋势比较**：与其他论文对照 secrecy rate 是否随机动能力、功率、Eve 强度、同步 freshness 变化而呈现类似趋势。
3. **公平复现实验**：若要与外部算法直接比较，应把外部算法复现在本项目同一环境、同一信道、同一动作空间和同一 Eve 模型下。
4. **论文表述口径**：可以说本项目采用了领域通用指标，但不能说本文的 `1.65` secrecy rate 绝对优于另一篇论文的某个数值，除非两者仿真口径一致。

### 7.2 本项目正式实验环境

三个主场景均为二维水平区域 + 固定 UAV 高度的离散时隙仿真。区域大小均为 `500 m × 500 m`，UAV 高度均为 `100 m`，基站位于区域中心附近 `(250, 250)`，每个场景有 3 个地面用户、2 架 UAV 和 1 个 Eve。

| 场景 | episode_length | 用户位置 | UAV 初始位置 | Eve 初始位置 | Eve 速度/最大速度 |
| --- | ---: | --- | --- | --- | --- |
| `paper_base` | 120 | `(100,120)`, `(380,120)`, `(250,400)` | UAV1 `(180,260)`, UAV2 `(320,260)` | `(235,250)` | `(-5,-2)`, max `5.5` |
| `paper_hard` | 140 | `(90,90)`, `(405,100)`, `(260,430)` | UAV1 `(150,250)`, UAV2 `(350,250)` | `(250,240)` | `(-6,-2.5)`, max `6.6` |
| `scenario_stress` | 160 | `(80,110)`, `(410,120)`, `(250,430)` | UAV1 `(140,250)`, UAV2 `(360,250)` | `(255,245)` | `(-7,-3.2)`, max `7.8` |

场景强度从 `paper_base` 到 `scenario_stress` 逐步增加，主要体现在更长 episode、更快 Eve、更高安全门限、更少同步预算和更强不确定性。

### 7.3 信道与 secrecy rate 定义

本项目采用概率 LoS/NLoS 空地信道：

1. 路径损耗基准 `beta0=1.0`。
2. 路径损耗指数分别为 `2.35`、`2.40`、`2.45`。
3. 噪声功率 `1e-6`。
4. 合法链路受到友方干扰泄漏系数 `xi_legit_interference` 影响，三个场景分别为 `0.18`、`0.20`、`0.21`。
5. LoS 概率参数为 `los_a=9.61`、`los_b=0.16`。
6. 额外损耗为 `eta_los_db=1.0`、`eta_nlos_db=18.0`。

单时隙 secrecy rate 定义为：

```text
r_sec = max(r_b - r_e, 0)
```

其中 `r_b` 是合法用户链路速率，`r_e` 是 Eve 窃听链路速率。每个时隙会在 3 个用户中选择当前 secrecy rate 最好的服务用户。

安全中断阈值 `r_min` 随场景增强而升高：

| 场景 | `r_min` |
| --- | ---: |
| `paper_base` | 2.55 |
| `paper_hard` | 2.72 |
| `scenario_stress` | 2.82 |

### 7.4 动作空间与控制变量

每个时隙控制器联合选择 UAV 移动、发射功率、干扰功率和同步动作。

移动动作共有 9 个：

```text
stay, up, down, left, right, up_left, up_right, down_left, down_right
```

每架 UAV 的移动步长为 `10 m`。对角移动会先归一化方向向量，因此实际移动距离仍为 `10 m`。位置会被裁剪在 `500 m × 500 m` 区域内。

功率动作：

```text
p_s_levels = [0.35, 0.50, 0.65, 0.80, 1.00]
p_j_levels = [0.00, 0.25, 0.50, 0.75, 1.00]
```

同步带宽动作：

```text
sync_bandwidth_levels = [0.25, 0.50, 0.75, 1.00]
```

同步具有 1 个时隙延迟，并存在同步失败概率。三个场景同步预算和失败概率如下：

| 场景 | 同步预算 | delay_slots | failure_prob | bandwidth range |
| --- | ---: | ---: | ---: | --- |
| `paper_base` | 28.0 | 1 | 0.05 | `0.25-1.00` |
| `paper_hard` | 22.0 | 1 | 0.06 | `0.25-1.00` |
| `scenario_stress` | 19.0 | 1 | 0.08 | `0.25-1.00` |

### 7.5 Eve 模型与数字孪生模型

Eve 采用 `adaptive_mobile` 模式。它不是简单匀速直线移动，而是在每个时隙根据 UAV 位置和通信功率，在候选移动方向中选择更有利于窃听的位置；随后叠加速度噪声并裁剪到区域内。

数字孪生使用 Kalman-style tracker 维护 Eve 的估计状态。同步成功时，孪生根据带宽相关测量噪声更新；未同步时，孪生执行预测步，AoI 增加。三个场景的孪生不确定性参数如下：

| 场景 | `sigma0` | `kalman_velocity_sigma0` | `process_accel_std` | `measurement_std_at_max_bw` |
| --- | ---: | ---: | ---: | ---: |
| `paper_base` | 3.8 | 1.8 | 0.8 | 1.1 |
| `paper_hard` | 4.0 | 2.0 | 0.9 | 1.2 |
| `scenario_stress` | 4.5 | 2.3 | 1.0 | 1.35 |

孪生质量指标由 AoI、Eve 估计误差和 sigma 加权得到：

```text
twin_badness = 0.35 * normalized_aoi
             + 0.45 * normalized_eve_error
             + 0.20 * normalized_sigma

twin_quality = 1 - clipped(twin_badness)
```

因此，本项目不是只优化通信链路，也显式考虑了数字孪生状态新鲜度和估计可信度。

### 7.6 本项目指标解释

| 指标 | 含义 | 越大/越小 |
| --- | --- | --- |
| `avg_secrecy_rate_mean` | 多 seed 平均真实 secrecy rate，来自 `true_r_sec` 的 episode 平均 | 越大越好 |
| `avg_secrecy_rate_ci95` | `avg_secrecy_rate` 的 95% 置信区间 | 越小越稳定 |
| `outage_prob_mean` | `true_r_sec < r_min` 的时隙比例 | 越小越好 |
| `outage_prob_ci95` | `outage_prob` 的 95% 置信区间 | 越小越稳定 |
| `avg_sync_cost_mean` | 平均同步资源消耗，当前等价于平均同步带宽成本 | 越小越省资源 |
| `sync_request_rate` | 请求同步的时隙比例 | 视预算而定 |
| `avg_sync_applied` | 实际完成同步更新的比例，受 delay 和 failure 影响 | 视任务而定 |
| `avg_pending_syncs` | 平均等待生效的同步请求数 | 越小表示队列压力越小 |
| `avg_twin_quality` | 数字孪生平均质量 | 越大越好 |
| `avg_twin_badness` | 数字孪生平均恶化程度 | 越小越好 |
| `avg_realized_loss` | `max(pred_r_sec - true_r_sec, 0)` 的均值，表示预测过乐观造成的 secrecy loss | 越小越好 |
| `avg_margin_gap` | `pred_r_sec - true_r_sec` 的均值 | 越接近 0 越稳健 |
| `avg_cert_slack` | 证书裕度，即 `predicted_margin - required_margin` | 越大越安全但可能更保守 |
| `certified_safe_rate` | 证书判定安全的时隙比例 | 视保守程度而定 |
| `certificate_violation_prob` | `cert_slack < 0` 的时隙比例 | 越小越好 |
| `certificate_cover_rate` | 证书上界覆盖真实 secrecy loss 的比例 | 越接近目标覆盖率越好 |
| `prediction_violation_prob` | `true_r_sec < pred_r_sec` 的比例，即预测高于真实的频率 | 越小越保守 |
| `success_prob` | `1 - outage_prob` | 越大越好 |
| `runtime_per_slot_ms` | 平均每时隙决策时间 | 越小越快 |
| `secrecy_gain_vs_periodic` | 相对 `periodic` 的 secrecy rate 差值 | 越大越好 |
| `outage_gain_vs_periodic` | `periodic_outage - method_outage`，相对 `periodic` 的 outage 降低量 | 越大越好 |

### 7.7 与其他论文指标的关系

与 UAV 物理层安全和轨迹优化论文相比，本项目的 `secrecy rate`、`outage probability`、功率/同步成本、runtime 属于可理解的同类指标；这些指标可以用于说明问题类型和性能趋势。

与数字孪生、AoI/AoS、状态同步类论文相比，本项目的 `aoi`、`avg_twin_quality`、`avg_twin_badness` 与 freshness/synchronization 类指标同源，但定义更贴合本项目：它不仅看多久没同步，也看 Eve 位置估计误差和 Kalman 不确定性。

本项目较有区分度的指标是 `certificate_cover_rate`、`avg_cert_slack`、`certificate_violation_prob` 和 `avg_realized_loss`。这些指标服务于本文的经验安全证书叙事，用来说明数字孪生误差下的 secrecy loss 是否被保守上界覆盖。普通 UAV 安全通信论文通常不会报告这一组 conformal certificate 指标。

因此，本文与外部工作的关系可以写成：

1. **共享领域通用指标**：secrecy rate、outage probability、资源成本、运行时间。
2. **扩展数字孪生指标**：AoI/freshness 进一步扩展为 twin quality/badness。
3. **新增证书可靠性指标**：用 certificate cover/slack/violation 描述不确定 Eve 估计下的安全保证。
4. **不直接横比绝对值**：不同环境和模型下的绝对 secrecy rate/outage 不具备严格可比性。
