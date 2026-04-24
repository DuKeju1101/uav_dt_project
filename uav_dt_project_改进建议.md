# UAV_DT 项目改进建议清单

> 面向 `uav_dt_project` 当前版本，基于 20-seed 主表结果和代码评估整理。
> 核心判断：方向没问题，工程量足够，但**每个关键模块都选了最简单的建模**，导致每个模块都容易成为审稿人的靶子。如果关键模块各往上走一档，论文档次可以从 **Q4 稳 / Q3 勉强** 提升到 **Q3 稳 / Q2 可能冲**。

---

## 1. 改良项全表（按性价比排序）

| 优先级 | 改良项 | 现在是什么 | 改成什么 | 难度 | 论文增益 | 预计工作量 |
|---|---|---|---|---|---|---|
| ⭐⭐⭐ P0 | **Twin 状态估计** | 线性外推 + sigma 固定线性增长 | Kalman Filter（预测步 + 更新步） | 低 | 方法论升一档，彻底堵住"为什么 sigma 线性增长"的审稿意见 | 1-2 天 |
| ⭐⭐⭐ P0 | **Eve 建模** | 1 个 Eve，固定速度 + 高斯噪声 | 2-3 个 Eve，或 1 个 adaptive Eve（知道 UAV 策略并最优响应） | 中 | 堵住物理层安全论文最常见的审稿意见 | 3-5 天 |
| ⭐⭐⭐ P0 | **安全证书** | Ridge regression + 经验分位数 | Conformal Prediction（带 (1-α) 覆盖率保证） | 低 | 经验启发式 → 分布无关的统计保证，理论成色翻倍 | 2-3 天（有现成库 `mapie`） |
| ⭐⭐ P1 | **同步模型** | 二值（同步 / 不同步） | 连续带宽 b ∈ [0, B_max]，带宽越大测量方差越小 | 中 | 多一个 tradeoff 维度，论文故事更丰满 | 3-4 天 |
| ⭐⭐ P1 | **信道模型** | 纯路径损耗 (β₀/d^α) | 3GPP UAV 信道模型（概率 LoS/NLoS + 小尺度衰落） | 低 | 工程可信度立刻提升 | 1-2 天 |
| ⭐⭐ P1 | **动作空间** | 5 方向 + 2 档功率 = 324 个动作 | 8 方向 + 5 档功率，或连续动作 | 低 | 324 枚举不再 trivial，rollout 搜索才有意义 | 半天 |
| ⭐⭐ P1 | **理论上界** | `oracle_sync` 假设总能同步 | 小场景下用值迭代 / 整数规划算 MDP 最优解 | 中 | "达到理论最优的 X%" 比 "比 periodic 好 0.03" 强得多 | 4-5 天 |
| ⭐ P2 | **同步不完美** | 同步 = 完美拷贝真值 | 同步 = 带测量噪声的 Bayesian update | 低 | 证书不再是拟合确定性映射，是真正的不确定性传播 | 1 天 |
| ⭐ P2 | **预算模型** | 整个任务总共 N 次同步 | per-slot 能量约束 或 per-slot 带宽约束 | 中 | 和通信功率预算耦合，形成自然的联合优化 | 3 天 |
| ⭐ P2 | **性能指标** | Secrecy rate + outage | 加 secrecy energy efficiency 或 effective secrecy throughput | 低 | 多指标 tradeoff 分析更全面 | 半天 |
| ⭐ P2 | **超参调优** | 手调，每个场景一套数字 | CE 方法或 Bayesian optimization 自动调 | 中 | 堵住"阈值是否用 eval seed 调的"审稿意见 | 2-3 天 |
| ⭐ P2 | **真实数据** | 全合成仿真 | 加一个公开 UAV 轨迹数据集验证 | 中 | 工程可信度再升一档 | 2-3 天 |

---

## 2. 推荐组合方案

### 方案 A：只有 2 周时间（保底升格）

| 步骤 | 改良项 |
|---|---|
| 1 | P0-1 Kalman Filter |
| 2 | P0-3 Conformal Prediction |
| 3 | P1-6 动作空间扩大 |

**预计效果**：Q4 稳 → Q3 勉强冲

---

### 方案 B：有 1 个月时间（明显升格） ⭐ 推荐

| 步骤 | 改良项 |
|---|---|
| 1 | P0-1 Kalman Filter |
| 2 | P0-2 Adaptive Eve（只做 adaptive，不做 multi-Eve） |
| 3 | P0-3 Conformal Prediction |
| 4 | P1-5 LoS/NLoS 信道 |
| 5 | P1-7 理论上界（只对小场景） |

**预计效果**：Q3 稳 → Q2 可能冲

---

### 方案 C：有 2-3 个月时间（完全重做方法章节）

全部 P0 + 全部 P1，实验全部重跑。

**预计效果**：Q2 稳，有机会 Q1

---

## 3. 三个最关键 P0 改动的具体落地建议

### 3.1 Kalman Filter 替换 twin 的线性外推

**现有代码**（`env/twin.py`）的问题：
- `predict` 步只做了 `eve_est += eve_vel_est * delta_t`
- `sigma += sigma_growth`（固定常数）

**改法**：

```python
# 状态：[x, y, vx, vy]，用常速度模型 (CV model)
# P 是 4×4 协方差矩阵，不再是一个 scalar sigma

def predict(self, twin):
    F = np.array([[1, 0, dt, 0],
                  [0, 1, 0, dt],
                  [0, 0, 1, 0],
                  [0, 0, 0, 1]])
    Q = process_noise_covariance  # 过程噪声
    twin.state = F @ twin.state
    twin.P = F @ twin.P @ F.T + Q
    twin.aoi += 1

def sync(self, twin, eve):
    # 测量 z = H @ true_state + noise
    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
    R = measurement_noise_covariance
    z = eve.position + np.random.multivariate_normal([0, 0], R)
    y = z - H @ twin.state
    S = H @ twin.P @ H.T + R
    K = twin.P @ H.T @ np.linalg.inv(S)
    twin.state = twin.state + K @ y
    twin.P = (np.eye(4) - K @ H) @ twin.P
    twin.aoi = 0
```

**论文表述升级**：从 "我们维护一个启发式不确定性指标 sigma" → "我们用 Kalman Filter 维护 Eve 位置的后验分布"。

---

### 3.2 Conformal Prediction 替换经验证书

**现有代码**（`env/sync.py` 的 `empirical_secrecy_loss_upper_bound`）的问题：
- Ridge regression 拟合 realized_loss
- 取训练残差的 quantile 作为 safety buffer
- 没有覆盖率保证

**改法**：

```python
# 用 conformal prediction
# 库：mapie (https://github.com/scikit-learn-contrib/MAPIE)

from mapie.regression import MapieRegressor
from sklearn.linear_model import Ridge

# 训练阶段
base_model = Ridge(alpha=1e-6)
mapie = MapieRegressor(base_model, method="plus", cv=5)
mapie.fit(X_train, y_train)  # X 是特征 (aoi, pred_error_radius, sigma, ...)

# 推断阶段：给出 (1-alpha) 覆盖率的预测区间
y_pred, y_intervals = mapie.predict(X_test, alpha=0.05)
upper_bound = y_intervals[:, 1, 0]  # 95% 覆盖率的上界
```

**论文表述升级**：从 "我们的证书经验上覆盖率达到 0.995" → "我们的证书在 conformal prediction 框架下具有 (1-α) 的边际覆盖率保证"。

---

### 3.3 Adaptive Eve

**现有代码**（`env/entities.py` 的 `Eve.step`）的问题：
- Eve 只按固定速度 + 噪声运动
- Eve 对 UAV 的策略一无所知

**改法**：

```python
class AdaptiveEve(Eve):
    """
    Eve 知道 UAV 的当前位置和发射功率，朝着能最大化自己接收信号的方向移动。
    """
    def step(self, uav1_pos, uav2_pos, p_s, p_j, delta_t, rng):
        # 估计朝各个方向移动后的 r_e（窃听速率）
        best_direction = None
        best_r_e = -np.inf
        for direction in [..., 8 个方向]:
            candidate_pos = self.position + direction * self.max_speed * delta_t
            r_e = compute_eve_rate(candidate_pos, uav1_pos, uav2_pos, p_s, p_j)
            if r_e > best_r_e:
                best_r_e = r_e
                best_direction = direction
        self.position += best_direction * self.max_speed * delta_t
```

**论文表述升级**：从 "我们假设 Eve 按预定轨迹移动" → "我们在 adversarial setting 下评估，Eve 知道 UAV 策略并做最优响应"。

**注意**：adaptive Eve 会让所有方法的性能都变差，但只要 rollout_joint 降得比 periodic 少，故事就成立。

---

## 4. 必须同步做的几件事（否则审稿人会抓）

| 注意事项 | 原因 |
|---|---|
| 改完之后**所有场景重跑，不要只跑最容易赢的** | 现在 scenario_stress 场景差距 0.0017 << CI 0.0054，改完可能差距拉大，也可能反而缩小，都要诚实报告 |
| Train seed / tuning seed / eval seed 必须**三段分离** | 现在多个 `stress_fix / fix_v2` 结果目录看起来像用 eval seed 调过超参，会被审稿人抓 |
| 做**配对显著性检验**（paired t-test 或 Wilcoxon signed-rank） | 不做的话 reviewer 会直接说 "差距在误差范围内" |
| 准备回答 "如果 Eve 知道你的策略呢？" | 物理层安全论文的**必问题**，现在完全没答。做 Adaptive Eve 就是为了回答这个 |
| Runtime 从 25× 降到 5× 以内 | 当前 235 ms/slot 对实时控制不可接受，审稿人会质疑"UAV 控制能容忍这个延迟吗" |

### Runtime 降低的几个简单办法

1. Rollout 的 `evaluate_candidate` 里反复在算 `best_user_metrics` → 缓存
2. `clone_state / restore_state` 里深拷了很多 list → 改成只保存增量
3. `branching_limit` 从 12 降到 6-8，配合更好的 candidate ranking
4. 用 `numba` 或 `cython` 加速信道计算的热点

---

## 5. 优先级最明确的一句话

**如果只做 2 件事，就做 P0-1（Kalman）+ P0-3（Conformal）**。

这两个改完，论文方法章节的骨架立刻立起来，实现难度都不高，**两周内能搞定**。其他改良项都是在这个骨架上锦上添花。

---

## 6. 叙事建议（和技术改动同等重要）

无论做多少改动，**论文叙事必须从下面这个口径调整**：

❌ 不要说："我们的方法在所有场景下都更优"
❌ 不要说："rollout_joint 稳定领先"

✅ 要说的是："我们提出一个 DT-aware 的联合控制框架，在不同场景下呈现不同的性能-成本权衡，我们系统性地刻画了这个 tradeoff"

✅ 要主动写进论文的"短板"：
- scenario_stress 下差距在误差范围内 → 写成"stress 场景下证书触发的强制同步主导了性能，此时 rollout 搜索退化为 certificate rule"
- 25× runtime → 写成"我们提供了一个可调的性能-复杂度权衡，实际部署时可通过调整 horizon 和 branching 在两者之间取舍"

审稿人最讨厌的是"我什么都最好"，最喜欢的是"我诚实地指出了边界条件"。
