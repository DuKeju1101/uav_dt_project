# 20-Seed 最终主表结果（2026-04-14）

## 1. 说明

本轮将最终主表扩展到 `20` 个验证 seed，统一使用：

1. 场景：`paper_base`、`paper_hard`、`scenario_stress`
2. 方法：`periodic`、`security_risk`、`security_margin`、`rollout_joint`
3. 验证 seed：`62-81`

对应结果文件：

1. 合并主表：[final20_main_table.csv](../results/final20_combined/final20_main_table.csv)
2. Markdown 主表：[final20_main_table.md](../results/final20_combined/final20_main_table.md)
3. 分场景结果：
   - [final20_paper_base/main_table.csv](../results/final20_paper_base/main_table.csv)
   - [final20_paper_hard/main_table.csv](../results/final20_paper_hard/main_table.csv)
   - [final20_scenario_stress/main_table.csv](../results/final20_scenario_stress/main_table.csv)

## 2. 20-seed 最终主表

### 2.1 paper_base

| 方法 | runs | 平均 secrecy | CI95 | outage | outage CI95 | 平均同步成本 | 覆盖率 | ms/slot | secrecy gain vs periodic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rollout_joint | 20 | 2.7309 | 0.0065 | 0.1600 | 0.0137 | 0.0421 | 0.9350 | 235.34 | +0.0287 |
| security_margin | 20 | 2.7116 | 0.0050 | 0.1758 | 0.0155 | 0.2333 | 0.9575 | 8.58 | +0.0094 |
| security_risk | 20 | 2.7032 | 0.0058 | 0.1717 | 0.0176 | 0.1021 | 0.9483 | 8.97 | +0.0010 |
| periodic | 20 | 2.7022 | 0.0054 | 0.1717 | 0.0178 | 0.1500 | 0.8975 | 9.17 | 0.0000 |

### 2.2 paper_hard

| 方法 | runs | 平均 secrecy | CI95 | outage | outage CI95 | 平均同步成本 | 覆盖率 | ms/slot | secrecy gain vs periodic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rollout_joint | 20 | 2.5769 | 0.0048 | 0.5654 | 0.0088 | 0.0511 | 0.9339 | 232.32 | +0.0064 |
| security_margin | 20 | 2.5722 | 0.0048 | 0.5682 | 0.0094 | 0.1571 | 0.9739 | 8.63 | +0.0018 |
| security_risk | 20 | 2.5714 | 0.0059 | 0.5739 | 0.0144 | 0.0882 | 0.9500 | 8.83 | +0.0010 |
| periodic | 20 | 2.5705 | 0.0058 | 0.5764 | 0.0119 | 0.1571 | 0.8896 | 8.90 | 0.0000 |

### 2.3 scenario_stress

| 方法 | runs | 平均 secrecy | CI95 | outage | outage CI95 | 平均同步成本 | 覆盖率 | ms/slot | secrecy gain vs periodic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rollout_joint | 20 | 2.4647 | 0.0054 | 0.4813 | 0.0083 | 0.0703 | 0.9316 | 228.77 | +0.0017 |
| periodic | 20 | 2.4630 | 0.0048 | 0.4800 | 0.0093 | 0.1188 | 0.9169 | 8.72 | 0.0000 |
| security_risk | 20 | 2.4611 | 0.0056 | 0.4834 | 0.0092 | 0.0794 | 0.9400 | 8.32 | -0.0019 |
| security_margin | 20 | 2.4603 | 0.0050 | 0.4759 | 0.0071 | 0.1188 | 0.9678 | 8.47 | -0.0027 |

## 3. 结果解读

### 3.1 主表已经足够厚了吗

就“四区应用类论文可投稿性”而言，这版主表已经明显比 `3-seed` 和 `5-seed` 版本更扎实。

原因：

1. 每个场景都已经有 `20` 个验证 seed。
2. 各核心指标的 `95% CI` 都明显收窄。
3. 现在可以更有把握地区分“稳定趋势”和“少量 seed 波动”。

结论：

`从证据厚度角度看，20-seed 主表已经足以支撑论文投稿。`

### 3.2 把 seed 增加到 20 后，结论有没有变

结论没有根本改变，但变得更清楚了。

#### paper_base

1. `rollout_joint` 仍然是最强 secrecy 方法。
2. 相比 `periodic` 的 secrecy 增益稳定在 `+0.0287`。
3. 同步成本依然明显更低，但 runtime 仍然高很多。

#### paper_hard

1. `rollout_joint` 仍然保持最优 secrecy。
2. 相对 `periodic` 的增益只有 `+0.0064`，说明优势是存在的，但不算大。
3. outage 也优于 `periodic`，但优势同样比较有限。

#### scenario_stress

1. `rollout_joint` 的平均 secrecy 现在略高于所有规则法。
2. 但它的 outage 不是最优，`security_margin` 的 outage 仍然更低。
3. 这说明 stress 场景下，`rollout_joint` 的核心问题不是“完全没优势”，而是“优势不够硬、且不是多指标统一最优”。

### 3.3 当前最稳妥的论文表述

20-seed 主表支持如下更稳妥的结论：

1. `rollout_joint` 在 `paper_base` 和 `paper_hard` 中稳定取得最高平均 secrecy。
2. 在 `scenario_stress` 中，`rollout_joint` 也能取得最高平均 secrecy，但优势已经缩小到非常接近规则法。
3. `security_margin` 在高压场景下仍然更擅长压低 outage。
4. 因此，项目更适合写成“不同方法在性能、同步成本与 runtime 之间具有不同优势”的系统论文，而不是“单一方法全面统治”的算法论文。

## 4. 对可发论文性的影响

### 4.1 已经被解决的问题

此前文档里提到的这条问题：

> 当前最成熟主表只有 `3` 个验证 seed。对低区期刊来说不算致命，但仍偏薄。

现在可以认为已经**解决**。

原因：

1. 主表已经扩展到 `20` 个验证 seed。
2. 结果稳定性和置信区间都已经达到可投稿水平。
3. 审稿人如果质疑“是不是 seed 太少”，现在这条质疑会明显弱很多。

### 4.2 还没有完全解决的问题

尽管 20-seed 主表已经足够厚，但有一个核心问题仍然存在：

`rollout_joint` 还没有形成跨所有场景、所有指标的稳定统治。`

尤其在 `scenario_stress`：

1. 它在 secrecy 上只领先很小一点。
2. 它的 outage 仍不如 `security_margin`。
3. 它的 runtime 仍然远高于规则法。

所以，如果你现在投稿，最合适的写法仍然是：

`提出一种在多数场景下具有较强竞争力的轻量前瞻控制方法，并系统分析其与规则型同步策略之间的性能-成本权衡。`

## 5. 最终判断

20-seed 主表补完之后，可以把结论更新为：

> 这个项目现在已经具备四区应用类论文的主表证据厚度。  
> 如果当前目标只是满足“可发论文性”，那么从验证 seed 数量这件事上看，已经达标。  
> 剩余主要问题不再是“证据太薄”，而是“主方法在最高压力场景下的优势还不够硬”。 

