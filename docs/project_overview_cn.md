# UAV_DT 项目中文总览

## 1. 项目一句话概括

这是一个面向无人机安全通信场景的纯 Python 仿真项目，研究的问题是：

在数字孪生信息会变旧、同步预算有限、同步存在时延和失败概率的条件下，如何联合决定“什么时候同步孪生”和“无人机如何移动/发射功率”，从而尽量提升保密速率、降低 outage，并控制同步开销。

---

## 2. 整个项目做了什么

### 2.1 项目研究对象

项目构建了一个小规模离散时隙 UAV 安全通信环境，典型场景包括：

- 1 个基站 / 边缘服务器
- 2 架合法 UAV
- 1 个窃听者 Eve
- 3 个地面用户

其中：

- `UAV-1` 主要承担服务/传输任务
- `UAV-2` 主要承担干扰/jamming 任务
- Eve 会运动，因此系统对 Eve 位置的认知会随时间失真

项目的关键设定不是“完美已知环境”，而是引入了数字孪生的不确定性：

- 系统同时维护 `true state` 和 `twin state`
- 如果长时间不同步，孪生会老化，表现为 `AoI` 增大、位置估计误差扩大、方差 `sigma` 增大
- 同步不是免费的，存在预算 `budget`
- 同步还可能有 `delay_slots` 和 `failure_prob`

因此，这个项目本质上在研究一个三元耦合问题：

1. 同步代价 `sync cost`
2. 孪生质量 `twin quality`
3. 安全通信性能 `secrecy performance`

### 2.2 项目具体完成了哪些模块

项目已经搭建了比较完整的研究流水线：

- 环境建模：`env/`
- 策略实现：`policies/`
- 实验脚本：`experiments/`
- 指标汇总与统计：`analysis/`
- 多场景配置：`configs/`
- 实验结果与论文主表文档：`results*/` 与 `docs/`

从研究流程看，项目已经不是“只有几个 baseline 的玩具脚本”，而是做成了一个较完整的仿真论文框架：

1. 先搭基础场景和 baseline
2. 再研究同步-孪生-保密的耦合关系
3. 再加入安全感知同步阈值设计
4. 再把手工证书规则升级为可拟合、可验证的经验型证书模型
5. 最后围绕论文场景做多轮调参与主表整理

---

## 3. 项目使用了什么方法

### 3.1 环境与指标层的方法

项目的底层方法不是深度学习，而是“可解释的模型驱动仿真 + 启发式/前瞻式控制”。

核心组件包括：

- 运动学更新：UAV 和 Eve 在二维平面按离散时隙移动
- 信道模型：根据 UAV、用户、Eve 的相对位置计算合法链路与窃听链路速率
- 数字孪生跟踪：同步时重置估计；不同步时按预测推进，并累积 `AoI` 与 `sigma`
- 孪生质量函数：把 `AoI`、Eve 估计误差、`sigma` 组合为 `twin_quality / twin_badness`
- 保密证书：根据 `AoI`、预测误差半径、`sigma`、同步时延和失败率，估计 secrecy loss upper bound，并判断当前预测 margin 是否足够安全

项目最终关注的关键指标包括：

- `avg_secrecy_rate`
- `outage_prob`
- `avg_sync_cost`
- `avg_twin_quality`
- `avg_cert_slack`
- `certificate_cover_rate`
- `runtime_per_slot_ms`

### 3.2 策略层的方法

项目里的方法大体可以分成三类。

#### A. 规则型同步 + 贪心联合控制

这一类方法先根据某个同步规则决定要不要 sync，再在当前时隙贪心选择 UAV 动作和功率。

代表方法有：

- `full`
- `periodic`
- `aoi_only`
- `security_risk`
- `security_margin`

其中：

- `full`：只要预算还有就同步
- `periodic`：每隔固定周期同步一次
- `aoi_only`：AoI 超过阈值就同步
- `security_risk`：把 AoI、预测误差半径、sigma、预测 secrecy 缺口加权成风险值，再和阈值比较
- `security_margin`：利用 secrecy certificate 判断当前 margin 是否足够，如果证书不安全就同步

#### B. 解耦式 baseline

- `decoupled`

这个方法先按固定同步规则决定是否同步，再在动作打分时不把同步代价和轨迹/功率控制真正联合起来优化，因此它是典型的“同步与控制分开做”的 baseline。

#### C. 前瞻式联合控制方法

- `rollout_joint`
- `oracle_sync`

这两个是项目里更强的方法。

`rollout_joint` 的核心思想是：

- 在当前时隙同时枚举同步、轨迹和功率动作
- 用轻量化 rollout 近似未来若干步收益
- 评分不仅考虑预测保密速率，还考虑
  - outage penalty
  - certificate penalty
  - pending sync backlog
  - projected twin badness
  - 正的 margin bonus

因此它更接近一个轻量级近似 MPC，而不是单步贪心。

`oracle_sync` 不是可实现方法，而是“用真实 Eve 状态做近似上界”的参考方法。它主要用于说明：如果同步/状态认知几乎完美，系统最多能做到什么程度。

### 3.3 证书方法的演进

项目的方法升级里，最重要的一条线就是证书模型的演进。

第一阶段：

- 使用手工设定的理论 margin 系数
- `security_margin` 依赖这个手工证书进行同步判断

后续发现的问题是：

- 手工证书覆盖率和紧致性都不够稳定
- 在较难场景下很难真正指导同步

第二阶段：

- 增加 `calibrate_margin.py`
- 对 `rho` 和 margin 系数做校准

第三阶段：

- 增加 `fit_certificate_holdout.py`
- 用训练/验证分离的方式拟合非负 ridge 证书模型
- 输出 holdout-fitted config

这一升级使项目现在可以把证书写成：

`empirically calibrated conservative secrecy-loss certificate`

这比早期纯手工规则更适合论文叙事。

---

## 4. baseline 是什么

如果按实验脚本 `experiments/run_baselines.py` 的定义，项目目前的 baseline / 对比方法包括：

- `full`
- `periodic`
- `aoi_only`
- `decoupled`
- `security_margin`
- `security_risk`
- `random_budgeted`
- `rollout_joint`
- `oracle_sync`

但如果按论文写作口径来区分，通常可以这样理解：

### 4.1 经典/弱基线

- `full`
- `periodic`
- `aoi_only`
- `random_budgeted`

这些方法主要用于说明：

- 不考虑安全风险时会怎样
- 只用简单规则时会怎样
- 随机同步会有多差

### 4.2 更强的结构化基线

- `decoupled`
- `security_risk`
- `security_margin`

这些方法比简单周期法更强，因为它们已经考虑了孪生状态或安全信息，但仍然不如真正的前瞻联合控制完整。

### 4.3 主方法与上界参考

- 主方法：`rollout_joint`
- 参考上界：`oracle_sync`

也就是说，这个项目当前最核心的实验叙事是：

拿 `rollout_joint` 去和 `periodic / security_risk / security_margin / decoupled` 等方法比较，并用 `oracle_sync` 作为近似上界参考。

---

## 5. 当前项目进行到了哪个阶段

结合仓库中的最新文档和主表，项目目前大致处于：

`已完成方法原型 + 已完成论文级实验框架 + 已得到最新多场景主表，但仍处于论文打磨与证据加固阶段`

更具体地说，可以拆成下面几个阶段判断。

### 5.1 已经完成的阶段

#### A. 基础环境和 baseline 已经完成

这一部分是成熟的，项目已经具备完整可运行的 baseline 实验管线。

#### B. 三元耦合问题已经验证过

项目已经系统分析过：

- 周期同步和 outage 的关系
- twin quality 和 secrecy 的关系
- 不同同步策略下的 Pareto 关系

说明项目的核心问题定义已经站住了。

#### C. 安全感知同步策略已经做出来了

`security_risk` 和 `security_margin` 都已经不是概念，而是完整可运行的方法。

#### D. 主方法 `rollout_joint` 已完成一轮强化与一轮轻量化

现在的 `rollout_joint` 已经不再是简单的搜索原型，而是：

- 根节点保留 top candidate
- 后续采用 greedy tail rollout
- 使用缓存动作模板
- 引入风险/证书/孪生质量联合评分

这意味着它已经具备“可写成论文方法章节”的清晰结构。

#### E. 证书模型已经升级为 holdout 拟合版本

这是当前项目最重要的成熟信号之一。现在的证书模块不再只是启发式阈值，而是：

- 有训练/验证分离
- 有覆盖率评估
- 有可解释系数
- 能自动写回配置文件

#### F. 已经形成最新主表

`docs/final_main_tables.md` 已经给出 `paper_base / paper_hard / scenario_stress` 三个场景下、基于最新 holdout-fitted config 和多 seed 验证的主表结果。

这说明项目已经进入“论文结果整理阶段”，而不只是方法开发阶段。

### 5.2 当前最新结论

根据最新主表，当前项目的结论大致是：

#### A. `rollout_joint` 是当前主方法，整体最有竞争力

在 `paper_base` 和 `paper_hard` 中：

- `rollout_joint` 的平均 secrecy rate 是最强或接近最强
- 表现接近 `oracle_sync`
- 同步成本非常低

这说明项目的主方法是成立的。

#### B. `security_margin` 在高压力场景下有局部优势

在 `scenario_stress` 中：

- `security_margin` 的 outage 更优
- `rollout_joint` 并没有在所有目标上绝对统治

所以当前最合理的说法不是“主方法全方位碾压”，而是：

`rollout_joint` 是整体最强、最有论文价值的方法，但在不同目标和不同场景上仍存在 tradeoff。`

#### C. 证书覆盖率已经很强，但证书仍偏保守

当前 holdout 证书最大的优点是覆盖率高，缺点是 bound 仍然较松，因此：

- 它已经足够支撑论文叙事
- 但还不是一个非常紧的理论界

#### D. runtime 仍然是主要短板

规则法大约是几十 ms/slot，而 `rollout_joint` 仍然在数百 ms/slot 量级。

虽然轻量化后比之前接近 `1 s/slot` 的版本好很多，但 runtime 仍是论文中必须正面讨论的 tradeoff。

### 5.3 当前项目最准确的阶段定位

如果用论文准备阶段来描述，当前项目最像下面这个状态：

1. 研究问题已经明确
2. baseline 体系已经完整
3. 主方法已经成型
4. 主要结果已经跑出来
5. 证书线已经从“弱点”提升为“可 defend 的模块”
6. 现在离正式投稿还差“最终打磨”，而不是“从零到一做方法”

换句话说，项目已经不在早期探索期，而是在：

`论文可写、结果可讲、但还需要继续补强最终证据和叙事的中后期阶段。`

---

## 6. 当前最推荐的论文叙事

如果把这个项目写成论文，目前最顺的叙事应当是：

### 6.1 问题定义

数字孪生驱动 UAV 安全通信并不是“只优化轨迹”这么简单，而是要同时面对：

- 孪生老化
- 同步预算有限
- 同步时延和失败
- 安全通信目标

因此需要联合设计同步与控制。

### 6.2 方法设计

提出两条方法线：

- 一条是证书驱动的安全同步线：`security_margin`
- 一条是风险/证书感知的前瞻联合控制线：`rollout_joint`

其中 `rollout_joint` 是主方法，证书模型为方法提供可解释的风险约束信息。

### 6.3 实验结论

- 简单同步策略无法稳定处理复杂场景
- 仅靠规则法虽然快，但性能有限
- `rollout_joint` 在多数主场景中达到最优或接近最优 secrecy
- `oracle_sync` 说明主方法已接近可达到的上界
- 证书模型具备较高覆盖率，支撑鲁棒同步叙事
- 系统最终呈现的是性能-同步成本-runtime 三者之间的 tradeoff

---

## 7. 一段简短结论

这个项目已经完成了从“基础仿真搭建”到“论文级实验框架”的升级。它现在的核心贡献不只是做了几个 baseline，而是系统地把数字孪生老化、同步预算、安全证书和 UAV 联合控制放进了同一个可验证框架里。

当前最核心的方法是 `rollout_joint`，最主要的 baseline 是 `periodic`、`aoi_only`、`security_risk`、`security_margin`、`decoupled`，而 `oracle_sync` 用作近似上界参考。项目目前已经进入论文中后期整理阶段：主表已有、主方法已成型、证书线已较可信，但还需要继续加强 runtime 解释、多 seed 证据和最终论文表达。
