# scenario_stress 定向优化记录（2026-04-14）

## 1. 目标

本轮只专注解决一个问题：

> `rollout_joint` 在 `scenario_stress` 中没有形成足够硬的优势。

具体希望改进的是：

1. 降低 `outage`
2. 尽量保住或提升 `secrecy`
3. 不让 runtime 继续恶化

## 2. 做了哪些尝试

### 2.1 候选动作多样化

先在 [rollout_joint.py](../policies/rollout_joint.py) 中加入了同步动作多样化保留：

1. 根节点不再只保留一步评分最高的动作
2. 强制在候选集中保留一定数量的 `sync=True` 分支
3. tail rollout 也保留同步分支

这个改动的结果是：

1. `rollout_joint` 在 `scenario_stress` 中从几乎不同步，提升到少量同步
2. 20-seed 下 secrecy 略高于 `periodic`
3. 但 outage 仍然不如 `security_margin`

对应旧结果：
[final20_scenario_stress/main_table.csv](../results/final20_scenario_stress/main_table.csv)

### 2.2 强制应急同步

之后在 [rollout_joint.py](../policies/rollout_joint.py) 里加入 stress 专用应急同步门控：

1. 当状态 `unsafe` 且 twin badness 超过阈值时，根节点只看同步动作
2. `scenario_stress.yaml` 中增加：
   - `rollout_force_sync_if_unsafe`
   - `rollout_force_sync_badness_threshold`
   - `rollout_min_sync_branching`

这一步对应的 20-seed 结果：
[final20_scenario_stress_fix/main_table.csv](../results/final20_scenario_stress_fix/main_table.csv)

### 2.3 同步奖励型修正

最后还尝试过一个更柔和的方案：

1. 不再强制同步
2. 对高风险状态下的同步动作增加额外奖励

实现于 [simulator.py](../env/simulator.py) 中的 `lambda_sync_emergency_bonus`。

但这版结果不如强制应急同步稳定，因此没有保留为最终方案。

对应试验结果：
[stress_bonus_fix/main_table.csv](../results/stress_bonus_fix/main_table.csv)

## 3. 关键结果对比

### 3.1 原始 20-seed stress 结果

| 方法 | 平均 secrecy | outage | 同步成本 | ms/slot |
| --- | ---: | ---: | ---: | ---: |
| rollout_joint | 2.4647 | 0.4813 | 0.0703 | 228.77 |
| periodic | 2.4630 | 0.4800 | 0.1188 | 8.72 |
| security_margin | 2.4603 | 0.4759 | 0.1188 | 8.47 |

来源：
[final20_scenario_stress/main_table.csv](../results/final20_scenario_stress/main_table.csv)

### 3.2 最优修正版 20-seed stress 结果

| 方法 | 平均 secrecy | outage | 同步成本 | ms/slot |
| --- | ---: | ---: | ---: | ---: |
| rollout_joint | 2.4613 | 0.4759 | 0.1188 | 117.10 |
| periodic | 2.4630 | 0.4800 | 0.1188 | 7.42 |
| security_margin | 2.4603 | 0.4759 | 0.1188 | 7.49 |

来源：
[final20_scenario_stress_fix/main_table.csv](../results/final20_scenario_stress_fix/main_table.csv)

### 3.3 变化总结

`rollout_joint` 从原始版到最优修正版的变化：

1. 平均 secrecy：`2.4647 -> 2.4613`
2. outage：`0.4813 -> 0.4759`
3. 同步成本：`0.0703 -> 0.1188`
4. runtime：`228.77 ms/slot -> 117.10 ms/slot`

这说明：

1. 强化同步后，outage 明显改善，并追平 `security_margin`
2. secrecy 略有回落
3. runtime 反而下降了接近一半

## 4. 现在这个问题算解决了吗

### 4.1 已经解决的部分

有两个重要改善已经成立：

1. `rollout_joint` 不再在 `scenario_stress` 中明显输给 `security_margin` 的 outage
2. `rollout_joint` 的 runtime 显著下降，不再像原始版那样过于昂贵

从“系统权衡”角度看，新的 stress 版 rollout 已经比原始版更合理。

### 4.2 还没有彻底解决的部分

如果标准是：

`在 scenario_stress 中同时拿到最高 secrecy 和最低 outage`

那么这个问题还**没有彻底解决**。

当前最好的 20-seed 结果是：

1. `rollout_joint` 与 `security_margin` 在 outage 上打平
2. `rollout_joint` 的 secrecy 高于 `security_margin`
3. 但 `rollout_joint` 的 secrecy 仍略低于 `periodic`

因此，最诚实的结论是：

> 这轮定向优化显著缩小了 `scenario_stress` 下的短板，并把 `rollout_joint` 推到了更均衡的位置；  
> 但它还没有形成对所有基线的完全统治。

## 5. 当前建议

如果接下来继续只围绕这个问题推进，我建议按下面顺序做：

1. 保留当前“强制应急同步”版本，作为 stress 场景默认方案
2. 下一步不再只调阈值，而是引入真正的 stress-aware 策略切换
3. 重点研究：
   - 什么时候该像 `periodic` 那样保住 secrecy
   - 什么时候该像 `security_margin` 那样优先压 outage

也就是说，下一阶段最值得做的不是继续微调几个标量系数，而是做一个：

`risk-adaptive hybrid rollout`

这样才更有希望在 `scenario_stress` 下真正同时吃到两边的优势。

## 6. 2026-04-15 实施结果（risk-adaptive hybrid rollout）

本轮已完成三件事：

1. 保留当前“强制应急同步”版本为默认 `rollout_joint`（未改默认 stress 基线行为）。
2. 新增方法 `risk_adaptive_hybrid_rollout`，通过 `RolloutJointController` 内部三态门控实现 stress-aware 切换：
   - `force_sync`：高风险时走 `security_margin` 风格（优先压 outage）
   - `force_nosync`：预算紧张时进入 `hybrid_budget_guard`（更接近 periodic 的节奏控制）
   - `free`：过渡状态保持 rollout 自主搜索
3. 将新方法接入实验入口（`experiments/common.py`、`run_baselines.py`、`run_readiness_multiseed.py`、`run_publication_suite.py`）。

### 6.1 代码落点

- [rollout_joint.py](../policies/rollout_joint.py)
- [common.py](../experiments/common.py)
- [run_baselines.py](../experiments/run_baselines.py)
- [run_readiness_multiseed.py](../experiments/run_readiness_multiseed.py)
- [run_publication_suite.py](../experiments/run_publication_suite.py)
- [scenario_stress.yaml](../configs/scenario_stress.yaml)

### 6.2 stress 小规模验证（5 seeds: 62-66）

结果目录：
[risk_adaptive_hybrid_stress_smoke](../results/risk_adaptive_hybrid_stress_smoke)

| 方法 | 平均 secrecy | outage | 同步成本 | ms/slot |
| --- | ---: | ---: | ---: | ---: |
| risk_adaptive_hybrid_rollout | 2.4654 | 0.4775 | 0.1188 | 138.08 |
| rollout_joint（默认应急版） | 2.4628 | 0.4738 | 0.1188 | 119.64 |
| periodic | 2.4634 | 0.4888 | 0.1188 | 7.82 |
| security_margin | 2.4619 | 0.4738 | 0.1188 | 8.17 |

阶段性解读：

1. hybrid 已经拿到最高 secrecy（高于 periodic / rollout_joint / security_margin）。
2. outage 还没有压到 `security_margin` 水平，当前处于中间带（优于 periodic，略弱于 security_margin/rollout_joint）。
3. 行为层面确实出现了策略切换，不再是“前 19 个时隙一次性耗尽预算”。

在 5-seed 的 hybrid 逐时隙统计中，`sync_reason` 汇总为：

- `hybrid_outage_priority`: 95
- `hybrid_budget_guard`: 150
- `rollout_skip`: 555

这说明“何时像 security_margin 压 outage、何时像 periodic 控节奏”已经进入可执行阶段，但还需要继续调 gating 参数以进一步压低 outage。
