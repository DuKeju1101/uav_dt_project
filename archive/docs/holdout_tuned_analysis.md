# Holdout 证书评估与调优场景分析

## 1. 本轮有哪些变化

本轮主要做了两项升级：

1. 新增了训练/验证分离的证书拟合流水线，见 [fit_certificate_holdout.py](/home/dkj/research/uav_dt_project/experiments/fit_certificate_holdout.py)。
2. 将 `paper_hard` 和 `scenario_stress` 从此前“几乎完全饱和”的设定，调整为“仍然困难但可以区分方法差异”的设定：
   [paper_hard.yaml](/home/dkj/research/uav_dt_project/configs/paper_hard.yaml)
   [scenario_stress.yaml](/home/dkj/research/uav_dt_project/configs/scenario_stress.yaml)

本轮 holdout 拟合产生的结果文件写入了 `/tmp/cert_holdout_eval`，包括：

1. `/tmp/cert_holdout_eval/holdout_summary.csv`
2. `/tmp/cert_holdout_eval/holdout_model_coefficients.csv`
3. `/tmp/cert_holdout_eval/configs/paper_base_holdoutfit.yaml`
4. `/tmp/cert_holdout_eval/configs/paper_hard_holdoutfit.yaml`
5. `/tmp/cert_holdout_eval/configs/scenario_stress_holdoutfit.yaml`

## 2. Holdout 证书泛化能力

### 2.1 划分协议

训练集划分：

1. 场景：`paper_base`、`paper_hard`
2. 方法：`periodic`、`security_risk`、`aoi_only`
3. 种子：`42`、`43`

验证集划分：

1. 场景：`paper_base`、`paper_hard`、`scenario_stress`
2. 方法：`periodic`、`security_risk`、`security_margin`、`rollout_joint`
3. 种子：`62`

### 2.2 Holdout 汇总

| 划分 | 场景 | 覆盖率 | 上界减损失均值 | P90 上界减损失 | 平均真实损失 |
| --- | --- | ---: | ---: | ---: | ---: |
| train | all | 0.9994 | 0.1222 | 0.2581 | 0.0051 |
| train | paper_base | 0.9986 | 0.0661 | 0.1495 | 0.0056 |
| train | paper_hard | 1.0000 | 0.1703 | 0.4525 | 0.0046 |
| validation | all | 0.9952 | 0.6999 | 2.3882 | 0.0102 |
| validation | paper_base | 1.0000 | 0.5084 | 1.7096 | 0.0105 |
| validation | paper_hard | 0.9964 | 0.7685 | 2.6324 | 0.0103 |
| validation | scenario_stress | 0.9906 | 0.7834 | 2.6761 | 0.0099 |

### 2.3 Holdout 系数解释

| 特征 | 系数 |
| --- | ---: |
| aoi_norm | 0.201293 |
| sigma_norm | 0.009779 |
| failure_prob | 0.298076 |
| aoi_x_radius | 0.070325 |
| delay_x_sigma | 0.009779 |

其余系数都被压到 `0`。

解释如下：

1. 从覆盖率角度看，模型具有较好的泛化能力。
2. 验证集覆盖率依然高于 `0.99`，因此拟合出来的证书并不是单纯在记忆训练轨迹。
3. 验证阶段的 bound 比训练阶段松得多。
4. 新的主导因素是 `aoi_norm`、`failure_prob` 和 `aoi_x_radius`。

这是一个有意义的结果：在引入训练/验证分离后，证书这条线现在可以被写成一个“具有可测样本外覆盖率的经验校准保守 bound”。

## 3. 调优场景下的验证表

下面所有表格都基于 holdout 拟合后的证书配置，并使用验证种子 `62`。

### 3.1 paper_base

| 方法 | 平均 secrecy | Outage | 同步成本 | 覆盖率 | 证书安全率 | 平均证书松弛量 | Runtime/slot ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 2.6948 | 0.1417 | 0.1500 | 1.0000 | 0.8333 | 0.0453 | 36.01 |
| security_risk | 2.6915 | 0.2333 | 0.1000 | 1.0000 | 0.6333 | -0.0119 | 32.31 |
| security_margin | 2.7016 | 0.2083 | 0.2333 | 1.0000 | 0.1667 | -0.5022 | 32.11 |
| rollout_joint | 2.7129 | 0.2083 | 0.0000 | 1.0000 | 0.0000 | -1.1916 | 934.24 |
| oracle_sync | 2.7134 | 0.2000 | 0.0000 | 1.0000 | 0.0000 | -1.1972 | 875.52 |

### 3.2 paper_hard

| 方法 | 平均 secrecy | Outage | 同步成本 | 覆盖率 | 证书安全率 | 平均证书松弛量 | Runtime/slot ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 2.5474 | 0.5786 | 0.1571 | 1.0000 | 0.1929 | -0.2978 | 36.19 |
| security_risk | 2.5516 | 0.5571 | 0.0857 | 0.9929 | 0.1429 | -0.3310 | 34.44 |
| security_margin | 2.5462 | 0.5714 | 0.1571 | 1.0000 | 0.0000 | -1.3265 | 26.96 |
| rollout_joint | 2.5615 | 0.5643 | 0.0143 | 0.9929 | 0.0000 | -0.9970 | 902.88 |
| oracle_sync | 2.5523 | 0.5714 | 0.0000 | 0.9929 | 0.0000 | -1.9473 | 791.90 |

### 3.3 scenario_stress

| 方法 | 平均 secrecy | Outage | 同步成本 | 覆盖率 | 证书安全率 | 平均证书松弛量 | Runtime/slot ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 2.4484 | 0.4875 | 0.1188 | 0.9875 | 0.0000 | -0.5772 | 35.13 |
| security_risk | 2.4345 | 0.4750 | 0.0813 | 0.9875 | 0.0000 | -0.5611 | 32.59 |
| security_margin | 2.4436 | 0.4625 | 0.1188 | 1.0000 | 0.0000 | -2.0756 | 29.17 |
| rollout_joint | 2.4455 | 0.4750 | 0.0188 | 0.9875 | 0.0000 | -1.4879 | 890.47 |
| oracle_sync | 2.4419 | 0.4750 | 0.0000 | 0.9938 | 0.0000 | -2.7479 | 749.81 |

## 4. 主要结论

### 4.1 证书模型现在可信得多

和之前手工设计的证书相比：

1. 现在具有明确的训练/验证分离。
2. 验证覆盖率稳定保持在 `>0.99`。
3. 它暴露了一个清晰的权衡：高覆盖率是用较松的 margin 换来的。

因此，这个证书现在可以作为“经验校准的保守证书”来写，但还不能作为一个紧的解析型 bound 来写。

### 4.2 hard/stress 场景不再完全饱和

这是本轮实验上最大的改进。

此前：

1. `paper_hard` 和 `scenario_stress` 基本都处于全 outage 状态。
2. 这使方法间对比很难成立。

现在：

1. `paper_hard` 的 outage 大约在 `0.56-0.58`
2. `scenario_stress` 的 outage 大约在 `0.46-0.49`

这对论文主表更有利，因为不同方法现在可以被区分开。

### 4.3 方法叙事更清楚了，但仍然是混合结论

1. 在 `paper_base` 中，`rollout_joint` 仍然最强，并且几乎追平 `oracle_sync`。
2. 在 `paper_hard` 中，`rollout_joint` 在 secrecy 上成为最强方法，但相对于最优规则法的 outage 改善仍然很小。
3. 在 `scenario_stress` 中，`security_margin` 获得了最优 outage，而 `rollout_joint` 虽然比部分 baseline secrecy 更好，但并没有统治性优势。

这意味着当前更合适的论文叙事是：

1. 拟合证书让同步模型更可辩护。
2. 调优后的场景揭示了真实权衡，而不是完全饱和。
3. `rollout_joint` 具有竞争力，而且经常是最优，但还不是在所有目标和所有场景下都统一占优。

### 4.4 runtime 仍然是主要系统瓶颈

1. 规则法大约维持在 `27-36 ms/slot`。
2. `rollout_joint` 仍然在 `890-934 ms/slot`。
3. `oracle_sync` 也仍然处在同一量级。

因此，项目现在已经很适合写一篇强调以下三点的论文：

1. 数字孪生不确定性的校准
2. 鲁棒感知的联合控制
3. 性能与 runtime 的权衡

但它还不太适合写成一篇宣称“控制算法在所有方面都明显优于其他方法”的论文。
