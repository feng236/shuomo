# MATLAB专区说明

本目录提供绿电直连电-氢-氨园区优化运行的 MATLAB 复现实装，和 `../python` 使用同一套表计口径：

- `E_self = E_re - E_sell - E_curtail`
- `R_self = E_self / E_re`
- `R_green = E_self / E_load`
- `R_sell = E_sell / E_re`

## 运行方式

```matlab
cd matlab
main("D:/qq file/A题/A题", "outputs")
```

输出目录：

- `outputs/tables/q1_metrics.csv`
- `outputs/tables/q2_discrete_scenarios.csv`
- `outputs/tables/q3_continuous_scenarios.csv`
- `outputs/tables/policy_margin_heatmap.csv`
- `outputs/tables/scenario_risk_summary.csv`
- `outputs/tables/flexible_load_value.csv`
- `outputs/tables/hard_soft_compare.csv`
- `outputs/tables/acceptance_report.csv`
- `outputs/figures/matlab_q1_power_balance.png`
- `outputs/figures/matlab_q2_cost_heatmap.png`
- `outputs/figures/matlab_policy_margin_heatmap.png`

MATLAB 版用于竞赛论文复现、交叉校验和无 Python 环境时的备用运行。Python 版保留更完整的 MILP、储能扫描和 TOPSIS 输出。
