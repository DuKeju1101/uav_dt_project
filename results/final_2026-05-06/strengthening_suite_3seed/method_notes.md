| method | note |
| --- | --- |
| full | Synchronize whenever budget is available, with greedy joint motion/power control. |
| periodic | Fixed-period synchronization with greedy joint motion/power control. |
| aoi_only | Age-of-information threshold synchronization baseline. |
| security_risk | Risk-triggered synchronization baseline. |
| security_margin | Certificate-triggered synchronization baseline. |
| decoupled | Decoupled periodic synchronization followed by greedy motion/power control. |
| random_budgeted | Stochastic budget-aware synchronization baseline. |
| myopic_greedy_no_sync | Myopic greedy motion/power controller with synchronization disabled. |
| no_twin | Rollout controller with digital-twin prediction disabled; it acts on the last synced Eve estimate. |
| sca_twin | Successive-approximation optimizer that scores candidates with the deployable twin estimate. |
| sca_oracle | Oracle successive-approximation upper reference that scores candidates with true Eve state. |
| rollout_fixed_periodic | Same rollout motion/power search as rollout_joint, but synchronization is fixed periodic. |
| rollout_no_sync | Same rollout motion/power search as rollout_joint, but synchronization is disabled. |
| rollout_joint | Proposed adaptive synchronization, motion, and power rollout controller. |
| oracle_sync | Upper-reference rollout that evaluates candidates with true Eve state. |
