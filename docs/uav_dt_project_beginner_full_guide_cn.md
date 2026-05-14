# UAV 数字孪生安全通信项目完整讲解

生成日期：2026-04-28

这份文档假设读者不了解 UAV 通信、物理层安全、数字孪生、AoI、Kalman filter 或 conformal certificate。它的目标不是把每个公式推到最深，而是让你能从“这个项目到底在干什么”一路理解到“为什么这样设计实验、结果怎么看、论文应该怎么讲”。

---

## 1. 一句话说明这个项目

本项目研究的是：

**在有窃听者 Eve 的 UAV 安全通信系统中，数字孪生会因为不同步而逐渐变旧，同步又有带宽成本、预算限制、时延和失败概率；因此系统需要联合决定什么时候同步数字孪生、两架 UAV 怎么移动、怎么分配发射功率和干扰功率，最终尽量提高保密通信性能。**

再直白一点：

1. UAV 想给地面用户安全传信息。
2. Eve 想偷听。
3. 系统维护了一个“数字孪生”，用来估计 Eve 在哪里。
4. 这个估计会过期，过期以后决策可能变差。
5. 同步孪生能变准，但同步要消耗资源。
6. 我们的方法 `rollout_joint` 就是在有限资源下，聪明地决定同步、移动和功率。

---

## 2. 先把故事讲成一个生活类比

你可以把这个系统想成一个“空中护送通信任务”。

有两架无人机：

1. **UAV-1**：负责给地面用户发送保密信息。
2. **UAV-2**：负责发干扰信号，尽量让 Eve 听不清。

地面上有：

1. **合法用户**：真正要接收信息的人。
2. **Eve**：窃听者，想靠近并截获信号。
3. **基站或边缘服务器**：维护仿真和决策系统。

系统还有一个“数字孪生”：

1. 它是现实世界的虚拟副本。
2. 它记录 Eve 的估计位置、估计速度和不确定性。
3. UAV 做决策时，很多时候只能看数字孪生，而不是直接看真实 Eve。

问题在于，Eve 是会移动的。如果数字孪生很久不更新，它里面的 Eve 位置就会越来越不准。此时系统可能以为“我离 Eve 很远，很安全”，但真实情况是 Eve 已经接近了。

同步数字孪生可以修正这个问题，但同步不是免费的：

1. 同步要消耗带宽。
2. 每个 episode 总同步预算有限。
3. 同步有 1 个时隙延迟。
4. 同步还可能失败。

所以核心矛盾是：

**同步太多会浪费资源；同步太少会让数字孪生过时，导致保密通信变差。**

---

## 3. 这个项目为什么有研究意义

很多 UAV 安全通信论文会研究：

1. UAV 怎么飞。
2. UAV 发射功率怎么调。
3. 干扰机怎么帮助压制 Eve。
4. 如何最大化 secrecy rate。

也有很多数字孪生或 AoI 论文会研究：

1. 信息多久更新一次。
2. 数据新鲜度如何影响系统性能。
3. 如何降低同步成本。

本项目的特点是把这两条线连起来：

1. **安全通信不是单独的通信问题**：因为对 Eve 位置判断不准会直接影响 secrecy rate。
2. **数字孪生同步不是单独的新鲜度问题**：因为同步是否值得，要看它能否改善安全通信决策。
3. **UAV 控制不是单独的轨迹问题**：因为飞行、功率、干扰、同步四件事互相影响。

因此，本项目的研究对象可以概括为：

**数字孪生不确定性驱动的 UAV 安全通信联合控制。**

---

## 4. 项目中的主要角色

### 4.1 UAV-1：服务 UAV

UAV-1 是主要发送保密数据的 UAV。它有位置和发射功率 `p_s`。

它离合法用户越近，合法链路通常越强；它离 Eve 越远，Eve 窃听链路通常越弱。

### 4.2 UAV-2：干扰 UAV

UAV-2 负责发干扰信号，功率为 `p_j`。

理想情况下，UAV-2 的干扰应该：

1. 对 Eve 影响很大。
2. 对合法用户影响尽量小。

但现实里干扰也会泄漏到合法用户，所以项目中设置了合法链路干扰泄漏系数 `xi_legit_interference`。

### 4.3 地面用户

每个场景有 3 个地面用户。每个时隙系统会计算服务哪个用户能获得最大的 secrecy rate。

### 4.4 Eve

Eve 是窃听者。项目中的 Eve 不是固定不动的，也不是简单直线运动，而是 `adaptive_mobile`：

1. 它会根据 UAV 当前位置和功率，选择更有利于窃听的移动方向。
2. 它会受到速度噪声影响。
3. 它的位置会被限制在仿真区域内。

这比固定 Eve 更难，因为系统必须不断应对一个主动变化的威胁。

### 4.5 数字孪生

数字孪生维护 Eve 的估计状态。它包含：

1. Eve 估计位置。
2. Eve 估计速度。
3. 协方差或不确定性。
4. AoI，也就是距离上次有效同步过去了多久。

同步成功时，数字孪生会根据观测更新；不同步时，它只能做预测，误差通常会扩大。

---

## 5. 仿真环境长什么样

正式主实验有三个场景：

1. `paper_base`
2. `paper_hard`
3. `scenario_stress`

它们都采用：

1. `500 m x 500 m` 的二维水平区域。
2. UAV 固定高度 `100 m`。
3. 2 架 UAV。
4. 3 个合法用户。
5. 1 个 Eve。
6. 离散时隙仿真，`delta_t = 1.0`。

三个场景逐渐变难：

| 场景 | episode 长度 | 同步预算 | Eve 最大速度 | 安全门限 `r_min` | 含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| `paper_base` | 120 | 28.0 | 5.5 | 2.55 | 基础场景 |
| `paper_hard` | 140 | 22.0 | 6.6 | 2.72 | 困难场景 |
| `scenario_stress` | 160 | 19.0 | 7.8 | 1.10 | 压力场景，门限按可达性校准 |

从 base 到 stress：

1. Eve 更快。
2. 同步预算更少。
3. Eve 更接近通信热点，且信道/同步不确定性更强。
4. episode 更长。
5. 数字孪生不确定性更强。

说明：`scenario_stress` 旧版曾使用 `r_min = 2.82`。诊断发现该门限高于该场景下代表性方法甚至 oracle 的可达时隙保密速率，导致所有方法 `outage_prob = 1.0`。当前版本将压力场景门限校准为 `1.10`，使 outage 既有压力又有区分度。

这意味着 stress 场景不是为了让方法“好看”，而是为了检验方法边界。

---

## 6. 信道模型和 secrecy rate

项目采用概率 LoS/NLoS 空地信道。简单说：

1. UAV 和地面节点距离越远，信道越弱。
2. UAV 高度固定，所以 3D 距离由水平距离和高度一起决定。
3. LoS 概率由仰角决定。
4. LoS 和 NLoS 有不同额外损耗。

通信速率用 Shannon 型公式计算：

```text
rate = log2(1 + SINR)
```

合法用户速率记为 `r_b`，Eve 窃听速率记为 `r_e`。

项目最核心的保密速率是：

```text
r_sec = max(r_b - r_e, 0)
```

这是什么意思？

1. 如果合法链路比 Eve 链路好，`r_b - r_e` 为正，可以安全传输一部分信息。
2. 如果 Eve 链路和合法链路一样好，甚至更好，那么保密速率接近 0。
3. `max(..., 0)` 表示保密速率不会是负数，最差就是没有安全传输能力。

这正是物理层安全领域常用的 secrecy rate 思想。

---

## 7. 什么是 outage

项目中定义了安全门限 `r_min`。如果某个时隙真实保密速率低于这个门限：

```text
true_r_sec < r_min
```

就认为这个时隙发生安全中断，记为 `outage = 1`。

因此：

```text
outage_prob = outage 时隙比例
```

如果 `outage_prob = 0.9`，说明 90% 的时隙都没有达到最低保密速率要求。

注意：secrecy rate 和 outage 不完全等价。

1. 一个方法可能平均 secrecy rate 高，但偶尔掉得很厉害，outage 也高。
2. 另一个方法可能平均 secrecy rate 不最高，但更稳定，outage 更低。

所以论文中通常要同时看 secrecy rate 和 outage。

---

## 8. 动作空间是什么

每个时隙，控制器要决定四类动作：

1. UAV-1 怎么移动。
2. UAV-2 怎么移动。
3. UAV-1 用多大发射功率。
4. UAV-2 用多大干扰功率。
5. 是否发起数字孪生同步，以及同步带宽是多少。

### 8.1 移动动作

每架 UAV 有 9 个移动动作：

```text
stay, up, down, left, right, up_left, up_right, down_left, down_right
```

步长为 `10 m`。对角方向会归一化，所以对角移动距离也是 `10 m`，不是 `10 * sqrt(2)`。

### 8.2 功率动作

服务 UAV 的功率候选：

```text
p_s_levels = [0.35, 0.50, 0.65, 0.80, 1.00]
```

干扰 UAV 的功率候选：

```text
p_j_levels = [0.00, 0.25, 0.50, 0.75, 1.00]
```

### 8.3 同步动作

同步带宽候选：

```text
sync_bandwidth_levels = [0.25, 0.50, 0.75, 1.00]
```

同步带宽越大，通常观测质量越好，但消耗预算也越多。

### 8.4 动作空间为什么不小

只看移动：

```text
UAV-1 9 种动作 x UAV-2 9 种动作 = 81 种移动组合
```

再乘以功率：

```text
5 种 p_s x 5 种 p_j = 25 种功率组合
```

如果再考虑同步带宽，组合数会继续上升。

所以 `rollout_joint` 不能暴力无限展开所有未来，而是采用候选筛选、branching limit 和短视界 rollout。

---

## 9. 数字孪生如何更新

数字孪生不是简单地保存一个位置，而是用类似 Kalman tracker 的方式维护状态。

### 9.1 同步成功时

系统收到关于 Eve 的新观测，观测噪声与同步带宽有关：

1. 带宽越大，测量噪声越小。
2. 带宽越小，测量噪声越大。

然后孪生状态被更新，AoI 归零。

### 9.2 不同步时

孪生只能根据上一时刻估计做预测：

1. Eve 位置向前预测。
2. 不确定性增加。
3. AoI 增加。

### 9.3 同步不是立即完美生效

本项目里同步有：

1. `delay_slots = 1`
2. `failure_prob > 0`

也就是说，今天发起同步，不一定马上刷新，而且可能失败。

这比“同步立即成功”的理想模型更贴近实际，也让问题更难。

---

## 10. twin quality 和 twin badness

项目用 `twin_badness` 衡量数字孪生有多糟糕，用 `twin_quality` 衡量有多好。

`twin_badness` 来自三部分：

1. AoI：多久没更新。
2. Eve 真实位置与孪生估计位置的误差。
3. Kalman sigma：估计不确定性。

公式可以理解为：

```text
twin_badness = 0.35 * normalized_aoi
             + 0.45 * normalized_eve_error
             + 0.20 * normalized_sigma
```

然后：

```text
twin_quality = 1 - clipped(twin_badness)
```

这说明本项目不是只看“多久没同步”，而是同时看：

1. 同步新鲜度。
2. 实际估计误差。
3. 状态不确定性。

这也是项目区别于普通 AoI-only 同步策略的地方。

---

## 11. 本项目实现了哪些方法

### 11.1 `periodic`

固定周期同步，例如每隔 `k` 个时隙同步一次。

优点：

1. 简单。
2. 稳定。
3. 很适合当强 baseline。

缺点：

1. 不管当前是否危险。
2. 可能在安全时浪费同步。
3. 也可能在危险时没及时同步。

### 11.2 `security_risk`

根据 AoI、预测误差、sigma、预测安全缺口等因素构造风险分数。风险超过阈值就同步。

优点：

1. 比 periodic 更有状态感知能力。
2. 同步成本通常更低。

缺点：

1. 仍然是规则触发。
2. 同步和 UAV 移动/功率没有真正联合前瞻优化。

### 11.3 `security_margin`

使用安全证书判断当前安全裕度是否足够。如果证书认为当前裕度不足，就同步。

优点：

1. 可解释。
2. 和本文的 certificate 叙事匹配。

缺点：

1. 如果证书过保守，可能过度同步。
2. 如果证书拟合不足，可能保护效果不稳定。

### 11.4 `rollout_joint`

这是当前主方法。

它联合考虑：

1. 是否同步。
2. 同步带宽是多少。
3. UAV-1 和 UAV-2 怎么移动。
4. `p_s` 和 `p_j` 怎么选。
5. 当前动作对未来几步的影响。

它更像一个轻量级模型预测控制方法：

1. 先生成候选动作。
2. 对动作打分。
3. 克隆环境状态，向前模拟一小段。
4. 计算即时收益和未来收益。
5. 选综合价值最高的动作。

它不是深度强化学习，不需要训练神经网络；它依赖的是已知仿真模型和可解释评分函数。

### 11.5 `oracle_sync`

这是参考上界，不是实际可部署方法。

它假设可以使用真实 Eve 状态来辅助决策，用来观察“如果信息几乎完美，性能上限大概在哪里”。

---

## 12. `rollout_joint` 的评分逻辑

`rollout_joint` 不是只追求 secrecy rate。它的评分函数大致同时考虑：

1. 预测保密速率。
2. UAV 移动成本。
3. 发射功率和干扰功率成本。
4. 同步成本。
5. outage 惩罚。
6. certificate 惩罚。
7. pending sync 队列惩罚。
8. twin badness 惩罚。
9. margin bonus。
10. 同步价值奖励。

这很重要，因为系统目标不是单一最大化通信速率，而是要在安全、同步、资源和实时性之间折中。

---

## 13. 什么是安全证书 certificate

安全证书回答的问题是：

**在当前数字孪生误差和同步不确定性下，系统需要多大的安全裕度，才可以相信当前通信是安全的？**

项目里有一个 `required_margin`：

```text
required_margin = rho + empirical_upper_bound
```

也有一个实际预测安全裕度：

```text
predicted_margin = pred_r_sec - r_min
```

然后：

```text
cert_slack = predicted_margin - required_margin
```

如果：

```text
cert_slack >= 0
```

说明证书认为当前状态有足够安全余量。

如果：

```text
cert_slack < 0
```

说明当前不确定性太大，或者预测安全裕度太小，最好同步或采取更保守动作。

---

## 14. 为什么使用 conformal/holdout 思路

早期可以用手工规则估计 secrecy loss 上界，例如：

```text
loss_bound = k1 * pred_error_radius + k2 * sigma + k3 * aoi
```

但手工规则有一个问题：参数是否可信？

因此项目进一步使用 holdout-fit：

1. 先用训练场景和训练方法收集数据。
2. 计算预测 secrecy 与真实 secrecy 的差距，也就是 realized loss。
3. 用特征回归拟合 secrecy loss。
4. 用 calibration/holdout 方式给出保守 buffer。
5. 在验证场景上检查 cover rate。

这样得到的证书更适合论文表达，因为它不是拍脑袋说“我觉得风险高”，而是有数据校准过程。

---

## 15. 本项目的指标怎么看

### 15.1 主指标

| 指标 | 含义 | 越大/越小 |
| --- | --- | --- |
| `avg_secrecy_rate_mean` | 多 seed 平均真实保密速率 | 越大越好 |
| `outage_prob_mean` | 低于安全门限的时隙比例 | 越小越好 |
| `avg_sync_cost_mean` | 平均同步资源消耗 | 越小越省 |
| `certificate_in_policy_cover_rate_mean` | controller 使用 certificate 后的 in-policy 覆盖/合规比例 | 只能说明当前策略分布下的合规情况 |
| `runtime_per_slot_ms_mean` | 每个时隙平均决策时间 | 越小越快 |
| `secrecy_gain_vs_periodic` | 相对 periodic 的 secrecy 提升 | 越大越好 |

### 15.2 辅助指标

| 指标 | 含义 |
| --- | --- |
| `avg_twin_quality` | 数字孪生平均质量 |
| `avg_twin_badness` | 数字孪生平均恶化程度 |
| `avg_realized_loss` | 预测过乐观造成的真实 secrecy loss |
| `avg_margin_gap` | 预测 secrecy 与真实 secrecy 的平均差距 |
| `avg_cert_slack` | 证书裕度 |
| `certificate_violation_prob` | 证书判定不安全的比例 |
| `prediction_violation_prob` | 预测 secrecy 高于真实 secrecy 的比例 |
| `success_prob` | `1 - outage_prob` |

### 15.3 为什么不能只看一个指标

如果只看 secrecy rate，可能忽略同步成本和 outage。

如果只看 outage，可能忽略平均性能。

如果只看同步成本，可能得到一个几乎不同步但安全性能很差的方法。

如果只看 runtime，最快的通常是简单 baseline，但不一定最好。

所以项目主表同时报告 secrecy、outage、sync cost、certificate cover 和 runtime。

---

## 16. 当前最新结果怎么理解

当前最新结果在：

```text
docs/scheme_c_results_2026-04-26_rollout_tuned_full.md
```

完整结果目录包括：

```text
results/scheme_c_holdout_2026-04-26_rollout_tuned_full
results/scheme_c_readiness_parallel_2026-04-26_rollout_tuned_full
results/scheme_c_readiness_20seed_2026-04-26_rollout_tuned_full_merged
```

最新主表显示：

| 场景 | `rollout_joint` secrecy | `periodic` secrecy | 相对增益 |
| --- | ---: | ---: | ---: |
| `paper_base_holdoutfit` | 1.6522 | 1.6313 | +0.0208 |
| `paper_hard_holdoutfit` | 1.4627 | 1.2951 | +0.1676 |
| `scenario_stress_holdoutfit` | 1.2670 | 0.9975 | +0.2695 |

配对 seed 比较也显示：

| 场景 | 胜出 seed |
| --- | ---: |
| `paper_base_holdoutfit` | 17 / 20 |
| `paper_hard_holdoutfit` | 20 / 20 |
| `scenario_stress_holdoutfit` | 20 / 20 |

这说明当前调优后的 `rollout_joint` 已经不是偶然在某个 seed 上好，而是在多 seed、多场景下都比较稳定。

---

## 17. 为什么结果不能和其他论文直接横比

你可能会问：

**别人的论文 secrecy rate 是 5，我们这里是 1.65，是不是别人更强？**

不能这么比。

因为不同论文的：

1. 区域大小不同。
2. UAV 高度不同。
3. 用户数量不同。
4. Eve 数量和移动方式不同。
5. 信道模型不同。
6. 噪声功率不同。
7. 安全门限不同。
8. 动作空间不同。
9. 是否有 jammer 不同。
10. 是否考虑数字孪生老化不同。
11. 是否考虑同步预算、时延、失败概率不同。

这些都会直接改变 secrecy rate 和 outage 的绝对值。

因此，合理的论文表述是：

1. 我们采用了领域通用指标，例如 secrecy rate、outage probability、同步/能耗成本。
2. 我们不能直接与外部论文做绝对数值横比。
3. 我们可以比较指标类型、趋势和问题设置。
4. 如果要公平比较外部算法，必须把外部算法复现在同一仿真环境中。

---

## 18. 项目目录结构怎么读

### 18.1 `env/`

环境层。

| 文件 | 作用 |
| --- | --- |
| `entities.py` | 定义 UAV、User、Eve、TwinState 等实体 |
| `mobility.py` | 定义移动方向和位置裁剪 |
| `channel.py` | 计算信道增益、速率、secrecy rate |
| `twin.py` | 数字孪生预测、同步、质量指标 |
| `sync.py` | 同步策略和安全证书 |
| `simulator.py` | 主环境，负责 reset、step、候选动作评估 |

如果你想理解“仿真世界怎么运转”，优先看 `env/simulator.py`。

### 18.2 `policies/`

方法层。

| 文件 | 作用 |
| --- | --- |
| `greedy_joint.py` | periodic、aoi_only、security_risk、security_margin 等规则方法 |
| `decoupled.py` | 同步与控制解耦的 baseline |
| `random_budgeted.py` | 随机预算同步 baseline |
| `rollout_joint.py` | 当前主方法 |

如果你想理解论文主方法，重点看 `policies/rollout_joint.py`。

### 18.3 `experiments/`

实验层。

| 文件 | 作用 |
| --- | --- |
| `common.py` | 统一加载配置、运行单个 episode |
| `run_baselines.py` | 跑 baseline |
| `run_readiness_multiseed.py` | 跑多 seed 主表 |
| `fit_certificate_holdout.py` | 拟合和验证 certificate |
| `run_scheme_c_pipeline.py` | 串起 holdout、主实验、小 MDP 上界 |
| `run_rollout_ablations.py` | 做主方法消融 |
| `run_runtime_tradeoff.py` | 做运行时间 tradeoff |
| `run_small_mdp_bound.py` | 小场景理论上界 |

如果你想复现实验，先看 `experiments/run_readiness_multiseed.py`。

### 18.4 `analysis/`

统计层。

| 文件 | 作用 |
| --- | --- |
| `metrics.py` | 计算 episode summary、多 seed 平均、置信区间 |
| `plotter.py` | 画线图、散点图、Pareto 图 |

### 18.5 `configs/`

配置层。

| 文件 | 作用 |
| --- | --- |
| `smoke.yaml` | 快速测试 |
| `paper_base.yaml` | 正式基础场景 |
| `paper_hard.yaml` | 正式困难场景 |
| `scenario_stress.yaml` | 正式压力场景 |
| `small_mdp_bound.yaml` | 小 MDP 上界实验 |

### 18.6 `docs/` 和 `results/`

文档和结果层。

`docs/` 存放说明文档、实验报告和执行清单。  
`results/` 存放 CSV、Markdown 表格和中间实验结果。

---

## 19. 运行项目的基本流程

### 19.1 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 19.2 冒烟测试

```bash
python -m experiments.run_readiness_multiseed \
  --configs configs/smoke.yaml \
  --methods rollout_joint \
  --num-seeds 1 \
  --seed-start 62 \
  --outdir /tmp/uav_dt_rollout_smoke
```

### 19.3 跑正式多 seed 主实验

```bash
python -m experiments.run_readiness_multiseed \
  --configs configs/paper_base.yaml configs/paper_hard.yaml configs/scenario_stress.yaml \
  --methods periodic security_risk security_margin rollout_joint \
  --num-seeds 20 \
  --seed-start 62 \
  --outdir results/readiness_multiseed
```

### 19.4 看主结果表

```bash
cat results/readiness_multiseed/main_table.md
```

---

## 20. 论文叙事应该怎么讲

论文主线可以这样组织：

1. UAV 安全通信需要联合轨迹和功率控制。
2. 现实中 Eve 状态不可能永远准确，因此引入数字孪生。
3. 数字孪生会老化，频繁同步又有资源成本。
4. 因此问题变成同步、轨迹、功率、安全证书的联合决策。
5. 本文提出 `rollout_joint`，在短视界内联合评估同步和控制动作。
6. 为了避免过度依赖不准的孪生预测，引入经验校准的 secrecy-loss certificate。
7. 多场景多 seed 实验表明，调优后的 `rollout_joint` 在 secrecy rate 上稳定优于固定周期同步等 baseline。

可以强调的创新点：

1. 把数字孪生同步质量纳入 UAV 安全通信控制。
2. 同步动作不是固定周期，而是与轨迹/功率联合前瞻决策。
3. 考虑同步带宽、同步延迟、同步失败和预算约束。
4. 引入 empirical/conformal-style secrecy-loss certificate。
5. 在 base、hard、stress 三类场景中进行多 seed 验证。

---

## 21. 项目的边界和不足

这个项目是一个纯 Python 仿真框架，不是真机系统。

当前没有包含：

1. ROS/Gazebo/QGroundControl 真机链路。
2. 真实无线信道测量。
3. 连续动作优化。
4. 深度强化学习。
5. 多 Eve 大规模场景。
6. 多 UAV swarm 的复杂编队控制。

这些不是缺陷，而是当前论文阶段的边界。写论文时要诚实说明：

1. 本文关注机制验证和算法对比。
2. 当前结果是仿真环境下的多 seed 评估。
3. 外部论文绝对数值不可直接横比。
4. 后续可扩展到更真实的信道、更多 UAV/Eve 和硬件在环。

---

## 22. 推荐阅读论文和资料

下面按学习顺序推荐。每篇都附上“为什么读”和“对应本项目哪一部分”。

### 22.1 物理层安全基础

1. **A. D. Wyner, "The Wire-Tap Channel", Bell System Technical Journal, 1975.**
   - 链接：https://doi.org/10.1002/j.1538-7305.1975.tb02040.x
   - 为什么读：这是物理层安全的源头之一，解释为什么可以从信道差异中获得保密性。
   - 对应项目：理解 `r_sec = max(r_b - r_e, 0)` 背后的基本思想。

2. **Zhou et al., "UAV-enabled secure communications: joint trajectory and transmit power optimization", IEEE TVT, 2019.**
   - 链接：https://doi.org/10.1109/TVT.2019.2900157
   - 为什么读：非常贴近本项目的 UAV 安全通信设置，包含 UAV base station、UAV jammer、轨迹和功率联合优化。
   - 对应项目：理解为什么 UAV 轨迹、服务功率、干扰功率需要联合考虑。

3. **An et al., "Secrecy Capacity Maximization of UAV-Enabled Relaying Systems with 3D Trajectory Design and Resource Allocation", Sensors, 2022.**
   - 链接：https://www.mdpi.com/1424-8220/22/12/4519
   - 为什么读：帮助理解 UAV relay、资源分配、3D 轨迹和 secrecy capacity 的常见建模方式。
   - 对应项目：理解本项目为什么要报告 secrecy rate、outage、功率和轨迹相关指标。

### 22.2 UAV 轨迹控制和 MPC 思路

4. **Lan et al., "Secure communications for UAV relay networks: a MPC-based trajectory tracking approach", EURASIP JWCN, 2025.**
   - 链接：https://link.springer.com/article/10.1186/s13638-025-02454-z
   - 为什么读：该文把安全通信、功率分配、UAV 轨迹和 MPC 联系起来。
   - 对应项目：理解 `rollout_joint` 为什么可以类比为轻量级 receding-horizon/MPC 思路。

### 22.3 AoI、同步新鲜度和数字孪生

5. **Amodu et al., "Age of Information minimization in UAV-aided data collection for WSN and IoT applications: A systematic review", JNCA, 2023.**
   - 链接：https://doi.org/10.1016/j.jnca.2023.103652
   - 为什么读：这是 UAV + AoI 数据采集方向的综述，适合入门。
   - 对应项目：理解 AoI 为什么能衡量信息新鲜度，以及为什么 UAV 系统经常关注 AoI。

6. **Loubany et al., "From Age of Information to Age of Digital Twin: A Review on Synchronization Metrics for IoT Networks", IEEE Access, 2025.**
   - 链接：https://doi.org/10.1109/ACCESS.2025.3591589
   - 为什么读：它把 AoI 推进到 Age of Digital Twin 和同步指标，更贴近数字孪生系统。
   - 对应项目：理解本项目为什么不只看 AoI，还要看 `twin_quality` 和 `twin_badness`。

7. **Wang et al., "Age of Information-Inspired Data Collection and Secure Upload Assisted by the UAV and RIS in Maritime Wireless Sensor Networks", Drones, 2024.**
   - 链接：https://www.mdpi.com/2504-446X/8/6/267
   - 为什么读：它同时涉及 UAV、AoI 和安全上传，和本项目的“新鲜度 + 安全”方向有交集。
   - 对应项目：理解 AoI 和安全传输可以放在同一个优化问题中。

### 22.4 不确定性量化和 conformal certificate

8. **Angelopoulos and Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification", arXiv, 2021.**
   - 链接：https://arxiv.org/abs/2107.07511
   - 入门网页：https://people.eecs.berkeley.edu/~angelopoulos/blog/posts/gentle-intro/
   - 为什么读：这是 conformal prediction 非常友好的入门资料。
   - 对应项目：理解为什么可以用 holdout/calibration 思路构造保守上界，并用 `cover_rate` 检查它是否可信。

---

## 23. 建议阅读顺序

如果你完全不懂领域，建议按这个顺序读：

1. 先读本文件第 1-10 节，建立项目直觉。
2. 读 Zhou et al. 2019，理解 UAV 安全通信、jammer、轨迹和功率。
3. 读 Lan et al. 2025，理解 MPC/receding-horizon 风格的安全轨迹控制。
4. 读 AoI UAV 综述，理解信息新鲜度。
5. 读 Age of Digital Twin 综述，理解数字孪生同步指标。
6. 最后读 conformal prediction 入门，理解证书覆盖率。
7. 回头看 `env/simulator.py`、`policies/rollout_joint.py` 和最新结果文档。

---

## 24. 如果要向别人介绍这个项目，可以这样说

简短版：

**我们研究数字孪生辅助的 UAV 安全通信。在存在移动窃听者 Eve 的情况下，系统需要基于可能过时的数字孪生状态做轨迹、功率和同步决策。我们提出 `rollout_joint`，联合评估同步、移动和功率动作，并结合经验校准的安全证书来控制数字孪生误差带来的 secrecy loss。多场景多 seed 实验显示，该方法在平均保密速率上稳定优于固定周期同步和安全风险规则基线。**

更口语版：

**这个项目解决的是“无人机怎么在有限同步预算下安全通信”的问题。我们不假设系统永远知道窃听者准确位置，而是维护一个会变旧的数字孪生。方法的关键是判断什么时候值得同步，以及同步、飞行、功率和干扰应该怎么一起决策。**

---

## 25. 最后总结

这个项目可以从四个层次理解：

1. **通信层**：最大化 secrecy rate，降低 outage。
2. **控制层**：联合优化 UAV 移动、服务功率和干扰功率。
3. **数字孪生层**：处理 Eve 状态估计老化和不确定性。
4. **同步决策层**：在有限预算、时延和失败概率下决定何时更新孪生。

项目的核心贡献不是某一个单独模块，而是把这些模块放进同一个仿真闭环中，并通过 `rollout_joint` 做联合前瞻决策。

这也是它适合写成论文的原因：它不是单纯跑一个 baseline，而是围绕一个清晰问题建立了环境、方法、证书、指标、场景和实验结果。
