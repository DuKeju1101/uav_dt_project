# Codex 在本项目中的推荐使用方式

## 原则
- 只让 Codex 做局部任务，不让它整仓库重写。
- 先跑通 baseline，再让 Codex 做增强。
- 每次只给一个清晰目标。

## 推荐任务 1：新增实验扫描

```text
阅读当前项目结构。
不要修改核心场景设定。
请新增一个 experiments/run_sigma_scan.py，扫描 sync.sigma_growth 对 avg_secrecy_rate、outage_prob、avg_twin_quality 的影响。
结果输出到 results/sigma_scan/。
保持现有代码风格，不修改其他脚本的行为。
```

## 推荐任务 2：补轨迹图

```text
请新增 analysis/trajectory_plot.py。
输入：results/baselines/slot_security_margin_seed*.csv
输出：results/plots/trajectory_security_margin.png
要求：画出 UAV-1、UAV-2、Eve 的二维轨迹，并标出 BS、3 个用户位置。
不要修改其他文件。
```

## 推荐任务 3：检查阈值逻辑

```text
请审查 env/sync.py 与 env/twin.py。
重点检查：
1. security_margin 阈值是否真正使用了 twin 不确定性；
2. AoI 与 sigma 的更新是否自洽；
3. 是否存在重复逻辑可抽取。
只允许做最小修改，并在最终说明里列出改了哪些文件。
```

## 推荐任务 4：导出论文表格

```text
请新增一个脚本 experiments/export_paper_table.py。
读取 results/baselines/summary_all_methods.csv 与 results/threshold/threshold_summary_agg.csv，
导出一份适合论文表格的 csv：
method, avg_sync_cost, avg_twin_quality, avg_secrecy_rate, outage_prob
保留 4 位小数。
```
