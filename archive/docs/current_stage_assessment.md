# Rollout 轻量化后的当前阶段评估

## 1. 本轮工作的范围

本轮主要聚焦两个目标：

1. 进一步轻量化 `rollout_joint` 控制器，使其 runtime 更容易在论文中解释。
2. 使用新的轻量化控制器、holdout 拟合证书模型，以及调优后的 `paper_base / paper_hard / scenario_stress` 场景，重新评估当前项目。

控制器改动实现于 [rollout_joint.py](/home/dkj/research/uav_dt_project/policies/rollout_joint.py)。关键变化在于，控制器不再在每个深度都展开递归搜索树，而是改用：

1. 根节点仅保留得分最高的一组动作候选
2. 未来步骤使用贪心 tail rollout
3. 缓存动作模板
4. 复用即时候选动作得分

这使得控制器更像一个容易解释的近似 MPC：

1. 第一步先评估若干强候选动作
2. 后续步骤不再指数分支，而是沿着局部最优延续

## 2. 本轮执行的实验

### 2.1 轻量化后的 runtime sanity check

执行命令：

```bash
python - <<'PY'
import pandas as pd
from experiments.common import load_config, run_single_episode
for cfg_path in ['configs/paper_base.yaml','configs/paper_hard.yaml','configs/scenario_stress.yaml']:
    cfg=load_config(cfg_path)
    rows=[]
    for m in ['periodic','rollout_joint','oracle_sync']:
        _, s = run_single_episode(cfg, seed=42, method=m)
        rows.append(s)
    print(pd.DataFrame(rows)[['method','avg_secrecy_rate','outage_prob','runtime_per_slot_ms','runtime_sec']].to_csv(index=False))
PY
```

### 2.2 Holdout 证书拟合与评估

执行命令：

```bash
python -m experiments.fit_certificate_holdout \
  --train-configs configs/paper_base.yaml configs/paper_hard.yaml \
  --eval-configs configs/paper_base.yaml configs/paper_hard.yaml configs/scenario_stress.yaml \
  --outdir /tmp/cert_holdout_eval_v2 \
  --train-methods periodic security_risk aoi_only \
  --eval-methods periodic security_risk security_margin rollout_joint \
  --train-seeds 2 \
  --eval-seeds 1 \
  --eval-seed-start 20 \
  --residual-quantile 0.95 \
  --safety-scale 1.1
```

### 2.3 使用新 holdout 拟合证书生成验证表

执行：

1. `/tmp/cert_holdout_eval_v2/configs/paper_base_holdoutfit.yaml`，验证种子 `62`
2. `/tmp/cert_holdout_eval_v2/configs/paper_hard_holdoutfit.yaml`，验证种子 `62`
3. `/tmp/cert_holdout_eval_v2/configs/scenario_stress_holdoutfit.yaml`，验证种子 `62`

## 3. 轻量化对 runtime 的影响

最公平的对比对象，是 [holdout_tuned_analysis.md](/home/dkj/research/uav_dt_project/docs/holdout_tuned_analysis.md) 里之前那组基于 holdout 的验证表，因为它们使用的是同一组场景家族和同一个验证种子。

### 3.1 rollout 轻量化前后 runtime 对比

| 场景 | 旧 rollout ms/slot | 新 rollout ms/slot | 降幅 |
| --- | ---: | ---: | ---: |
| paper_base | 934.24 | 690.48 | 26.1% |
| paper_hard | 902.88 | 679.04 | 24.8% |
| scenario_stress | 890.47 | 669.94 | 24.8% |

### 3.2 轻量化后的 rollout 性能

| 场景 | 平均 secrecy | Outage | Runtime ms/slot |
| --- | ---: | ---: | ---: |
| paper_base | 2.7129 | 0.2083 | 690.48 |
| paper_hard | 2.5615 | 0.5643 | 679.04 |
| scenario_stress | 2.4455 | 0.4750 | 669.94 |

解释：

1. 三个论文场景中的 runtime 都下降了大约四分之一。
2. 相比之前调优后的 holdout 表，secrecy 和 outage 数值基本没有明显变化。
3. 因此，这次轻量化改善了系统叙事，同时没有显著损害控制器质量。

这是一个重要里程碑。rollout 控制器仍然较贵，但已经不再是此前接近 `1 s/slot` 的量级。

## 4. Holdout 证书评估

### 4.1 Holdout 汇总

| 划分 | 场景 | 覆盖率 | 上界减损失均值 | P90 上界减损失 | 平均真实损失 |
| --- | --- | ---: | ---: | ---: | ---: |
| train | all | 0.9994 | 0.1222 | 0.2581 | 0.0051 |
| train | paper_base | 0.9986 | 0.0661 | 0.1495 | 0.0056 |
| train | paper_hard | 1.0000 | 0.1703 | 0.4525 | 0.0046 |
| validation | all | 0.9952 | 0.6999 | 2.3882 | 0.0102 |
| validation | paper_base | 1.0000 | 0.5084 | 1.7096 | 0.0105 |
| validation | paper_hard | 0.9964 | 0.7685 | 2.6324 | 0.0103 |
| validation | scenario_stress | 0.9906 | 0.7834 | 2.6761 | 0.0099 |

### 4.2 Holdout 模型系数

| 特征 | 系数 |
| --- | ---: |
| aoi_norm | 0.201293 |
| sigma_norm | 0.009779 |
| failure_prob | 0.298076 |
| aoi_x_radius | 0.070325 |
| delay_x_sigma | 0.009779 |

其余所有系数都被压到 `0`。

### 4.3 对证书的评估

证书模型现在已经成为项目里最强的部分之一。

原因是：

1. 它具有明确的训练/验证划分。
2. 即使在 `scenario_stress` 上，验证覆盖率仍保持在 `0.99` 以上。
3. 拟合结构是可解释的。

这些系数传达的信息是：

1. `aoi_norm` 较大，说明孪生老化直接重要。
2. `failure_prob` 较大，说明同步不可靠性不是一个微小修正项，而是结构性因素。
3. `aoi_x_radius` 仍然重要，这支持了项目核心的耦合假设。

但当前叙事的限制仍然包括：

1. 该 bound 是保守的，而不是紧的。
2. 验证阶段 slack 膨胀较明显。
3. 该模型仍然是经验型的，而不是解析型的。

因此，现在可以将证书写成：

`empirically calibrated conservative secrecy-loss certificate`

这比早期手工设计的 margin 规则强得多。

## 5. 当前验证表

下面所有结果都使用写入 `/tmp/cert_holdout_eval_v2/configs/` 的新 holdout 拟合证书配置，以及验证种子 `62`。

### 5.1 paper_base

| 方法 | 平均 secrecy | Outage | 同步成本 | 覆盖率 | 证书安全率 | 平均证书松弛量 | Runtime ms/slot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 2.6948 | 0.1417 | 0.1500 | 1.0000 | 0.8333 | 0.0453 | 27.65 |
| security_risk | 2.6915 | 0.2333 | 0.1000 | 1.0000 | 0.6333 | -0.0119 | 27.38 |
| security_margin | 2.7016 | 0.2083 | 0.2333 | 1.0000 | 0.1667 | -0.5022 | 25.97 |
| rollout_joint | 2.7129 | 0.2083 | 0.0000 | 1.0000 | 0.0000 | -1.1916 | 690.48 |
| oracle_sync | 2.7134 | 0.2000 | 0.0000 | 1.0000 | 0.0000 | -1.1972 | 660.29 |

### 5.2 paper_hard

| 方法 | 平均 secrecy | Outage | 同步成本 | 覆盖率 | 证书安全率 | 平均证书松弛量 | Runtime ms/slot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 2.5474 | 0.5786 | 0.1571 | 1.0000 | 0.1929 | -0.2978 | 25.78 |
| security_risk | 2.5516 | 0.5571 | 0.0857 | 0.9929 | 0.1429 | -0.3310 | 23.67 |
| security_margin | 2.5462 | 0.5714 | 0.1571 | 1.0000 | 0.0000 | -1.3265 | 27.13 |
| rollout_joint | 2.5615 | 0.5643 | 0.0143 | 0.9929 | 0.0000 | -0.9970 | 679.04 |
| oracle_sync | 2.5523 | 0.5714 | 0.0000 | 0.9929 | 0.0000 | -1.9473 | 609.72 |

### 5.3 scenario_stress

| 方法 | 平均 secrecy | Outage | 同步成本 | 覆盖率 | 证书安全率 | 平均证书松弛量 | Runtime ms/slot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 2.4484 | 0.4875 | 0.1188 | 0.9875 | 0.0000 | -0.5772 | 30.22 |
| security_risk | 2.4345 | 0.4750 | 0.0813 | 0.9875 | 0.0000 | -0.5611 | 27.41 |
| security_margin | 2.4436 | 0.4625 | 0.1188 | 1.0000 | 0.0000 | -2.0756 | 21.24 |
| rollout_joint | 2.4455 | 0.4750 | 0.0188 | 0.9875 | 0.0000 | -1.4879 | 669.94 |
| oracle_sync | 2.4419 | 0.4750 | 0.0000 | 0.9938 | 0.0000 | -2.7479 | 619.89 |

## 6. 对当前项目的详细评估

### 6.1 现在真正强的地方

#### A. 问题定义是连贯的

项目现在清楚地在研究：

1. 数字孪生老化带来的不确定性
2. 预算受限的同步决策
3. 保密感知的联合控制
4. 性能与 runtime 的权衡

这已经是一个真实的论文问题，而不仅仅是一个仿真练习。

#### B. 证书这条线现在是可辩护的

证书部分此前是项目最薄弱的一环，这一点现在已经不成立了。

现在它具备：

1. 拟合结构
2. 可解释的主导项
3. 明确的 holdout 验证
4. 很强的覆盖率

这已经足够支撑一条关于鲁棒校准的论文叙事。

#### C. 实验场景现在是可用的

`paper_hard` 和 `scenario_stress` 已经不再完全饱和。这一点非常重要，因为论文主表需要非平凡的 tradeoff。

当前范围大致为：

1. `paper_hard` 的 outage 大约在 `0.56-0.58`
2. `scenario_stress` 的 outage 大约在 `0.46-0.49`

这已经足够难，具有意义，但又没有难到所有方法一起崩溃。

#### D. rollout 方法现在更适合发表

轻量化之后，控制器可以被清楚地描述为：

1. 当前时隙先做 top-action beam selection
2. 后续步骤做贪心近似 tail rollout
3. 采用风险/证书感知的一步评分

这比以前指数分支的 rollout 更适合写成论文方法。

### 6.2 目前只是中等强度的地方

#### A. `rollout_joint` 具有竞争力，但还不是处处统治

1. 在 `paper_base` 中，`rollout_joint` 在 secrecy 上最强，并且几乎追平 `oracle_sync`。
2. 在 `paper_hard` 中，`rollout_joint` 的 secrecy 最好，但 outage 不是最优。
3. 在 `scenario_stress` 中，`security_margin` 的 outage 最好，而 `rollout_joint` 并没有统治。

因此，目前更准确的说法是：

`rollout_joint` 是一个强且有竞争力的方法，尤其在中等和困难场景中表现较好，但它还不是在所有目标和所有场景下都统一最优的控制器。`

这仍然是可投稿的，只不过这是一个更细腻的结论，而不是一个横扫式结论。

#### B. runtime 变好了，但仍然较贵

规则型方法在当前验证表里大约是 `21-30 ms/slot`，这一点很容易解释。

`rollout_joint` 现在大约是 `670-690 ms/slot`，虽然明显优于之前，但仍然偏大。

这意味着论文应该把 runtime 当作明确的系统权衡来讨论，而不是回避它。

### 6.3 目前仍然偏弱的地方

#### A. 多 seed 最终表此前仍然偏薄

当前最强的证据当时主要是：

1. 使用多个训练种子做 holdout 校准
2. 在 holdout 种子 `62` 上生成验证表

对于开发阶段评估来说，这已经很强；但对于最终论文版本，仍应加入：

1. 多 seed 的最终主表
2. 最终报告数值的 CI 或显著性区间

#### B. 证书在理论上还不够紧

尽管证书现在泛化得不错，它仍然是保守且经验型的。

这意味着：

1. 它适合作为经验性的鲁棒 bound
2. 但还不适合作为一个强解析定理

### 6.4 当前阶段的投稿成熟度

当前评估如下：

1. 项目现在已经明确具备论文能力。
2. 证书叙事比以前强得多。
3. 场景设计比以前健康得多。
4. rollout 方法在轻量化之后也更容易呈现。

最准确的判断是：

`这个项目目前已经处于一个很强的论文原型阶段，距离一篇偏应用/系统方向论文的扎实可投稿状态已经很近，但若想达到最有说服力的程度，仍需要补上多 seed 最终主表，并把最终算法 claim 表达得更清楚。`

## 7. 推荐的下一步

如果从当前继续推进，价值最高的下一步是：

1. 用多个验证种子跑最终主表，并给出置信区间。
2. 为 `rollout_joint` 加一个明确的消融表：
   full old rollout
   lightweight rollout
   no certificate penalty
   no outage penalty
3. 将方法章节围绕以下三点来写：
   empirical secrecy-loss certificate
   lightweight approximate MPC controller
   synchronization-runtime-performance tradeoff
