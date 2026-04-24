# `rollout_joint` 20-seed 主实验执行文档

适用日期：`2026-04-24`

适用仓库：`/home/dkj/research/uav_dt_project`

目的：
基于 `2026-04-23` 之后最新修改过的 `rollout_joint` 逻辑，重新生成 holdout-fit 配置，并分块并行跑完整 `20-seed` 主实验，最终得到新的 `main_table.csv / summary.csv / all_runs.csv`，用于判断 `rollout_joint` 是否已经恢复到主方法应有表现。

---

## 1. 执行原则

1. 不复用旧的 holdout-fit 配置。
说明：`rollout_joint` 在 `2026-04-23` 已经继续修改过一轮门控逻辑，所以必须先重新跑 `fit_certificate_holdout`。

2. 主实验使用重新生成的 holdout-fit 配置。
说明：必须使用新生成的：
`paper_base_holdoutfit.yaml`
`paper_hard_holdoutfit.yaml`
`scenario_stress_holdoutfit.yaml`

3. 用 CPU 分块并行，不依赖 GPU。
说明：当前项目实现基本是纯 CPU 仿真，GPU 显存大小不会明显缩短主实验时间。

4. 分块跑完后统一合并结果。
说明：不要直接依赖单个块目录中的 `summary.csv` 做结论，最终结论以合并后的总目录为准。

---

## 2. 目录约定

明天执行时统一使用下面两个输出目录：

- holdout 输出目录：
`results/scheme_c_holdout_2026-04-24_rollout_vnext`

- 20-seed 并行块输出目录：
`results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext`

- 合并后的总输出目录：
`results/scheme_c_readiness_20seed_2026-04-24_rollout_vnext_merged`

---

## 3. Step 1: 重新生成 holdout-fit 配置

在仓库根目录执行：

```bash
./.venv/bin/python -u -m experiments.fit_certificate_holdout \
  --train-configs configs/base.yaml configs/scenario_hard.yaml configs/scenario_stress.yaml \
  --eval-configs configs/paper_base.yaml configs/paper_hard.yaml configs/scenario_stress.yaml \
  --train-methods periodic security_risk aoi_only \
  --eval-methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --train-seeds 3 \
  --eval-seeds 1 \
  --eval-seed-start 20 \
  --alpha 0.05 \
  --calibration-ratio 0.2 \
  --outdir results/scheme_c_holdout_2026-04-24_rollout_vnext
```

执行成功后，必须确认下面三个文件存在：

- `results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_base_holdoutfit.yaml`
- `results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_hard_holdoutfit.yaml`
- `results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/scenario_stress_holdoutfit.yaml`

---

## 4. Step 2: 分块并行跑 20-seed 主实验

### 4.1 分块策略

三个场景分别按 seed 切成四块，每块 5 个 seeds，共 12 个块：

- `62-66`
- `67-71`
- `72-76`
- `77-81`

每个块都跑 5 个方法：

- `periodic`
- `security_risk`
- `security_margin`
- `rollout_joint`
- `risk_adaptive_hybrid_rollout`

### 4.2 paper_base 四块

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_base_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 62 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_base_62_66
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_base_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 67 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_base_67_71
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_base_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 72 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_base_72_76
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_base_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 77 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_base_77_81
```

### 4.3 paper_hard 四块

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_hard_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 62 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_hard_62_66
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_hard_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 67 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_hard_67_71
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_hard_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 72 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_hard_72_76
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/paper_hard_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 77 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/paper_hard_77_81
```

### 4.4 scenario_stress 四块

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/scenario_stress_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 62 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/scenario_stress_62_66
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/scenario_stress_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 67 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/scenario_stress_67_71
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/scenario_stress_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 72 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/scenario_stress_72_76
```

```bash
./.venv/bin/python -u -m experiments.run_readiness_multiseed \
  --configs results/scheme_c_holdout_2026-04-24_rollout_vnext/configs/scenario_stress_holdoutfit.yaml \
  --methods periodic security_risk security_margin rollout_joint risk_adaptive_hybrid_rollout \
  --num-seeds 5 \
  --seed-start 77 \
  --outdir results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext/scenario_stress_77_81
```

说明：
实际执行时建议把上面 12 个块并行启动，而不是串行一个个等完。

---

## 5. Step 3: 合并 12 个块的结果

所有分块完成后，在仓库根目录执行：

```bash
./.venv/bin/python - <<'PY'
from pathlib import Path
import pandas as pd
from analysis.metrics import aggregate_runs_with_ci

root = Path('results/scheme_c_readiness_parallel_2026-04-24_rollout_vnext')
outdir = Path('results/scheme_c_readiness_20seed_2026-04-24_rollout_vnext_merged')
outdir.mkdir(parents=True, exist_ok=True)

parts = sorted(root.glob('*/all_runs.csv'))
if not parts:
    raise SystemExit('no all_runs.csv files found')

frames = [pd.read_csv(p) for p in parts]
df = pd.concat(frames, ignore_index=True)
df = df.sort_values(['scenario', 'seed', 'method']).reset_index(drop=True)
df.to_csv(outdir / 'all_runs.csv', index=False)

agg = aggregate_runs_with_ci(df, ['scenario', 'method'])
agg.to_csv(outdir / 'summary.csv', index=False)

base = agg[agg['method'] == 'periodic'][['scenario', 'avg_secrecy_rate_mean', 'outage_prob_mean']].rename(
    columns={
        'avg_secrecy_rate_mean': 'periodic_avg_secrecy_rate_mean',
        'outage_prob_mean': 'periodic_outage_prob_mean',
    }
)

gains = agg.merge(base, on='scenario', how='left')
gains['secrecy_gain_vs_periodic'] = gains['avg_secrecy_rate_mean'] - gains['periodic_avg_secrecy_rate_mean']
gains['outage_gain_vs_periodic'] = gains['periodic_outage_prob_mean'] - gains['outage_prob_mean']
gains.to_csv(outdir / 'summary_with_gains.csv', index=False)

main_table = gains[
    [
        'scenario',
        'method',
        'num_runs',
        'avg_secrecy_rate_mean',
        'avg_secrecy_rate_ci95',
        'outage_prob_mean',
        'outage_prob_ci95',
        'avg_sync_cost_mean',
        'certificate_cover_rate_mean',
        'runtime_per_slot_ms_mean',
        'runtime_per_slot_ms_ci95',
        'secrecy_gain_vs_periodic',
        'outage_gain_vs_periodic',
    ]
].sort_values(['scenario', 'avg_secrecy_rate_mean'], ascending=[True, False])

main_table.to_csv(outdir / 'main_table.csv', index=False)

header = '| ' + ' | '.join(str(c) for c in main_table.columns) + ' |'
sep = '| ' + ' | '.join('---' for _ in main_table.columns) + ' |'
rows = ['| ' + ' | '.join(str(row[c]) for c in main_table.columns) + ' |' for _, row in main_table.iterrows()]
(outdir / 'main_table.md').write_text('\n'.join([header, sep] + rows) + '\n', encoding='utf-8')

print(f'merged_parts={len(parts)}')
print(f'saved_to={outdir}')
print(main_table.to_string(index=False))
PY
```

---

## 6. Step 4: 结果检查清单

最终至少检查下面 4 件事：

1. 合并目录里是否存在这些文件：
- `all_runs.csv`
- `summary.csv`
- `summary_with_gains.csv`
- `main_table.csv`
- `main_table.md`

2. `all_runs.csv` 行数是否合理。
预期是：
`3 场景 × 5 方法 × 20 seeds = 300 条 episode 级记录`

3. `main_table.csv` 中每个 `scenario × method` 的 `num_runs` 是否都是 `20`

4. 重点看三个场景中 `rollout_joint` 的：
- `avg_secrecy_rate_mean`
- `avg_sync_cost_mean`
- `secrecy_gain_vs_periodic`

---

## 7. 明天执行时的默认目标

明天执行时，默认目标不是只看“能不能跑完”，而是回答这三个问题：

1. `rollout_joint` 是否已经在 `paper_base` 上恢复为最强或接近最强？
2. `rollout_joint` 是否已经在 `paper_hard` 上稳定优于 `periodic`？
3. `rollout_joint` 的同步成本是否从“过度同步”回落到比上一版更合理的范围？

---

## 8. 明天对话约定

如果明天把这份文档发给 Codex，默认按下面方式执行：

1. 先确认当前工作区代码就是最新要验证的版本
2. 按本文档的目录命名重新跑 holdout-fit
3. 按本文档的 12 块方案并行跑 20-seed 主实验
4. 合并结果
5. 直接汇报 `main_table` 结论，不再重复问是否要分块并行

---

## 9. 一句话执行摘要

明天的正确做法是：
先重新生成一套新的 holdout-fit 配置，再按 `12` 个并行块跑三场景 `20-seed` 主实验，最后统一合并结果，以新的 `main_table.csv` 作为唯一结论来源。
