# Digital-Twin-Aware Secure UAV Communication

本项目是一个纯 Python 仿真与论文复现实验仓库，研究数字孪生状态会老化、同步预算有限、窃听者移动且 UAV 需要联合控制轨迹/功率/干扰时，如何进行安全通信控制。

当前项目已经从早期 baseline 探索进入论文成稿阶段。主要结果、图表和论文草稿均已整理到 `results/final_2026-05-12/` 与 `paper/`。

## 当前状态

论文主线已经收束为：

1. 建模数字孪生感知的 secure UAV communication control loop。
2. 用 `rollout_joint` 联合同步、UAV 运动、source power 和 jamming power。
3. 用 holdout-fitted empirical secrecy-loss risk estimator 量化 twin 不确定性带来的保密损失风险。
4. 通过 20-seed 主实验、SCA/PPO baseline、消融实验、runtime 分析和 small MDP sanity check 支撑论文结论。

最新论文 PDF：

```bash
paper/main.pdf
```

最新结果说明：

```bash
docs/final_results_2026-05-12.md
docs/final_results_detailed_analysis_cn.md
docs/publication_readiness_assessment_cn.md
```

## 核心结论

最新主表位于：

```bash
results/final_2026-05-12/scheme_c_readiness_20seed/main_table.csv
```

20-seed 主实验中，`rollout_joint` 在三个主场景中均提高平均 secrecy-rate。校准后的 stress 场景不再是全 outage；在 `R_min = 1.10` 这个非饱和 QoS operating point 下，主方法同时提升 secrecy-rate 并降低 outage。`R_min` sweep 进一步说明：secrecy-rate gain 在测试阈值上较稳定，但 outage gain 主要集中在非饱和阈值区间，不能泛化为所有 outage target。

| 场景 | rollout_joint secrecy | periodic secrecy | secrecy 增益 | rollout_joint outage | periodic outage | outage 改善 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `paper_base_holdoutfit` | 1.6429 | 1.6115 | +0.0314 | 0.8913 | 0.8913 | 0.0000 |
| `paper_hard_holdoutfit` | 1.4429 | 1.2803 | +0.1626 | 0.9482 | 0.9496 | +0.0014 |
| `scenario_stress_holdoutfit` | 1.2540 | 0.9858 | +0.2683 | 0.4294 | 0.6434 | +0.2141 |

Holdout validation cover rate 高于 0.95 目标：

| split | 场景 | cover_rate |
| --- | --- | ---: |
| validation | `paper_base` | 0.9873 |
| validation | `paper_hard` | 1.0000 |
| validation | `scenario_stress` | 1.0000 |
| validation | all | 0.9964 |

需要注意：risk estimator / certificate 只能写成 holdout-validated in-policy empirical upper bound，不能写成任意未知环境下的严格安全保证。

## 目录结构

```text
uav_dt_project/
├─ configs/                 # Base, hard, stress and small-MDP scenario configs
├─ env/                     # Simulator, channel, twin, sync and mobility models
├─ policies/                # Rule-based, rollout, SCA and PPO policies
├─ experiments/             # Experiment runners and risk-estimator fitting scripts
├─ analysis/                # Metrics and plotting helpers
├─ results/
│  ├─ final_2026-05-12/     # Current paper-ready result set
│  └─ final_2026-05-06/     # Older historical result set
├─ paper/
│  ├─ main.tex              # Paper entry
│  ├─ main.pdf              # Compiled manuscript
│  ├─ sections/             # Paper sections
│  ├─ figures/              # Paper figures
│  └─ scripts/              # Figure generation script
├─ docs/                    # Chinese project notes and final result analyses
├─ requirements.txt
└─ README.md
```

## 环境安装

本项目当前不依赖 Gazebo、QGroundControl、ROS、相机链路或真机控制。实验全部在 Python 仿真器中运行。

```bash
cd ~/research/uav_dt_project
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

检查依赖：

```bash
python -c "import numpy, pandas, matplotlib, yaml; print('env ok')"
```

## 主要配置

当前论文使用的主场景：

```bash
configs/paper_base.yaml
configs/paper_hard.yaml
configs/scenario_stress.yaml
```

`scenario_stress.yaml` 的 outage threshold 已校准为 `channel.r_min = 1.10`。这个值应表述为来自 pilot feasibility sweep 的可行但非平凡服务阈值，用于避免旧版 `2.82` 造成 all-outage 退化；不要表述为根据 `rollout_joint` 的中位表现调出来的阈值。校准说明见：

```bash
docs/outage_threshold_calibration_2026-05-12.md
```

Small MDP sanity check 使用：

```bash
configs/small_mdp_bound_final.yaml
```

## 复现实验

### 1. Holdout risk estimator

项目已有最终输出：

```bash
results/final_2026-05-12/scheme_c_holdout/
```

如需重新拟合，可运行：

```bash
python -m experiments.fit_certificate_holdout \
  --train-configs configs/base.yaml configs/scenario_hard.yaml \
  --eval-configs configs/paper_base.yaml configs/paper_hard.yaml configs/scenario_stress.yaml \
  --train-methods periodic security_risk security_margin rollout_joint \
  --eval-methods periodic security_risk security_margin rollout_joint \
  --train-seeds 3 \
  --train-seed-start 0 \
  --eval-seeds 1 \
  --eval-seed-start 100 \
  --alpha 0.05 \
  --calibration-ratio 0.2 \
  --posthoc-calibration-ratio 0.5 \
  --posthoc-calibration-by-scenario \
  --outdir results/final_2026-05-12/scheme_c_holdout
```

### 2. 20-seed 主实验

项目已有最终输出：

```bash
results/final_2026-05-12/scheme_c_readiness_20seed/
```

如需重新跑主表：

```bash
python -m experiments.run_readiness_multiseed \
  --configs \
    results/final_2026-05-12/scheme_c_holdout/configs/paper_base_holdoutfit.yaml \
    results/final_2026-05-12/scheme_c_holdout/configs/paper_hard_holdoutfit.yaml \
    results/final_2026-05-12/scheme_c_holdout/configs/scenario_stress_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint \
  --num-seeds 20 \
  --seed-start 62 \
  --outdir results/final_2026-05-12/scheme_c_readiness_20seed
```

### 3. Stress baseline 和消融

统一 holdout-fitted 口径的 stress 补跑结果位于：

```bash
results/final_2026-05-12/sca_baselines_5seed_stress_holdoutfit/
results/final_2026-05-12/drl_ppo_200ep_5seed_stress_holdoutfit/
results/final_2026-05-12/strengthening_suite_3seed_stress_holdoutfit/
```

这些目录是论文主文优先引用的 baseline / ablation 结果。未带 `holdoutfit` 的 stress 结果主要作为诊断参考。

### 4. R_min sweep

R_min sweep 用于说明 stress threshold 附近的 secrecy-rate gain 和 outage gain，并证明 `R_min = 1.10` 不是唯一支撑点：

```bash
python -m experiments.run_rmin_sweep \
  --config results/final_2026-05-12/scheme_c_holdout/configs/scenario_stress_holdoutfit.yaml \
  --outdir results/final_2026-05-12/rmin_sweep_stress
```

详细协议见：

```bash
docs/rmin_sweep_protocol.md
```

## 生成论文图

论文图位于：

```bash
paper/figures/
```

生成脚本：

```bash
python paper/scripts/make_figures.py --results-dir results/final_2026-05-12
```

注意：当前 `paper/sections/01_introduction.tex` 使用的是人工替换后的框架图：

```bash
paper/figures/dt_uav_joint_sync_secure_control_loop.pdf
```

`paper/scripts/make_figures.py` 已不再生成 Figure 1，避免重新运行脚本时误生成旧版 `framework_control_loop.pdf`。

## 编译论文

本地编译：

```bash
cd paper
latexmk -pdf main.tex
```

若不用 `latexmk`，可按顺序运行：

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

编译说明见：

```bash
paper/README_compile_cn.md
```

## 关键代码

- `env/simulator.py`：核心仿真器，执行时隙推进、secrecy/outage 计算和指标记录。
- `env/twin.py`：数字孪生状态预测、同步更新、AoI 和不确定性维护。
- `env/sync.py`：同步策略和 secrecy-loss risk / certificate 相关计算。
- `policies/rollout_joint.py`：论文主方法，联合选择同步、运动、source power 和 jamming power。
- `policies/sca_baseline.py`：SCA baseline。
- `policies/ppo_baseline.py`：轻量 PPO diagnostic baseline。
- `experiments/fit_certificate_holdout.py`：holdout-fitted empirical risk estimator。
- `experiments/run_readiness_multiseed.py`：多 seed 主表。
- `experiments/run_sca_baselines.py`：SCA baseline。
- `experiments/run_drl_ppo_baseline.py`：PPO baseline。
- `experiments/run_strengthening_suite.py`：baseline 完整性和消融实验。
- `experiments/run_small_mdp_bound.py`：small exact-DP sanity check。

## 结果口径

当前论文应优先引用：

```bash
results/final_2026-05-12/
```

其中：

- `scheme_c_readiness_20seed/` 是主表。
- `scheme_c_holdout/` 是 risk estimator / certificate 拟合和验证结果。
- `sca_baselines_5seed_stress_holdoutfit/`、`drl_ppo_200ep_5seed_stress_holdoutfit/`、`strengthening_suite_3seed_stress_holdoutfit/` 是统一口径 stress baseline 和消融。
- `rmin_sweep_stress/` 是 threshold sweep，用于约束 outage claim 的适用范围。
- `small_mdp_bound/` 是 sanity check。

以下目录是旧结果或诊断结果，不能作为当前论文主口径：

```bash
results/final_2026-05-06/
results/final_2026-05-12/sca_baselines_5seed_stress/
results/final_2026-05-12/drl_ppo_200ep_5seed_stress/
results/final_2026-05-12/strengthening_suite_3seed_stress/
```

## 论文写作注意事项

建议论文贡献写成四点：

1. Digital-twin-aware secure UAV joint synchronization and control framework。
2. Empirical-risk-aware joint rollout controller。
3. Holdout-fitted secrecy-loss risk estimator。
4. Multi-seed validation with baselines, ablations, runtime analysis and small exact-DP sanity check。

需要主动承认的边界：

1. `rollout_joint` 运行时间较高，约 1.2 到 1.3 seconds/slot，适合 edge-assisted planning 或 moderate-timescale control，不应声称轻量实时。
2. Risk estimator 是 empirical / in-policy，不是 universal out-of-distribution safety guarantee。
3. PPO baseline 是 200-episode lightweight diagnostic，不代表所有 DRL 方法的上限。

## Git 状态建议

大型实验输出和 PDF 已纳入仓库，便于论文复现。若后续继续跑实验，建议新结果统一放入带日期的目录，例如：

```bash
results/final_YYYY-MM-DD/<experiment_name>/
```

不要把虚拟环境、Python 缓存或临时 IDE 文件提交到仓库。
