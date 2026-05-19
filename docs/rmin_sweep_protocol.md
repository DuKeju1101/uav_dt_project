# R_min Sweep Protocol

The calibrated stress scenario uses `channel.r_min = 1.10` because the earlier stress threshold made all evaluated methods remain in outage. This is a valid calibrated operating point, but it is not enough by itself to support a threshold-robust outage claim.

Run the stress-threshold sweep before making broad claims about outage robustness:

```bash
python3 -m experiments.run_rmin_sweep \
  --config results/final_2026-05-12/scheme_c_holdout/configs/scenario_stress_holdoutfit.yaml \
  --r-min-values 0.6 0.9 1.1 1.4 1.7 2.0 2.5 \
  --methods periodic security_risk security_margin rollout_joint \
  --num-seeds 20 \
  --seed-start 62 \
  --outdir results/final_2026-05-12/rmin_sweep_stress
```

The script writes:

1. `all_runs.csv`: one row per seed, method, and threshold.
2. `summary.csv`: bootstrap aggregate metrics by `r_min` and method.
3. `gains_vs_periodic.csv`: secrecy-rate and outage gains relative to `periodic`.
4. `rmin_sweep_secrecy_gain.pdf`: secrecy-rate gain curve.
5. `rmin_sweep_outage_gain.pdf`: outage-reduction curve.

After the sweep finishes, regenerate paper figures:

```bash
python3 paper/scripts/make_figures.py
```

Interpretation rule:

- If `rollout_joint` remains above `periodic` across several `R_min` values, the stress conclusion can be described as robust to the outage threshold over that range.
- If the gain appears only near `R_min = 1.10`, keep the paper narrative narrower: the method is effective at the calibrated stress operating point, but outage gains are threshold-sensitive.

This sweep must rerun the controllers rather than recomputing outage from existing summaries, because `R_min` affects the rollout score, certificate slack, and synchronization decisions.
