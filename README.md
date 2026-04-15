# 安全感知事件触发同步下的数字孪生驱动 UAV 网络安全通信与轨迹协同优化

本项目是一个**纯 Python、纯仿真**的小规模实验框架，严格围绕以下 3 个当前阶段目标：

1. 场景与 baseline 搭建
2. sync cost、twin quality、secrecy performance 三元耦合基础实验
3. 安全感知事件触发阈值设计

> 当前阶段**不依赖 Gazebo、QGroundControl、ROS、相机链路、真机控制**。
> 你已经安装了 Gazebo/QGC，但在本阶段它们只是“已具备的软件环境”，暂时**不参与实验执行**。

---

## 1. 目录结构

```text
uav_dt_project/
├─ configs/
│  └─ base.yaml
├─ env/
│  ├─ __init__.py
│  ├─ entities.py
│  ├─ mobility.py
│  ├─ channel.py
│  ├─ twin.py
│  ├─ sync.py
│  └─ simulator.py
├─ policies/
│  ├─ __init__.py
│  ├─ greedy_joint.py
│  └─ decoupled.py
├─ experiments/
│  ├─ common.py
│  ├─ run_baselines.py
│  ├─ run_coupling.py
│  └─ run_threshold.py
├─ analysis/
│  ├─ metrics.py
│  └─ plotter.py
├─ results/
├─ requirements.txt
└─ README.md
```

---

## 2. 环境说明

### 2.1 最小仿真场景
- 1 个 BS / 边缘服务器
- 2 架合法 UAV
  - UAV-1：主服务 UAV
  - UAV-2：干扰 UAV（jammer）
- 1 个 Eve
- 3 个地面用户
- 2D 平面，固定高度
- 离散时隙系统

### 2.2 核心思路
- **真实状态**：用于计算真实 secrecy performance
- **twin 状态**：用于做同步判断和控制决策
- **同步动作**：决定是否刷新 twin
- **控制动作**：决定 UAV 轨迹与功率

### 2.3 当前提供的同步策略
- `full`
- `periodic`
- `aoi_only`
- `security_risk`
- `security_margin`
- `decoupled`

---

## 3. 在 WSL Ubuntu 中搭建运行环境

下面步骤都在 **Ubuntu(W Sl)** 终端中执行。

### Step 1：进入自己的工作目录

```bash
cd ~
mkdir -p research
cd research
```

### Step 2：把项目文件放进该目录

假设你已经把整个 `uav_dt_project` 文件夹复制到这里。

检查：

```bash
ls
```

应该能看到：

```bash
uav_dt_project
```

### Step 3：进入项目目录

```bash
cd ~/research/uav_dt_project
pwd
```

### Step 4：创建 Python 虚拟环境

```bash
python3 -m venv .venv
```

如果报错 `ensurepip is not available`，执行：

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
```

### Step 5：激活虚拟环境

```bash
source .venv/bin/activate
```

激活后终端前面通常会出现：

```bash
(.venv)
```

### Step 6：安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 7：检查依赖安装是否成功

```bash
python -c "import numpy, pandas, matplotlib, yaml; print('env ok')"
```

如果看到：

```bash
env ok
```

说明环境正常。

---

## 4. 用 VS Code 远程打开项目

你已经能用 VS Code 连接 WSL，所以直接按下面做：

### Step 1：在 WSL 终端进入项目目录

```bash
cd ~/research/uav_dt_project
```

### Step 2：用 VS Code 打开当前目录

```bash
code .
```

### Step 3：检查 VS Code 左下角
你应该看到远程环境类似：
- `WSL: Ubuntu`

### Step 4：在 VS Code 终端中激活环境
打开 VS Code 内置终端，执行：

```bash
source .venv/bin/activate
```

---

## 5. 第一次运行：先做 baseline

### Step 1：确认当前目录正确

```bash
cd ~/research/uav_dt_project
source .venv/bin/activate
```

### Step 2：先做冒烟测试（推荐先跑这个）

```bash
python -m experiments.run_baselines --config configs/smoke.yaml --outdir results/baselines_smoke
```

### Step 3：再跑正式 baseline

```bash
python -m experiments.run_baselines
```

### Step 4：查看输出目录

```bash
ls results/baselines
```

你应当能看到：
- 每个方法、每个 seed 的逐时隙 csv
- `summary_all_methods.csv`
- `summary_agg_methods.csv`

### Step 5：查看汇总结果

```bash
python - <<'PY'
import pandas as pd

df = pd.read_csv('results/baselines/summary_agg_methods.csv')
print(df)
PY
```

---

## 6. 第二次运行：三元耦合实验

### Step 1：先跑 quick 版本 coupling

```bash
python -m experiments.run_coupling --config configs/smoke.yaml --quick --outdir results/coupling_quick
```

### Step 2：再跑正式 coupling

```bash
python -m experiments.run_coupling
```

### Step 3：查看结果目录

```bash
ls results/coupling
```

你应当看到：
- `coupling_summary.csv`
- `coupling_summary_agg.csv`
- `cliff_effect.png`
- `periodic_vs_twin_quality.png`
- `periodic_vs_outage.png`
- `q_vs_rs.png`
- `pareto_sync_vs_secrecy.png`
- `tfscc.csv`
- `tfscc_vs_eve_speed.png`

### Step 4：打开图片
在 WSL 中可以先用 VS Code 文件浏览器直接点开。

---

## 7. 第三次运行：安全感知阈值实验

### Step 1：运行 threshold 扫描

```bash
python -m experiments.run_threshold
```

### Step 3：查看结果目录

```bash
ls results/threshold
```

你应当看到：
- `threshold_summary.csv`
- `threshold_summary_agg.csv`
- `threshold_vs_secrecy.png`
- `threshold_vs_outage.png`
- `threshold_pareto.png`

---

## 8. 你应该如何理解这些代码文件

### `env/simulator.py`
核心环境文件。

负责：
- 维护 UAV、Eve、Twin 状态
- 执行一步 `step()`
- 计算真实 secrecy rate 和 twin quality
- 记录实验日志

### `env/twin.py`
Twin 更新逻辑。

负责：
- 初始化 twin
- 同步时刷新 twin
- 不同步时按运动模型预测 twin
- 维护 AoI 和不确定性

### `env/sync.py`
同步策略定义。

负责：
- Full Sync
- Periodic Sync
- AoI-only Trigger
- Security Risk Trigger
- Security Margin Trigger

### `policies/greedy_joint.py`
当前阶段的联合控制器。

负责：
- 枚举 UAV 轨迹动作 + 功率动作
- 基于 twin 预测 secrecy rate
- 选择当前时隙的最佳动作

### `policies/decoupled.py`
解耦 baseline。

负责：
- 先固定同步规则
- 再单独优化轨迹与功率

### `experiments/run_baselines.py`
跑各个 baseline。

### `experiments/run_coupling.py`
跑三元耦合实验。

### `experiments/run_threshold.py`
跑阈值设计对比实验。

---

## 9. 如何修改关键参数

所有主要参数都在：

```text
configs/base.yaml
```

### 9.1 修改 episode 长度

```yaml
episode_length: 200
```

### 9.2 修改同步预算

```yaml
sync:
  budget: 80
```

### 9.3 修改 periodic baseline 周期

```yaml
sync:
  periodic_k: 4
```

### 9.4 修改 AoI 阈值

```yaml
sync:
  aoi_threshold: 6
```

### 9.5 修改安全感知阈值

```yaml
sync:
  tau0: 0.52
  rho: 0.05
```

### 9.6 修改 Eve 运动速度

```yaml
eve:
  velocity: [-2.0, -1.0]
```

### 9.7 修改轨迹步长

```yaml
control:
  step_size: 10.0
```

---

## 10. 推荐你的实际实验顺序

### 第 1 阶段：只跑 baseline
按顺序跑：

```bash
python -m experiments.run_baselines
```

看：
- Full Sync 是否最好
- Periodic / AoI-only 是否明显下降
- Decoupled 是否弱于 Joint

### 第 2 阶段：跑三元耦合

```bash
python -m experiments.run_coupling
```

重点看：
- 是否出现 cliff effect
- Twin quality 下降时 secrecy rate 是否快速恶化
- TFSCC 是否随 Eve 速度变大

### 第 3 阶段：跑阈值设计

```bash
python -m experiments.run_threshold
```

重点看：
- Security-aware 是否优于 AoI-only
- 在近似 sync cost 下，是否能降低 outage

---

## 11. Gazebo 和 QGroundControl 在这里如何处理

你已经装好了 Gazebo 和 QGroundControl，但**当前阶段不要接入**。

原因：
- 你当前题目是 **安全感知事件触发同步 + 数字孪生 + 安全通信 + 轨迹协同优化**
- 当前阶段目标是 **纯仿真 baseline、三元耦合、阈值设计**
- Gazebo/QGC/ROS/视觉链路会显著增加工程复杂度，但对当前论文主线没有直接收益

因此建议：
- **保留 Gazebo/QGC 安装状态即可**
- **本阶段所有实验只在 Python 项目里完成**

---

## 12. 在 VS Code 中如何使用 Codex（建议工作流）

### 推荐工作流 A：用 Codex 生成局部改动
适合：
- 补参数扫描
- 加新图
- 改 reward
- 增加一个 baseline

建议你在打开本项目后，对 Codex 下这样的任务：

```text
阅读当前项目结构。
不要改动核心场景设定。
请在 experiments/run_threshold.py 中新增一个对 sigma_growth 的扫描实验，
并把结果保存到 results/threshold_sigma/ 下。
要求保持现有代码风格。
```

### 推荐工作流 B：用 Codex 做代码审查
适合：
- 检查逻辑错误
- 看是否有重复代码
- 补类型注解

示例提示词：

```text
请审查当前项目，重点检查：
1. twin 状态更新是否自洽；
2. security_margin 阈值是否真的比 AoI-only 更有针对性；
3. 是否有可提取的公共函数。
不要大改结构，只给出最小修改方案并直接修改代码。
```

### 推荐工作流 C：用 Codex 生成单个新增模块
适合：
- 加 trajectory 可视化
- 加灵敏度分析
- 加结果汇总脚本

示例提示词：

```text
请新增 analysis/trajectory_plot.py。
功能：读取 results/baselines/slot_security_margin_seed*.csv，
画出 UAV-1、UAV-2、Eve 的二维轨迹图。
输出到 results/plots/trajectory_security_margin.png。
不要修改其他文件。
```

### 不推荐你现在让 Codex 做的事
- 不要让它一次性大改所有文件
- 不要直接让它把系统扩展到 ROS/Gazebo
- 不要让它自行发散到真实无人机控制
- 不要让它同时改环境、策略、实验、画图所有模块

建议你始终采用：
- **一次只下一个清晰任务**
- **先看 diff，再接受修改**
- **先让它改小文件，再改核心文件**

---

## 13. 常见问题排查

### 问题 1：`No module named experiments`
在项目根目录运行：

```bash
cd ~/research/uav_dt_project
python -m experiments.run_baselines
```

不要在 `experiments/` 子目录里直接运行。

### 问题 2：matplotlib 无法显示图片
这是正常的，因为脚本默认是保存 png，不是弹窗显示。

直接去 `results/...` 目录查看图片文件即可。

### 问题 3：运行太慢
先把 `configs/base.yaml` 里的：

```yaml
num_seeds: 10
episode_length: 200
```

改小成：

```yaml
num_seeds: 3
episode_length: 80
```

先跑通，再恢复。

### 问题 4：想固定 Eve 不动
把：

```yaml
eve:
  velocity: [0.0, 0.0]
```

---

## 14. 你的下一步建议

你现在最稳的实际操作顺序是：

1. 在 WSL 中创建 venv 并安装依赖
2. 用 VS Code Remote 打开项目
3. 先运行 `python -m experiments.run_baselines`
4. 看 `results/baselines/summary_agg_methods.csv`
5. 再运行 `python -m experiments.run_coupling`
6. 再运行 `python -m experiments.run_threshold`
7. 最后再考虑让 Codex 帮你做“局部增强”而不是“整体重写”

只要你先把这 3 类实验跑通，项目就已经从“方案阶段”进入“可验证实验阶段”了。
