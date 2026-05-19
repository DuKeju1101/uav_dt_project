# Project Context

本文档用于项目交接和论文协作。它不是 README 的替代品，而是给自己、师兄或后续接手者快速了解“项目现在处在哪一步、最近改了什么、哪些结论不能写满”的上下文入口。

建议每次完成一轮较大的论文、实验或代码修改后，都更新本文档的“近期更新记录”和“当前审核重点”。

## 1. 项目一句话

本项目研究数字孪生状态会老化、同步预算有限、窃听者 Eve 会移动时，UAV 安全通信系统如何联合优化同步、轨迹、发射功率和干扰功率。

当前论文主方法是 `rollout_joint`：一个 empirical-risk-aware joint rollout controller。它使用数字孪生特征、secrecy-loss risk estimator 和有限时域前瞻评分，联合选择：

1. 是否同步以及同步带宽；
2. 两架 UAV 的运动；
3. source power；
4. jamming power；
5. 与 outage、twin quality、certificate slack 相关的风险项。

## 2. 当前论文状态

当前项目已经进入论文成稿和投稿前打磨阶段。

论文入口：

```bash
paper/main.tex
```

当前已编译 PDF：

```bash
paper/main.pdf
```

当前论文图目录：

```bash
paper/figures/
```

当前 paper-ready 结果目录：

```bash
results/final_2026-05-12/
```

当前优先引用的说明文档：

```bash
docs/final_results_2026-05-12.md
docs/publication_readiness_assessment_cn.md
docs/outage_threshold_calibration_2026-05-12.md
docs/rmin_sweep_protocol.md
```

## 3. 当前核心结论

主结论应写成：

1. `rollout_joint` 在三个主场景中稳定提高 average secrecy rate。
2. base 场景：secrecy-rate 小幅提升，outage 基本不变。
3. hard 场景：secrecy-rate 提升明显，outage 仍接近饱和，改善很小。
4. stress 场景：在校准的非饱和阈值 `R_min = 1.10` 下，secrecy-rate 提升且 outage 降低。
5. `R_min` sweep 表明 secrecy-rate gain 在测试阈值上较稳定，但 outage gain 只集中在非饱和阈值区间，不能写成对所有 outage target 都成立。

主表关键结果：

| scenario | secrecy gain vs periodic | outage gain vs periodic | 口径 |
| --- | ---: | ---: | --- |
| `paper_base_holdoutfit` | +0.0314 | 0.0000 | 只强调 secrecy-rate 小幅提升 |
| `paper_hard_holdoutfit` | +0.1626 | +0.0014 | 强调 secrecy-rate，outage 基本饱和 |
| `scenario_stress_holdoutfit` | +0.2683 | +0.2141 | 仅限校准非饱和阈值 `R_min = 1.10` |

`R_min` sweep 对 `rollout_joint` 相对 `periodic` 的结果：

| R_min | secrecy gain | outage gain | 解释 |
| ---: | ---: | ---: | --- |
| 0.6 | +0.2862 | +0.2853 | outage 改善明显 |
| 0.9 | +0.2760 | +0.3362 | outage 改善明显 |
| 1.1 | +0.2683 | +0.2141 | 校准阈值，仍有改善 |
| 1.4 | +0.2793 | -0.0006 | outage 优势消失 |
| 1.7 | +0.2791 | 0.0000 | outage 饱和 |
| 2.0 | +0.2767 | -0.0006 | outage 饱和 |
| 2.5 | +0.2717 | +0.0003 | outage 饱和 |

## 4. 不能写满的地方

这些是师兄审核时最容易抓到的问题，后续写论文、README 或 rebuttal 时要保持一致。

1. 不要写 `rollout_joint` 在所有场景都显著降低 outage。
   正确写法：`rollout_joint` 在 base/hard 主要提升 secrecy-rate；stress 的 outage 降低发生在校准的非饱和阈值区间。

2. 不要写 outage 改善是普适结论。
   正确写法：outage reduction is concentrated in the informative non-saturated threshold range。

3. 不要写 `R_min = 1.10` 是根据 `rollout_joint` 的中位表现调出来的。
   正确写法：`R_min = 1.10` comes from a pilot feasibility check / sweep and is treated as a feasible but non-trivial service target。

4. 不要把 holdout-fitted certificate 写成 universal safety guarantee。
   正确写法：它是 holdout-validated in-policy empirical secrecy-loss upper bound。

5. 不要把 PPO 结果写成否定所有 DRL 方法。
   正确写法：当前 PPO 是 200-episode lightweight diagnostic baseline。

6. 不要声称 `rollout_joint` 是低延迟方法。
   正确写法：它以更高 runtime 换取更好的 secrecy-rate 和 stress 非饱和阈值下更低 outage。

## 5. 最近关键更新记录

### 2026-05-19: Figure 1 替换与论文重编译

完成事项：

1. 论文 Figure 1 从旧的 `framework_control_loop.pdf` 替换为：

   ```bash
   paper/figures/dt_uav_joint_sync_secure_control_loop.pdf
   ```

2. Figure 1 caption 修改为 digital-twin-aware joint synchronization and secure control loop 版本。
3. `paper/main.pdf` 已重新编译。

相关文件：

```bash
paper/sections/01_introduction.tex
paper/main.pdf
```

### 2026-05-19: 删除旧框架图生成逻辑

完成事项：

1. 从 `paper/scripts/make_figures.py` 中删除 `plot_framework()`。
2. 删除脚本末尾对 `plot_framework()` 的调用。
3. 避免重新运行脚本时生成旧的 `framework_control_loop.pdf`。

相关文件：

```bash
paper/scripts/make_figures.py
```

### 2026-05-19: README 重新整理

完成事项：

1. README 从早期项目说明改为当前论文复现实验入口。
2. 补充当前主结果、配置、复现实验命令、论文编译命令、关键代码和写作边界。
3. 明确 `paper/scripts/make_figures.py` 不再生成 Figure 1。

相关文件：

```bash
README.md
```

### 2026-05-19: R_min 与 outage claim 口径修正

背景：

师兄指出 stress 场景中 outage gain 只在 `R_min <= 1.10` 的非饱和阈值区间明显，`R_min >= 1.40` 后基本消失。因此不能把 outage 改善写成普适结论。

完成事项：

1. 在论文 Introduction、System Model、Experiments、Discussion、Conclusion 中统一阈值限定口径。
2. 将 `R_min = 1.10` 解释为 pilot feasibility check 得到的 feasible but non-trivial service target。
3. 明确该阈值不是根据 `rollout_joint` 中位数或最优表现反推得到。
4. 在 `publication_readiness_assessment_cn.md` 和 `outage_threshold_calibration_2026-05-12.md` 中同步更新口径。
5. `paper/main.pdf` 已重新编译。

相关文件：

```bash
paper/main.tex
paper/sections/01_introduction.tex
paper/sections/03_system_model.tex
paper/sections/05_experiments.tex
paper/sections/06_discussion.tex
paper/sections/07_conclusion.tex
docs/publication_readiness_assessment_cn.md
docs/outage_threshold_calibration_2026-05-12.md
docs/rmin_sweep_protocol.md
configs/scenario_stress.yaml
README.md
paper/main.pdf
```

仍需注意：

```bash
docs/final_results_detailed_analysis_cn.md
docs/codex_desktop_paper_workflow_cn.md
```

这两个辅助文档中仍有少量旧式强口径表述，后续建议统一改成“校准非饱和阈值下 outage 改善”。

## 6. 代码演变记录

### 早期阶段

早期项目重点是构建纯 Python 仿真环境、baseline 和安全感知同步策略。核心模块包括：

```bash
env/
policies/
experiments/
analysis/
configs/
```

早期主要关注：

1. twin state update；
2. sync cost；
3. secrecy performance；
4. rule-based synchronization baseline；
5. threshold / coupling 实验。

### 当前阶段

当前代码已经服务于论文主线：

1. `env/simulator.py` 负责仿真推进、secrecy/outage 指标记录。
2. `policies/rollout_joint.py` 是主方法，实现联合前瞻控制。
3. `policies/sca_baseline.py` 提供 SCA baseline。
4. `policies/ppo_baseline.py` 提供 lightweight PPO diagnostic baseline。
5. `experiments/fit_certificate_holdout.py` 负责 holdout-fitted risk estimator。
6. `experiments/run_readiness_multiseed.py` 负责 20-seed 主表。
7. `experiments/run_rmin_sweep.py` 负责 stress threshold sweep。
8. `experiments/run_strengthening_suite.py` 负责 ablation / strengthening suite。
9. `paper/scripts/make_figures.py` 负责生成论文结果图，但不再生成 Figure 1。

## 7. 师兄审核建议流程

建议以后每轮修改都按下面流程对接。

### 修改前

1. 明确这轮修改目的，例如“修正 R_min/outage claim”或“替换 Figure 1”。
2. 新建一个独立分支。
3. 修改前记录当前论文 PDF 和结果目录是否已经是最新。

### 修改后

1. 更新代码或论文。
2. 重新编译论文：

   ```bash
   cd paper
   latexmk -pdf main.tex
   ```

3. 更新 `context.md` 的近期更新记录。
4. 用 `git diff` 检查改动。
5. 将修改推到 GitHub，开 Pull Request 给师兄审。

### 给师兄的 PR 描述建议

```md
## 修改目的
说明这轮修改解决什么问题。

## 主要修改
- 文件 1
- 文件 2
- 文件 3

## 审核重点
- claim 是否写满？
- 论文和 README/docs 是否一致？
- 图、表、caption 是否正确？
- 是否重新编译 main.pdf？

## 验证
- latexmk -pdf main.tex 成功
- 相关搜索已确认旧口径不再残留
```

## 8. 当前审核重点

如果师兄现在继续审核，建议重点看：

1. Abstract 是否需要补一句 calibrated non-saturated stress threshold。
   当前 abstract 已写 “outage reduction is concentrated in the non-saturated threshold range”，总体是稳的。

2. `05_experiments.tex` 是否已经足够清楚地区分 secrecy-rate gain 和 outage gain。
   当前实验章已明确写出 `R_min = 0.6, 0.9, 1.1` 有 outage gain，`R_min >= 1.4` 后基本消失。

3. `final_results_detailed_analysis_cn.md` 和 `codex_desktop_paper_workflow_cn.md` 是否要继续同步旧口径。
   这两个是辅助文档，不是论文正文，但为了长期协作，建议后续统一修改。

4. `paper/scripts/make_figures.py` 是否还会生成旧 Figure 1。
   当前已删除旧图生成逻辑。

## 9. 常用命令

查看当前改动：

```bash
git status --short
git diff --stat
```

搜索旧 outage claim 口径：

```bash
rg -n -F "同时提升 secrecy-rate 和降低 outage" README.md docs paper
rg -n -F "中位时隙保密速率" README.md docs paper
rg -n -F "R_min = 1.10" README.md docs paper
```

重新编译论文：

```bash
cd paper
latexmk -pdf main.tex
```

重新生成论文图：

```bash
python paper/scripts/make_figures.py --results-dir results/final_2026-05-12
```

注意：重新生成图不会生成 Figure 1。Figure 1 当前使用手动提供的：

```bash
paper/figures/dt_uav_joint_sync_secure_control_loop.pdf
```

## 10. 后续更新模板

以后每次有重要更新，可以在这里追加：

```md
### YYYY-MM-DD: 更新标题

背景：

- 为什么要改。

完成事项：

1. 改了什么。
2. 涉及哪些文件。
3. 是否重新编译论文。

审核重点：

- 希望师兄重点看什么。

遗留问题：

- 还有哪些需要后续处理。
```
