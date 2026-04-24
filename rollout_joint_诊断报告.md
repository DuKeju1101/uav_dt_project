# `rollout_joint` 性能下降诊断报告

> 日期：2026-04-23  
> 针对仓库：`uav_dt_project-main`（2026-04-22 版本）

---

## 1. 现象

本轮 Scheme C 大改之后，20-seed 主实验结果显示 `rollout_joint`（项目的核心主方法）在所有场景下 **secrecy rate 大幅低于简单基线**：

| 场景 | periodic | security_risk | rollout_joint |
|------|----------|---------------|---------------|
| paper_base | **1.6315** | 1.5096 | 0.9928 |
| paper_hard | 1.2948 | 1.2435 | 0.7872 |
| scenario_stress | **0.9887** | 0.9646 | 0.7775 |

`rollout_joint` 本应是项目最强的前瞻式联合优化方法，现在却被最简单的 `periodic`（固定周期同步）全面压制。

---

## 2. 直接原因：rollout_joint 从未同步

看 `avg_sync_cost_mean` 这一列：

| 方法 | avg_sync_cost |
|------|---------------|
| periodic | 0.1500 |
| security_risk | 0.0375 |
| risk_adaptive_hybrid_rollout | 0.1648 |
| **rollout_joint** | **0.0000** |

`rollout_joint` 的同步成本为 **0.0000**，意味着它在整个 120 步 episode 中 **一次同步都没有做**。

Twin 从第 0 步之后再也没有被更新过。Eve 的位置估计越来越偏，UAV 的移动和功率决策完全基于错误的 Eve 位置信息，导致真实 secrecy rate 大幅下降。

反观 `periodic` 每隔 7 步同步一次（sync_cost = 0.15 ≈ 120/7 × 0.75/120），twin 被定期校正，UAV 基于较准确的 Eve 估计做出合理决策。

---

## 3. 根因分析：信息回避效应（Information Avoidance）

### 3.1 评分机制回顾

`rollout_joint` 的决策核心是 `evaluate_candidate()`（`env/simulator.py` 第 297-408 行）。评分公式的主项为：

```
score = pred_metrics["r_sec"]                          ← 用 twin 估计的 Eve 位置算出
      - lambda_move * movement_cost
      - lambda_power * power_cost
      - lambda_sync * sync_cost                        ← 同步要扣分
      - lambda_outage * max(r_min - pred_r_sec, 0)     ← 也基于 twin 估计
      - lambda_certificate * effective_cert_penalty
      - lambda_badness * projected_badness
      + lambda_margin * max(pred_margin, 0)             ← 也基于 twin 估计
      + emergency_sync_bonus
      - 0.001 * projected_twin.aoi
```

**关键问题**：`pred_metrics["r_sec"]` 是基于 `projected_twin.eve_est`（twin 估计的 Eve 位置）计算的，而不是真实 Eve 位置。

### 3.2 悖论是怎么产生的

当 twin 过旧（AoI 很高）时：

**评估"不同步"的动作：**
1. Twin 不更新，`eve_est` 停留在旧位置（或按 Kalman 预测继续）
2. 旧的 Eve 估计位置可能恰好偏离 UAV-用户链路，使得 `pred_r_sec` **虚高**
3. Rollout 看到"不同步的分数很好"，选择不同步

**评估"同步"的动作：**
1. Twin 被校正到真实 Eve 位置附近
2. 真实 Eve 可能已经移动到对窃听更有利的位置
3. 校正后的 `pred_r_sec` **下降**（因为现实比幻想更差）
4. 同时还要扣 `lambda_sync * sync_cost = 0.03 × 0.75 = 0.0225`
5. Rollout 看到"同步后分数更低了"，不愿同步

**这就是"信息回避"**：rollout 宁可用错误但乐观的 twin 来维持高分，也不愿同步后面对现实。好比一个人不去体检——体检后"感觉更差了"，但不体检并不意味着真的健康。

### 3.3 现有惩罚项为什么没起作用

| 惩罚项 | 当前值 | 问题 |
|--------|--------|------|
| `lambda_badness` | 0.1 | 太弱。`badness` 最大为 1.0，惩罚仅 0.1，远不及虚高的 `pred_r_sec` 带来的"幻觉收益" |
| `lambda_certificate` | 0.2 | 被 `stress_relief` 机制削弱了（最多削减到 0.1 倍），实际惩罚可能不到 0.02 |
| `lambda_outage` | 0.75 | **也基于 twin 估计**。如果旧 twin 显示 `pred_r_sec > r_min`，outage penalty 为 0——但真实可能已经 outage 了 |
| AoI 正则化 | 0.001 × AoI | 即使 AoI=20，惩罚也只有 0.02，几乎可以忽略 |

总结：**所有惩罚项要么太弱，要么也依赖 twin 估计，无法打破信息回避的循环。**

### 3.4 为什么 hybrid 方法表现更好

`risk_adaptive_hybrid_rollout` 在 `paper_hard` 场景拿到了最高 secrecy（1.3901），sync_cost 为 0.1310。

原因：它在 `_hybrid_sync_gate()` 中有**硬性门控逻辑**——当 `badness` 高、`margin` 低、或到了周期性刷新时间点时，会直接 `force_sync`，绕过 rollout 的评分决策。

这说明**强制同步机制是有效的**，但当前只在 hybrid 变体里有，纯 `rollout_joint` 缺少这个保底。

---

## 4. 代码定位

需要修改的关键代码位置：

| 文件 | 行号 | 内容 |
|------|------|------|
| `env/simulator.py` | 297-408 | `evaluate_candidate()` 评分函数 — 核心修改点 |
| `env/simulator.py` | 395-397 | `pred_metrics["r_sec"]` 直接用于评分，无任何不确定性折扣 |
| `env/simulator.py` | 407 | AoI 正则化系数 0.001 太小 |
| `policies/rollout_joint.py` | 329-398 | `act()` 方法 — 添加 AoI 保底同步的位置 |
| `configs/paper_base.yaml` | 96-98 | `lambda_badness=0.1` 需要调大 |

---

## 5. 修复方案

### 方案 A：不确定性折扣（推荐，优先实现）

**原理**：twin 越旧，预测越不可信，应该给 `pred_r_sec` 打折扣。

**修改位置**：`env/simulator.py` 的 `evaluate_candidate()` 方法

**修改方式**：在计算最终 score 之前，对 `pred_metrics["r_sec"]` 施加折扣：

```python
# 在 score 计算之前加入（约第 394 行之前）
alpha_discount = float(self.cfg["control"].get("aoi_discount_alpha", 0.05))
aoi_discount = 1.0 / (1.0 + alpha_discount * projected_twin.aoi)
adjusted_r_sec = pred_metrics["r_sec"] * aoi_discount

# 然后把 score 公式中的 pred_metrics["r_sec"] 替换为 adjusted_r_sec
# 同时 outage_penalty 也应基于 adjusted_r_sec
outage_penalty = max(r_min - adjusted_r_sec, 0.0)
```

**参数建议**：`aoi_discount_alpha` 初始设为 0.05。当 AoI=10 时，折扣因子为 1/1.5 ≈ 0.67；AoI=20 时为 1/2 = 0.5。

**优点**：
- 直接打破信息回避循环
- 可解释性强，可以写进论文
- 只改一处代码

### 方案 B：大幅提高 twin 老化惩罚

**修改位置**：`configs/*.yaml` 中的超参数

**修改方式**：

```yaml
# 原值
lambda_badness: 0.1

# 建议调整为
lambda_badness: 0.5    # 甚至 0.8
```

同时将 AoI 正则化系数从 0.001 提高到 0.01-0.02（`simulator.py` 第 407 行）。

**优点**：改动最小，只改配置  
**缺点**：需要调参，且 badness 本身的计算也部分依赖 twin 估计

### 方案 C：信息价值奖励（Value of Information Bonus）

**原理**：同步动作应该获得额外奖励，因为它带来信息价值。

**修改位置**：`env/simulator.py` 的 `evaluate_candidate()` 方法

```python
# 在 score 计算时添加（约第 394 行）
lambda_voi = float(self.cfg["control"].get("lambda_voi", 0.3))
if do_sync:
    voi_bonus = lambda_voi * projected_badness * (1.0 + float(self.twin.aoi) / a_max)
    score += voi_bonus
```

**优点**：明确建模信息价值，论文叙事价值高  
**缺点**：新增超参数，需要调参

### 方案 D：AoI 保底同步（最快验证方案）

**原理**：当 AoI 超过阈值时，强制同步，不再依赖 rollout 评分。

**修改位置**：`policies/rollout_joint.py` 的 `act()` 方法

```python
# 在 act() 方法的 force_sync 逻辑中添加（约第 336 行之后）
max_aoi_before_force = int(self.cfg["control"].get("rollout_max_aoi", 8))
if int(obs.get("aoi", 0)) >= max_aoi_before_force and not force_nosync_only:
    force_sync_only = True
    forced_sync_reason = "rollout_aoi_floor"
```

**优点**：改动最小，10 分钟就能跑起来验证  
**缺点**：本质是退化为"规则 + rollout"的混合策略，不够优雅

---

## 6. 建议执行顺序

```
第 1 步（半天）
│  实施方案 D（AoI 保底同步）
│  跑 1 个 seed 的 paper_base 场景
│  确认 secrecy 是否回升到 1.3+ 以上
│
├── 如果回升 → 确认根因正确，继续第 2 步
└── 如果没有 → 需要进一步排查，联系师兄

第 2 步（1-2 天）
│  实施方案 A（不确定性折扣）+ 方案 B（调大 lambda_badness）
│  移除方案 D 的硬编码保底
│  跑 3 个 seed 的 paper_base 对比
│
├── 如果 rollout_joint 稳定超过 periodic → 进入第 3 步
└── 如果仍然偏低 → 调整 aoi_discount_alpha 和 lambda_badness

第 3 步（2-3 天）
│  完整 20-seed 三场景主实验
│  重新生成主表
│  验证 rollout_joint 是否在 paper_base 和 paper_hard 上稳定领先

第 4 步（可选）
│  加入方案 C（VOI bonus）做消融实验
│  对比有/无 VOI 的效果差异
│  这个对比本身可以作为论文的一节分析
```

---

## 7. 论文价值

这个 bug 反过来是一个很好的论文素材。建议在论文中加一节讨论：

> **The Information Avoidance Pitfall in Joint Optimization with Digital Twins**
>
> 当联合优化器同时控制同步决策和通信决策时，如果评分函数直接依赖 twin 估计而不考虑估计的不确定性，优化器会出现"信息回避"行为——回避同步以维持虚高的预测分数。
>
> 我们通过引入 AoI 感知的不确定性折扣（方案 A）和信息价值奖励（方案 C）解决了这一问题。消融实验表明，这两个修正分别贡献了 X% 和 Y% 的性能提升。

这比单纯展示"我的方法比 baseline 好"要有深度得多，也更容易打动审稿人。

---

## 8. 一句话总结

**`rollout_joint` 性能下降的根因不是方法框架有问题，而是评分函数存在"信息回避"缺陷——它用旧 twin 的虚高预测来回避同步的短期代价。修复方向是让评分函数意识到"预测越旧，可信度越低"。**
