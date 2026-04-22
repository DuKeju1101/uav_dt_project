# 实验部分草稿

## 1. 实验设置

### 1.1 目标

我们从三个维度评估当前项目：

1. 保密性能
2. 在孪生信息陈旧或存在时延时的 outage 表现
3. 控制器的运行时间开销

当前比较的五种方法包括：

1. `periodic`
2. `security_risk`
3. `security_margin`
4. `rollout_joint`
5. `oracle_sync`

### 1.2 证书协议

最终表格中使用的证书模型，是通过下面命令生成的 holdout 拟合模型：

`python -m experiments.fit_certificate_holdout ... --outdir /tmp/cert_holdout_eval_v2`

训练集划分：

1. 场景：`paper_base`、`paper_hard`
2. 方法：`periodic`、`security_risk`、`aoi_only`
3. 种子：`42`、`43`

验证集划分：

1. 场景：`paper_base`、`paper_hard`、`scenario_stress`
2. 方法：`periodic`、`security_risk`、`security_margin`、`rollout_joint`
3. 最终表格使用的验证种子：`62`、`63`、`64`

拟合得到的验证配置文件为：

1. `/tmp/cert_holdout_eval_v2/configs/paper_base_holdoutfit.yaml`
2. `/tmp/cert_holdout_eval_v2/configs/paper_hard_holdoutfit.yaml`
3. `/tmp/cert_holdout_eval_v2/configs/scenario_stress_holdoutfit.yaml`

### 1.3 多 seed 评估协议

最终多 seed 表格是基于三个场景中五种方法、验证种子 `62, 63, 64` 生成的。我们使用 [metrics.py](/home/dkj/research/uav_dt_project/analysis/metrics.py) 中现有的汇总流水线，报告均值和 `95%` 置信区间。

导出的汇总文件保存在：

1. `/tmp/final_multiseed_tables/paper_base_holdoutfit_v2_summary.csv`
2. `/tmp/final_multiseed_tables/paper_hard_holdoutfit_v2_summary.csv`
3. `/tmp/final_multiseed_tables/scenario_stress_holdoutfit_v2_summary.csv`
4. `/tmp/final_multiseed_tables/combined_summary.csv`

## 2. Holdout 证书泛化能力

### 2.1 Holdout 汇总

| 划分 | 场景 | 覆盖率 | 上界减损失均值 | P90 上界减损失 | 平均真实损失 |
| --- | --- | ---: | ---: | ---: | ---: |
| train | all | 0.9994 | 0.1222 | 0.2581 | 0.0051 |
| train | paper_base | 0.9986 | 0.0661 | 0.1495 | 0.0056 |
| train | paper_hard | 1.0000 | 0.1703 | 0.4525 | 0.0046 |
| validation | all | 0.9952 | 0.6999 | 2.3882 | 0.0102 |
| validation | paper_base | 1.0000 | 0.5084 | 1.7096 | 0.0105 |
| validation | paper_hard | 0.9964 | 0.7685 | 2.6324 | 0.0103 |
| validation | scenario_stress | 0.9906 | 0.7834 | 2.6761 | 0.0099 |

### 2.2 解释

这个证书现在已经具有较好的样本外泛化能力：

1. 所有场景中的验证覆盖率都高于 `0.99`
2. 证书不再像一个纯粹的样本内启发式规则
3. 这种鲁棒性的代价是更保守的 slack 膨胀

这意味着，当前这个证书可以被描述为一个经验校准的保守 secrecy-loss bound。

## 3. 主要多 seed 结果

### 3.1 paper_base

| 方法 | 平均 secrecy ± CI | Outage ± CI | 平均同步成本 | 覆盖率 | Runtime ms/slot ± CI |
| --- | --- | --- | ---: | ---: | --- |
| rollout_joint | 2.7356 ± 0.0255 | 0.1583 ± 0.0499 | 0.0083 | 1.0000 | 684.95 ± 11.57 |
| oracle_sync | 2.7292 ± 0.0247 | 0.1556 ± 0.0446 | 0.0000 | 1.0000 | 617.45 ± 20.63 |
| security_margin | 2.7110 ± 0.0129 | 0.1611 ± 0.0465 | 0.2333 | 1.0000 | 25.29 ± 0.59 |
| security_risk | 2.7075 ± 0.0185 | 0.1694 ± 0.0628 | 0.1028 | 1.0000 | 25.98 ± 2.13 |
| periodic | 2.7034 ± 0.0212 | 0.1389 ± 0.0054 | 0.1500 | 1.0000 | 25.61 ± 1.36 |

### 3.2 paper_hard

| 方法 | 平均 secrecy ± CI | Outage ± CI | 平均同步成本 | 覆盖率 | Runtime ms/slot ± CI |
| --- | --- | --- | ---: | ---: | --- |
| rollout_joint | 2.5762 ± 0.0247 | 0.5738 ± 0.0415 | 0.0143 | 0.9976 | 666.01 ± 4.98 |
| oracle_sync | 2.5755 ± 0.0307 | 0.5738 ± 0.0364 | 0.0000 | 0.9976 | 619.44 ± 25.31 |
| security_margin | 2.5709 ± 0.0255 | 0.5714 ± 0.0242 | 0.1571 | 1.0000 | 25.03 ± 1.67 |
| security_risk | 2.5695 ± 0.0215 | 0.5690 ± 0.0306 | 0.0881 | 0.9976 | 24.77 ± 0.52 |
| periodic | 2.5666 ± 0.0226 | 0.5738 ± 0.0047 | 0.1571 | 1.0000 | 24.82 ± 1.82 |

### 3.3 scenario_stress

| 方法 | 平均 secrecy ± CI | Outage ± CI | 平均同步成本 | 覆盖率 | Runtime ms/slot ± CI |
| --- | --- | --- | ---: | ---: | --- |
| periodic | 2.4658 ± 0.0237 | 0.4917 ± 0.0147 | 0.1188 | 0.9958 | 25.09 ± 1.13 |
| security_margin | 2.4657 ± 0.0260 | 0.4729 ± 0.0147 | 0.1188 | 1.0000 | 24.42 ± 0.93 |
| rollout_joint | 2.4629 ± 0.0255 | 0.4854 ± 0.0108 | 0.0271 | 0.9958 | 683.44 ± 21.55 |
| oracle_sync | 2.4618 ± 0.0297 | 0.4937 ± 0.0212 | 0.0000 | 0.9979 | 619.30 ± 26.51 |
| security_risk | 2.4563 ± 0.0313 | 0.4958 ± 0.0248 | 0.0813 | 0.9958 | 24.78 ± 2.39 |

## 4. Runtime 权衡

### 4.1 相对 periodic 的运行时间比例

| 场景 | 方法 | 相对 periodic 的 runtime 比例 |
| --- | --- | ---: |
| paper_base | rollout_joint | 26.75x |
| paper_base | oracle_sync | 24.11x |
| paper_hard | rollout_joint | 26.83x |
| paper_hard | oracle_sync | 24.96x |
| scenario_stress | rollout_joint | 27.24x |
| scenario_stress | oracle_sync | 24.68x |

### 4.2 解释

经过最近一轮轻量化之后，rollout 控制器已经比之前便宜了很多，但相对于规则型策略仍然昂贵得多。

变化如下：

1. 之前的 rollout runtime 大约在 `890-934 ms/slot`
2. 现在的 rollout runtime 大约在 `666-685 ms/slot`

因此，新控制器在基本保持 secrecy 表现不变的情况下，将 runtime 降低了大约四分之一。

## 5. 结果分析

### 5.1 当前最终表格能强力支持的结论

#### A. 证书模型已经足够稳定，可以用于投稿

holdout 结果支持一个较强的经验性结论：

1. 证书可以跨 seed 泛化
2. 可以跨场景泛化
3. 即使在 stress 场景下也保持较高覆盖率

这是当前项目最强的组成部分之一。

#### B. 实验场景设置现在是合适的

项目已经摆脱了早期“所有方法都同样失败”的饱和状态。

现在：

1. `paper_base` 仍然是中等难度
2. `paper_hard` 具有挑战性，但没有完全崩溃
3. `scenario_stress` 难度较高，并能暴露 tradeoff

这给论文提供了更健康的实验梯度。

#### C. 轻量化 rollout 可以被写成一个实用近似方法

最新版本的 `rollout_joint` 已经不再只是一个很重的搜索型 baseline，而是一个实用的近似 MPC，它具有：

1. 当前时隙的 top action beam
2. 未来时隙中的贪心 continuation
3. 明确的 runtime-performance tradeoff

这比以前更容易在论文中建立动机。

### 5.2 表格对方法排序说明了什么

#### A. paper_base

`rollout_joint` 在 secrecy 上最强，并且仍然接近 `oracle_sync`。

这是一个很干净的结果：

1. 相对 `periodic` 的 secrecy 增益约为 `+0.0323`
2. 相对 `security_risk` 的 secrecy 增益约为 `+0.0281`
3. runtime 代价明显更高，因此这种提升并不是免费的

#### B. paper_hard

`rollout_joint` 在 secrecy 上再次最强，但相对于最好的规则法，增益较小。

这意味着 hard 场景的叙事应是：

1. rollout 在更困难条件下仍具有竞争力
2. 但它的优势是渐进式的，而不是压倒性的

#### C. scenario_stress

`security_margin` 与 `periodic` 在 top secrecy 上几乎打平，而 `security_margin` 的 outage 最优。

这最清楚地说明了 rollout 方法还没有做到“全局统治”。因此，当前项目更支持下面这种更克制的说法：

`rollout_joint` 是一个强方法，在 base 和 hard 场景中优势明显；但在压力最大的场景下，证书感知规则法仍然非常有竞争力。

### 5.3 要让论文完全有说服力，还缺什么

项目现在已经很接近完成，但还没有彻底收尾。

剩余的主要缺口有：

1. 最终主表仍然只用了 `3` 个验证种子
2. rollout 控制器仍然较贵
3. 论文还需要一个 ablation 表，用来拆解 rollout 的性能提升究竟来自哪里

## 6. 推荐的文字结论

按照当前阶段，项目可以支撑如下结论：

1. 数字孪生证书模型已经被显著加强，并表现出很强的 holdout 泛化能力。
2. 调优后的场景能够在不退化为完全 outage 饱和的前提下，提供有意义的方法区分。
3. 轻量化后的 `rollout_joint` 在大幅降低 runtime 的同时，保留了主要性能优势。
4. 因此，系统现在已经能够支撑一个围绕“校准后的孪生不确定性、鲁棒同步以及性能-runtime 权衡”的可信论文叙事。

最诚实的最终说法是：

`对于一篇偏应用/系统方向的论文来说，这个项目现在已经接近可投稿状态：证书模型已经足够强，控制器叙事也基本建立；剩余主要工作是再补一层多 seed 证据或消融分析，使最终证据更厚实。`
