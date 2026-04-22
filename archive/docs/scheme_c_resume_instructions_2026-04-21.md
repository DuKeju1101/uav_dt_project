# 方案 C 实验补跑说明（2026-04-21）

## 1. 这份文档的用途

这份文档用于在明天继续处理 `scheme_c` 实验时，快速恢复上下文并避免重复重跑已经完成的步骤。

如果明天把这份文档发给 Codex，目标应当是：

1. 先核对当前结果状态是否与本文档一致。
2. 只补跑最后未完成的步骤。
3. 不要从头重跑整条 `scheme_c` 流水线。

## 2. 当前结论

截至 2026-04-21 晚上，本次 `scheme_c` 实验不在运行中，且主实验的前两步已经完成落盘。

结论如下：

1. 当前没有相关实验进程在跑。
2. `holdout` 结果已经完成。
3. `20-seed readiness` 结果已经完成。
4. 未完成的是最后两步：
   `small_mdp_bound` 和最终结果文档覆盖写入。
5. 因此，明天应当补跑最后两步，而不是整套实验从头开始。

## 3. 当时的判断依据

### 3.1 进程状态

检查时没有发现相关 Python 实验进程，说明 VSCode 关闭后并没有遗留后台任务继续运行。

### 3.2 已完成的结果

以下目录已经存在且有完整输出：

1. `results/scheme_c_holdout/`
2. `results/scheme_c_readiness_20seed/`

其中：

1. `results/scheme_c_holdout/holdout_summary.csv` 已存在。
2. `results/scheme_c_readiness_20seed/all_runs.csv` 已存在，且共有 `300` 条记录。
3. 这 `300` 条记录正好等于：
   `3 个场景 × 5 个方法 × 20 个 seed = 300`。
4. `results/scheme_c_readiness_20seed/summary.csv` 和 `main_table.csv` 已存在。

### 3.3 未完成的结果

以下内容没有完成：

1. `results/scheme_c_small_mdp/` 目录存在，但为空。
2. `docs/scheme_c_results_2026-04-21.md` 仍是占位文本，没有被最终结果覆盖。

## 4. 为什么不能直接说“整条已经跑完”

主脚本 `experiments/run_scheme_c_pipeline.py` 的执行顺序是：

1. `fit_certificate_holdout`
2. `run_readiness_multiseed`
3. `run_small_mdp_bound`
4. `_generate_doc`

当前现象是：

1. 前两步产物已落盘。
2. 第三步对应的 `results/scheme_c_small_mdp/` 仍为空。
3. 第四步对应的结果文档也没有生成完成。

因此更合理的判断是：

实验在第三步或第三步之后、第四步之前附近中断了，而不是完整结束。

## 5. 明天应该怎么做

明天的目标不是重跑全流程，而是补齐最后两步：

1. 跑 `small_mdp_bound`
2. 基于现有 `holdout/readiness` 结果重新生成最终文档

不要优先执行整条命令：

`python -m experiments.run_scheme_c_pipeline`

原因是这个脚本没有断点续跑逻辑，会把前两步重新再跑一遍，浪费时间。

## 6. 明天建议的执行顺序

### Step 1. 先核对现状是否仍一致

优先检查以下文件是否仍然存在：

1. `results/scheme_c_holdout/holdout_summary.csv`
2. `results/scheme_c_readiness_20seed/all_runs.csv`
3. `results/scheme_c_readiness_20seed/summary.csv`
4. `results/scheme_c_readiness_20seed/main_table.csv`
5. `docs/scheme_c_results_2026-04-21.md`

并确认：

1. `all_runs.csv` 仍然是 `300` 条。
2. `results/scheme_c_small_mdp/` 仍然为空或仍未包含 `summary.csv`。

如果这些条件都满足，则按本文档继续。

如果明天发现这些结果目录被删除、覆盖，或者代码/配置已经明显变动，需要重新判断是否还能只补最后两步。

### Step 2. 补跑 `small_mdp_bound`

建议执行的命令是：

```bash
python -u -m experiments.run_small_mdp_bound \
  --config configs/small_mdp_bound.yaml \
  --outdir results/scheme_c_small_mdp
```

预期产物：

1. `results/scheme_c_small_mdp/summary.csv`
2. `results/scheme_c_small_mdp/optimal_trace.csv`

### Step 3. 重新生成最终结果文档

目标文档是：

`docs/scheme_c_results_2026-04-21.md`

文档内容应当基于以下三个结果目录重新汇总生成：

1. `results/scheme_c_holdout/`
2. `results/scheme_c_readiness_20seed/`
3. `results/scheme_c_small_mdp/`

同时还应写出：

1. 主表
2. holdout 证书覆盖结果
3. `rollout_joint` 的配对比较
4. 小场景理论上界
5. 结论摘要

如果届时没有单独的“只生成文档”脚本，可以让 Codex按 `experiments/run_scheme_c_pipeline.py` 中 `_generate_doc(...)` 的逻辑补一个最小化生成步骤，但不要重跑前两步实验。

## 7. 成功补跑后的验收标准

明天完成后，至少应满足：

1. `results/scheme_c_small_mdp/summary.csv` 存在且非空。
2. `results/scheme_c_small_mdp/optimal_trace.csv` 存在且非空。
3. `docs/scheme_c_results_2026-04-21.md` 不再是“结果流水线正在运行中”的占位内容。
4. 最终文档中应能看到：
   主表、holdout 表、paired comparison，以及 small MDP summary。

## 8. 风险提醒

明天补跑前，应尽量避免这些变化：

1. 修改 `experiments/run_small_mdp_bound.py`
2. 修改 `experiments/run_scheme_c_pipeline.py`
3. 修改 `configs/small_mdp_bound.yaml`
4. 修改 `results/scheme_c_holdout/` 或 `results/scheme_c_readiness_20seed/` 下已有结果

否则会出现一种情况：

前两步结果来自“今天的代码/配置”，后两步结果来自“明天改过后的代码/配置”，导致整套结果口径不完全一致。

## 9. 时间预估

基于当前配置：

1. 文档生成通常接近秒级到分钟级。
2. 时间主要花在 `small_mdp_bound`。
3. 保守估计，补跑最后两步总耗时大约 `10-30 分钟`。
4. 如果状态空间展开偏大，可能延长到 `40 分钟` 左右。

## 10. 明天给 Codex 的一句话

如果明天需要快速恢复工作，可以直接把这句话连同本文档一起发给 Codex：

“请按照 `docs/scheme_c_resume_instructions_2026-04-21.md` 的说明，先核对现状，再只补跑 `scheme_c` 的最后两步，不要从头重跑整条 pipeline。”
