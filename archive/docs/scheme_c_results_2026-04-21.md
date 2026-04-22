# 方案 C 重跑结果（2026-04-21）

结果流水线正在运行中。

预期自动写入内容：

1. holdout conformal 拟合结果
2. `paper_base / paper_hard / scenario_stress` 的 20-seed 主表
3. `rollout_joint` 对 `periodic / security_risk / security_margin` 的配对比较
4. 小场景 MDP 理论上界

结果目录：

1. [scheme_c_holdout](../results/scheme_c_holdout/)
2. [scheme_c_readiness_20seed](../results/scheme_c_readiness_20seed/)
3. [scheme_c_small_mdp](../results/scheme_c_small_mdp/)

脚本完成后会自动覆盖本文件。
