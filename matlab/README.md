# MATLAB专区说明

本目录提供绿电直连电-氢-氨园区优化运行的 MATLAB 完整实现，和 `../python` 使用同一套表计口径：

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
- `outputs/tables/q2_annual_summary.csv`
- `outputs/tables/q3_annual_summary.csv`
- `outputs/tables/policy_margin_heatmap.csv`
- `outputs/tables/scenario_risk_summary.csv`
- `outputs/tables/flexible_load_value.csv`
- `outputs/tables/hard_soft_compare.csv`
- `outputs/tables/q4_offgrid_no_storage.csv`
- `outputs/tables/q4_storage_capacity_scan.csv`
- `outputs/tables/q4_offgrid_with_storage.csv`
- `outputs/tables/q4_storage_annual_summary.csv`
- `outputs/tables/q4_grid_vs_offgrid.csv`
- `outputs/tables/grid_support_value.csv`
- `outputs/tables/storage_2d_scan.csv`
- `outputs/tables/storage_marginal_value.csv`
- `outputs/tables/storage_trace_report.csv`
- `outputs/tables/topsis_candidates.csv`
- `outputs/tables/acceptance_report.csv`

图形输出：

- `outputs/figures/fig_01_typical_power_balance.png`
- `outputs/figures/fig_02_discrete_schedule_heatmap.png`
- `outputs/figures/fig_03_continuous_schedule_heatmap.png`
- `outputs/figures/fig_04_6x4_cost_heatmap.png`
- `outputs/figures/fig_05_6x4_policy_margin_heatmap.png`
- `outputs/figures/fig_06_flexible_load_value.png`
- `outputs/figures/fig_07_storage_E_P_contour.png`
- `outputs/figures/fig_08_storage_marginal_value.png`
- `outputs/figures/fig_09_grid_vs_offgrid_cost.png`
- `outputs/figures/fig_10_pareto_cost_compliance.png`
- `outputs/figures/fig_11_topsis_radar.png`

## 创新功能覆盖

| 创新功能 | MATLAB 输出 |
|---|---|
| 政策安全裕度 | `policy_margin_heatmap.csv`, `fig_05_6x4_policy_margin_heatmap.png` |
| 硬/软合规比较 | `hard_soft_compare.csv` |
| 柔性制氢虚拟储能价值 | `flexible_load_value.csv`, `fig_06_flexible_load_value.png` |
| 多场景风险与 CVaR | `scenario_risk_summary.csv` |
| 离网储能容量扫描 | `q4_storage_capacity_scan.csv` |
| 储能 E/P 二维扫描 | `storage_2d_scan.csv`, `fig_07_storage_E_P_contour.png` |
| 储能边际价值 | `storage_marginal_value.csv`, `fig_08_storage_marginal_value.png` |
| 储能绿电溯源 | `storage_trace_report.csv` |
| 联网/离网支撑价值 | `grid_support_value.csv`, `fig_09_grid_vs_offgrid_cost.png` |
| Pareto/TOPSIS 推荐 | `topsis_candidates.csv`, `fig_10_pareto_cost_compliance.png`, `fig_11_topsis_radar.png` |

MATLAB 版已经覆盖论文创新功能，可由 MATLAB 环境独立运行生成核心表格和图件。Python 版保留更强的 MILP 求解主线，两者可互相校验。
