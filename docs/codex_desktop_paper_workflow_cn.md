# 使用 Codex 桌面端撰写 IJCS 论文的操作指南

本文是一份一步一步的使用文档，目标是帮助你用 Codex 桌面端基于当前项目、实验结果和 Wiley / International Journal of Communication Systems 的 LaTeX 模板撰写论文初稿。

适用场景：

1. 你已经下载了 International Journal of Communication Systems 的 LaTeX 模板。
2. 你已经有当前项目目录：`uav_dt_project`。
3. 项目里已经有实验结果、结果分析和论文可发表性评估文档。
4. 你希望让 Codex 桌面端帮你读取这些材料，生成 LaTeX 论文，并逐步修改到可投稿状态。

## 1. 先理解一件事：桌面端 Codex 不一定知道我们这段聊天

桌面端 Codex 和当前对话里的 Codex 不一定共享完整聊天记忆。

所以最稳妥的办法是：让桌面端 Codex 读取项目文件中的上下文。

目前最重要的上下文已经写进这些文件：

1. `docs/project_overview_cn.md`
2. `docs/final_results_2026-05-12.md`
3. `docs/final_results_detailed_analysis_cn.md`
4. `docs/publication_readiness_assessment_cn.md`
5. `docs/outage_threshold_calibration_2026-05-12.md`
6. `results/final_2026-05-12/`

你后面只要让桌面端 Codex 先读这些文件，它就能接上我们目前的工作。

## 2. 推荐的项目目录结构

建议在项目根目录下建立一个 `paper/` 目录，用来存放论文。

推荐结构如下：

```text
uav_dt_project/
  docs/
  results/
  experiments/
  paper/
    ijcs_template/
    main.tex
    refs.bib
    sections/
      01_introduction.tex
      02_related_work.tex
      03_system_model.tex
      04_method.tex
      05_experiments.tex
      06_discussion.tex
      07_conclusion.tex
    figures/
    tables/
    build/
```

其中：

- `paper/ijcs_template/`：放你从官网下载的 LaTeX 模板原文件。
- `paper/main.tex`：论文主文件。
- `paper/refs.bib`：参考文献 BibTeX 文件。
- `paper/sections/`：论文各章节。
- `paper/figures/`：后续放图。
- `paper/tables/`：后续放表。
- `paper/build/`：编译生成的临时文件，可有可无。

## 3. 第一步：把 IJCS 模板放进项目

你可以手动操作：

1. 打开文件管理器。
2. 找到你下载的 IJCS LaTeX 模板压缩包。
3. 解压。
4. 把解压后的模板文件夹复制到：

```text
/home/dkj/research/uav_dt_project/paper/ijcs_template/
```

如果 `paper/` 目录还不存在，你可以先创建。

当前已下载的 Wiley 官方 2026 模板包位于：

```text
paper/ijcs_template/
```

本次解压后的实际结构主要是：

```text
paper/ijcs_template/
  SOURCE.txt
  Author-guidelines for LaTex Template_Wiley (2026).pdf
  Optimal-Design-layout/
    Optimal-Design-layout.tex
    USG.cls
    wileyNJD-Chicago.bst
    wileyNJD-Chicago-lastoo.bst
    wileyNJD-Chicago.bib
    Fonts/
    images/
    *.sty
```

所以后面让 Codex 检查模板时，应重点查看 `Optimal-Design-layout/Optimal-Design-layout.tex` 和 `USG.cls`，而不是旧版 Wiley 模板里的 `WileyNJD-v2.cls`。

## 4. 第二步：打开桌面端 Codex

打开 Codex 桌面端后，务必确认它打开的是当前项目目录：

```text
/home/dkj/research/uav_dt_project
```

不要只打开 `paper/` 子目录。因为论文需要读取 `docs/`、`results/` 和 `experiments/` 里的内容。

如果桌面端让你选择 workspace / project folder，请选择：

```text
uav_dt_project
```

## 5. 第三步：给桌面端 Codex 的第一条提示词

打开桌面端 Codex 后，可以直接复制下面这段提示词。

```text
请先不要写论文。请先阅读以下文件，理解当前 UAV digital twin secure communication 项目的研究内容、实验结果和投稿目标：

1. docs/project_overview_cn.md
2. docs/final_results_2026-05-12.md
3. docs/final_results_detailed_analysis_cn.md
4. docs/publication_readiness_assessment_cn.md
5. docs/outage_threshold_calibration_2026-05-12.md

同时请浏览 results/final_2026-05-12/ 下的主要结果文件，尤其是：

1. scheme_c_readiness_20seed/main_table.csv
2. scheme_c_readiness_20seed/paired_comparisons_rollout_joint.csv
3. scheme_c_holdout/holdout_summary.csv
4. sca_baselines_5seed_stress_holdoutfit/main_table.csv
5. drl_ppo_200ep_5seed_stress_holdoutfit/main_table.csv
6. strengthening_suite_3seed_stress_holdoutfit/main_table.csv

阅读后请总结：

1. 论文的核心研究问题；
2. 论文可以收束成哪 4 个贡献点；
3. International Journal of Communication Systems 投稿时应采用什么叙事口径；
4. 还需要从 LaTeX 模板中确认哪些格式信息。

暂时不要修改文件。
```

这一步的目的：

- 让桌面端 Codex 先建立上下文。
- 避免它一上来乱写论文。
- 让它先告诉你它理解到什么。

## 6. 第四步：让 Codex 检查 LaTeX 模板

等它完成第一步总结后，继续给它这段提示词：

```text
请检查 paper/ijcs_template/ 中的 LaTeX 模板文件。

请告诉我：

1. 模板主 tex 文件是哪一个；
2. 使用的 documentclass 是什么；
3. bibliography 使用 BibTeX 还是 biblatex；
4. 参考文献样式文件是什么；
5. 图表、摘要、关键词、作者信息应该按照什么格式写；
6. 你建议我们基于模板复制出 paper/main.tex，还是直接改模板示例文件。

请先只分析，不要修改文件。
```

这一步很重要，因为不同 Wiley 模板可能略有差异。

不要让 Codex 还没看模板就凭空写 `main.tex`。

## 7. 第五步：让 Codex 创建论文目录和初稿文件

当 Codex 已经确认模板格式后，再让它创建论文文件。

提示词可以这样写：

```text
请基于 paper/ijcs_template/ 的 IJCS LaTeX 模板，创建论文初稿结构。

要求：

1. 不要删除模板原文件；
2. 在 paper/ 下创建或更新 main.tex；
3. 在 paper/sections/ 下创建以下章节：
   - 01_introduction.tex
   - 02_related_work.tex
   - 03_system_model.tex
   - 04_method.tex
   - 05_experiments.tex
   - 06_discussion.tex
   - 07_conclusion.tex
4. 创建 paper/refs.bib；
5. main.tex 使用 \input{} 引入各章节；
6. 论文题目暂定为：
   Digital-Twin-Aware Joint Synchronization and Control for Secure UAV Communication Systems
7. 作者、单位、邮箱先用占位符；
8. 先写英文论文初稿，目标期刊是 International Journal of Communication Systems；
9. 先不要追求完美语言，重点是结构完整、结果准确、能编译。

请完成文件创建，并告诉我修改了哪些文件。
```

这一步之后，项目里应该出现：

```text
paper/main.tex
paper/refs.bib
paper/sections/*.tex
```

## 8. 第六步：建议论文结构

建议桌面端 Codex 按下面结构写论文。

### 8.1 Title

推荐标题：

```text
Digital-Twin-Aware Joint Synchronization and Control for Secure UAV Communication Systems
```

备选标题：

```text
Holdout-Validated Digital Twin Synchronization for Secrecy-Aware UAV Communication Control
```

更偏 IJCS 的标题：

```text
A Digital-Twin-Aware Secure UAV Communication System With Joint Synchronization and Rollout Control
```

### 8.2 Abstract

摘要应包含：

1. UAV secure communication 的背景；
2. Eve 移动导致状态不确定；
3. 数字孪生同步有代价；
4. 提出 `rollout_joint`；
5. 提出 holdout-fitted secrecy-loss certificate；
6. 主要实验结果：
   - stress 场景 secrecy 提升 `+0.2683`
   - outage 改善 `+0.2141`
   - holdout validation cover rate 高于 0.95
7. 承认 runtime tradeoff。

### 8.3 Introduction

Introduction 建议分 5 段：

1. UAV communication 和安全通信背景；
2. Eve mobility 与 imperfect state awareness 的问题；
3. Digital twin synchronization 的机会与代价；
4. 现有方法不足：规则同步、局部优化、轻量 DRL 都没有联合处理同步、轨迹、功率和 certificate 风险；
5. 本文贡献。

贡献点建议写成四条：

1. Digital-twin-aware secure UAV communication framework；
2. Joint rollout controller；
3. Holdout-fitted empirical secrecy-loss certificate；
4. Multi-seed validation with baselines and ablations。

### 8.4 Related Work

Related Work 建议分 4 类：

1. UAV communication systems and FANETs；
2. Physical-layer security and secrecy outage；
3. UAV trajectory / resource allocation / anti-jamming；
4. Digital twins, state synchronization, and simulation-based evaluation。

可以参考这些 IJCS 论文：

1. `Network simulation tools for unmanned aerial vehicle communications: A survey`, DOI: `10.1002/dac.5878`
2. `Intelligent deep learning-aided future beam and proactive handoff prediction model in UAV-assisted anti-jamming Terahertz communication system`, DOI: `10.1002/dac.5504`
3. `ECaD: Energy-efficient routing in flying ad hoc networks`, DOI: `10.1002/dac.4156`
4. `A distributed fault-tolerant mechanism for mission-oriented unmanned aerial vehicle swarms`, DOI: `10.1002/dac.4789`
5. `Teredo tunneling-based secure transmission between UAVs and ground ad hoc networks`, DOI: `10.1002/dac.3144`
6. `Emerging ICT UAV applications and services: Design of surveillance UAVs`, DOI: `10.1002/dac.4023`

### 8.5 System Model

System Model 建议包含：

1. Network topology；
2. UAV、users、base station、Eve；
3. Time-slotted operation；
4. Communication and secrecy rate；
5. Digital twin state；
6. Synchronization model；
7. Outage definition；
8. Optimization objective。

要用通信系统语言写，不要写成单纯 Python 仿真说明。

### 8.6 Proposed Method

方法章节建议包含：

1. Baseline synchronization rules；
2. Secrecy-loss certificate；
3. Holdout fitting and validation；
4. Joint rollout control；
5. Computational complexity and runtime discussion。

这里要强调：

`rollout_joint` 同时决定：

- sync or not；
- sync bandwidth；
- UAV motion；
- source power；
- jamming power。

### 8.7 Experiments

实验章节建议包含：

1. Experimental setup；
2. Metrics；
3. Main 20-seed results；
4. Certificate validation；
5. SCA and PPO baselines；
6. Strengthening / ablation suite；
7. Small MDP sanity check；
8. Runtime analysis。

核心结果表应该优先引用：

```text
results/final_2026-05-12/scheme_c_readiness_20seed/main_table.csv
results/final_2026-05-12/scheme_c_holdout/holdout_summary.csv
results/final_2026-05-12/sca_baselines_5seed_stress_holdoutfit/main_table.csv
results/final_2026-05-12/drl_ppo_200ep_5seed_stress_holdoutfit/main_table.csv
results/final_2026-05-12/strengthening_suite_3seed_stress_holdoutfit/main_table.csv
results/final_2026-05-12/small_mdp_bound/summary.csv
```

### 8.8 Discussion

Discussion 必须主动写局限：

1. `rollout_joint` runtime 高；
2. certificate 是 holdout-validated in-policy upper bound；
3. PPO baseline 是 lightweight training budget；
4. small MDP sanity check 不直接作为主场景理论上界。

### 8.9 Conclusion

Conclusion 简洁总结：

1. 本文研究数字孪生不确定性下的 UAV 安全通信；
2. 提出 joint rollout + certificate；
3. 校准非饱和 stress 阈值下实现 secrecy-rate 提升与 outage 下降；
4. 后续工作是加速 rollout、增强 certificate 泛化、训练更强 DRL baseline。

## 9. 第七步：让 Codex 写 Introduction 和 Abstract

建议不要一次让它写完整论文。先写最重要的 Introduction 和 Abstract。

提示词：

```text
请先撰写 paper/sections/01_introduction.tex 和 main.tex 中的 abstract。

要求：

1. 目标期刊是 International Journal of Communication Systems；
2. 叙事重点是 communication systems，而不是单纯 UAV control；
3. Introduction 包含背景、挑战、现有方法不足、本文方法和贡献；
4. 贡献点收束成 4 条；
5. Abstract 中必须准确包含以下结果：
   - scenario_stress_holdoutfit 中 rollout_joint 相对 periodic 的 avg_secrecy_rate 提升 +0.2683；
   - outage 改善 +0.2141；
   - holdout validation cover rates are above 0.95；
6. 不要夸大 certificate，不要写 universal guarantee；
7. 不要写 PPO 方法本质无效，只写 lightweight PPO baseline under current training budget。

完成后请告诉我你写了哪些内容。
```

## 10. 第八步：写 Related Work

提示词：

```text
请撰写 paper/sections/02_related_work.tex，并更新 paper/refs.bib。

Related Work 分成四个小节：

1. UAV communication systems and FANETs；
2. Physical-layer security and secrecy outage；
3. UAV trajectory, resource allocation, and anti-jamming；
4. Digital twins, synchronization, and simulation-based evaluation。

请至少加入以下 IJCS 相关参考：

1. Network simulation tools for unmanned aerial vehicle communications: A survey, DOI 10.1002/dac.5878
2. Intelligent deep learning-aided future beam and proactive handoff prediction model in UAV-assisted anti-jamming Terahertz communication system, DOI 10.1002/dac.5504
3. ECaD: Energy-efficient routing in flying ad hoc networks, DOI 10.1002/dac.4156
4. A distributed fault-tolerant mechanism for mission-oriented unmanned aerial vehicle swarms, DOI 10.1002/dac.4789
5. Teredo tunneling-based secure transmission between UAVs and ground ad hoc networks, DOI 10.1002/dac.3144

如果你不能确认完整 BibTeX，请先写尽可能准确的 BibTeX 条目，并标注 TODO: verify metadata。
```

注意：如果 Codex 要联网查 BibTeX，可能需要你授权网络访问。

## 11. 第九步：写 System Model 和 Method

提示词：

```text
请撰写 paper/sections/03_system_model.tex 和 paper/sections/04_method.tex。

请根据 docs/project_overview_cn.md、docs/final_results_detailed_analysis_cn.md 和代码中的 env/、policies/、experiments/ 内容来写。

要求：

1. 用论文语言描述系统模型，不要写成代码说明；
2. 定义 UAV、Eve、users、digital twin、sync budget、secrecy rate、outage；
3. 描述 certificate 是 empirical secrecy-loss upper bound；
4. 描述 holdout fitting 的 train/validation 思路；
5. 描述 rollout_joint 如何联合选择 sync、bandwidth、movement、power、jamming；
6. 加一个 complexity/running time discussion 小节；
7. 不要声称严格全局最优。
```

这一部分很容易写得过度，所以要重点检查：

- 是否夸大理论保证；
- 是否把仿真实现误写成闭式理论；
- 是否把 `rollout_joint` 写成最优算法。

## 12. 第十步：写 Experiments

提示词：

```text
请撰写 paper/sections/05_experiments.tex。

请基于以下结果文件生成实验分析和 LaTeX 表格：

1. results/final_2026-05-12/scheme_c_readiness_20seed/main_table.csv
2. results/final_2026-05-12/scheme_c_readiness_20seed/paired_comparisons_rollout_joint.csv
3. results/final_2026-05-12/scheme_c_holdout/holdout_summary.csv
4. results/final_2026-05-12/sca_baselines_5seed_stress_holdoutfit/main_table.csv
5. results/final_2026-05-12/drl_ppo_200ep_5seed_stress_holdoutfit/main_table.csv
6. results/final_2026-05-12/strengthening_suite_3seed_stress_holdoutfit/main_table.csv
7. results/final_2026-05-12/small_mdp_bound/summary.csv

要求：

1. 先解释指标含义；
2. 主表突出三个场景的 secrecy 和 outage；
3. stress holdoutfit baseline 使用统一口径结果；
4. 配对统计只简洁汇报，不要堆满所有 p-value；
5. runtime tradeoff 必须写；
6. small MDP 只作为 sanity check，不直接与主场景数值比较。
```

建议论文里不要放太多大表。主文可以放：

1. Main 20-seed table；
2. Holdout certificate table；
3. Stress holdoutfit baselines table；
4. Strengthening suite table；
5. Runtime table，或者把 runtime 合并在主表里。

## 13. 第十一步：写 Discussion 和 Conclusion

提示词：

```text
请撰写 paper/sections/06_discussion.tex 和 paper/sections/07_conclusion.tex。

Discussion 必须包含：

1. why rollout_joint improves secrecy and outage；
2. computational cost tradeoff；
3. empirical/in-policy nature of the certificate；
4. limitation of lightweight PPO baseline；
5. future work。

Conclusion 要简洁，避免重复实验细节。
```

## 14. 第十二步：编译 LaTeX

如果你的系统安装了 `latexmk`，可以让 Codex 运行：

```bash
cd paper
latexmk -pdf main.tex
```

如果模板需要 XeLaTeX：

```bash
cd paper
latexmk -xelatex main.tex
```

如果没有 `latexmk`，可以试：

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

如果使用 `biblatex`，可能是：

```bash
cd paper
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

具体用哪个，要看模板。

给 Codex 的提示词：

```text
请尝试编译 paper/main.tex。

如果编译失败，请读取报错信息并修复 LaTeX 问题。

要求：

1. 不要删除正文内容；
2. 优先修复缺包、引用、表格过宽、特殊字符、BibTeX 格式问题；
3. 每次修复后重新编译；
4. 最终告诉我 PDF 是否生成成功，以及还有哪些 warning。
```

## 15. 第十三步：人工检查清单

PDF 生成后，你需要人工检查：

### 15.1 题目

是否像 communication systems 论文，而不是纯控制论文。

### 15.2 摘要

是否包含：

- 研究问题；
- 方法；
- certificate；
- 关键结果；
- 不夸大。

### 15.3 贡献点

是否只有 3 到 4 条，且每条清楚。

### 15.4 实验表格

检查数值是否和这些文档一致：

- `docs/final_results_2026-05-12.md`
- `docs/final_results_detailed_analysis_cn.md`
- `docs/publication_readiness_assessment_cn.md`

### 15.5 局限性

必须写：

- runtime 高；
- certificate 是 empirical / in-policy；
- PPO baseline 训练预算有限；
- small MDP 是 sanity check。

### 15.6 引用

检查：

- 引用是否都在正文出现；
- BibTeX 是否编译；
- 是否引用了 IJCS 相关论文；
- 是否有明显乱编的文献。

## 16. 第十四步：让 Codex 做语言润色

论文初稿编译成功后，再让 Codex 逐节润色。

不要一次要求“润色全文”，容易改坏逻辑。建议逐节来：

```text
请润色 paper/sections/01_introduction.tex。

要求：

1. 保持技术含义不变；
2. 不要修改实验数值；
3. 语言更符合 International Journal of Communication Systems；
4. 避免夸大；
5. 输出修改后的文件，并总结主要修改。
```

按顺序润色：

1. Introduction；
2. Related Work；
3. System Model；
4. Method；
5. Experiments；
6. Discussion；
7. Conclusion。

## 17. 第十五步：让 Codex 做投稿前审稿人视角检查

最后可以让 Codex 扮演审稿人。

提示词：

```text
请以 International Journal of Communication Systems 审稿人的角度审查 paper/main.tex。

请重点检查：

1. scope 是否贴合 IJCS；
2. contribution 是否清楚；
3. method 是否有足够新意；
4. experiment 是否支撑 claims；
5. 是否存在过度声称；
6. baseline 是否合理；
7. runtime limitation 是否写清楚；
8. certificate limitation 是否写清楚；
9. 哪些地方最可能被审稿人质疑。

请先给审稿意见，不要直接修改文件。
```

拿到审稿意见后，再逐条让它修改。

## 18. 常见问题

### 18.1 Codex 找不到模板怎么办

确认模板是否真的在：

```text
paper/ijcs_template/
```

并告诉 Codex 具体路径。

### 18.2 Codex 编译失败怎么办

让它读取 `.log` 文件。

提示词：

```text
请读取 paper/main.log，定位 LaTeX 编译失败原因，并修复。
```

### 18.3 参考文献不完整怎么办

可以先保留 TODO，然后后续用 Google Scholar / Crossref / Wiley 页面补全。

提示词：

```text
请检查 paper/refs.bib 中所有 TODO: verify metadata 的条目，并告诉我哪些需要人工核对。
```

### 18.4 表格太宽怎么办

让 Codex 改成：

- `table*`
- `resizebox{\textwidth}{!}{...}`
- 缩短列名
- 拆成两个表

提示词：

```text
实验表格太宽，请在不改变数值的前提下优化 LaTeX 表格排版。
```

### 18.5 论文太像项目报告怎么办

让 Codex 按 IJCS 口径重写。

提示词：

```text
请把当前论文叙事从项目报告风格改成通信系统论文风格。重点突出 communication system model, secrecy outage, synchronization-control tradeoff, performance evaluation。
```

## 19. 最推荐的完整执行顺序

你可以按下面顺序一步一步做：

1. 把 IJCS 模板放到 `paper/ijcs_template/`。
2. 打开桌面端 Codex，选择项目根目录 `uav_dt_project`。
3. 让 Codex 先读 `docs/` 和 `results/`，不要写文件。
4. 让 Codex 检查 LaTeX 模板。
5. 让 Codex 创建 `paper/main.tex`、`sections/`、`refs.bib`。
6. 先写 Abstract 和 Introduction。
7. 写 Related Work，并补 BibTeX。
8. 写 System Model 和 Method。
9. 写 Experiments。
10. 写 Discussion 和 Conclusion。
11. 编译 LaTeX。
12. 修复编译错误。
13. 逐节润色。
14. 做审稿人视角检查。
15. 根据检查意见修改。
16. 最后人工核查数值、引用、图表和投稿格式。

## 20. 一段可以直接给桌面端 Codex 的总启动提示词

如果你想简单一点，可以直接复制下面这段作为桌面端 Codex 的第一条任务：

```text
我正在准备向 International Journal of Communication Systems 投稿一篇论文。请基于当前项目撰写 LaTeX 论文初稿。

请先阅读以下上下文文件：

1. docs/project_overview_cn.md
2. docs/final_results_2026-05-12.md
3. docs/final_results_detailed_analysis_cn.md
4. docs/publication_readiness_assessment_cn.md
5. docs/outage_threshold_calibration_2026-05-12.md

并浏览 results/final_2026-05-12/ 下的关键结果。

我已经把 IJCS LaTeX 模板放在 paper/ijcs_template/。

请按以下顺序执行：

1. 先总结你对项目、实验结果、论文贡献和 IJCS 投稿口径的理解；
2. 检查 paper/ijcs_template/ 的模板结构；
3. 等我确认后，再创建 paper/main.tex、paper/refs.bib 和 paper/sections/；
4. 使用英文撰写论文初稿；
5. 论文题目暂定为 Digital-Twin-Aware Joint Synchronization and Control for Secure UAV Communication Systems；
6. 论文必须准确引用最终结果，不要夸大 certificate，不要声称 PPO 方法本质无效；
7. 最后尝试编译 LaTeX 并修复错误。

第一步请只阅读和总结，不要修改文件。
```

## 21. 最后提醒

Codex 可以帮你极大加快论文写作，但最终投稿前你仍然要人工确认：

1. 作者、单位、基金、伦理声明是否正确；
2. 所有实验数值是否准确；
3. 所有引用是否真实存在；
4. 是否符合 IJCS 的 Author Guidelines；
5. 是否符合导师和学校对期刊、版面费、署名和查重的要求。

尤其是参考文献，不能完全依赖自动生成，必须人工核对 DOI、作者、年份和期刊名。
