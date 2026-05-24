# 绿电直连电-氢-氨园区优化运行代码包

本仓库面向数学建模竞赛 A 题，按语言划分为两个专区：

- `python/`：完整计算主线，包含数据读取、MILP/LP 调度、绿电直连指标、Q4 minimax 扩容与储能扫描、风险统计、Pareto/TOPSIS 推荐、论文图表输出。
- `matlab/`：MATLAB 完整实现版本，使用同一指标口径和 Q4 minimax 口径，可独立生成创新表格、创新图件和验收报告，便于同学在 MATLAB 环境直接运行。

## 指标口径

采用表计边界口径：

```text
E_self = E_re - E_sell - E_curtail
R_self = E_self / E_re
R_green = E_self / E_load
R_sell = E_sell / E_re
```

合规阈值：

```text
R_self >= 60%
R_green >= 30%
R_green_2030 >= 35%   # 补充目标
R_sell <= 20%
```

## Python 运行

```powershell
cd D:\shumo\green_direct_e_h2_nh3_model_pack_v2\python
pip install -r requirements.txt
python main.py --data_dir "D:\qq file\A题\A题" --out_dir ".\outputs"
```

主要输出：

- `python/outputs/tables/result_summary_for_paper.xlsx`
- `python/outputs/tables/acceptance_report.csv`
- `python/outputs/tables/policy_margin_heatmap.csv`
- `python/outputs/tables/scenario_risk_summary.csv`
- `python/outputs/tables/flexible_load_value.csv`
- `python/outputs/tables/q4_minimum_capacity.csv`
- `python/outputs/tables/q4_minimax_expanded_no_storage.csv`
- `python/outputs/tables/q4_storage_design_recommendations.csv`
- `python/outputs/tables/storage_2d_scan.csv`
- `python/outputs/tables/storage_trace_report.csv`
- `python/outputs/tables/grid_support_value.csv`
- `python/outputs/tables/topsis_candidates.csv`
- `python/outputs/figures/fig_01_typical_power_balance.png` 至 `fig_11_topsis_radar.png`

## MATLAB 运行

```matlab
cd("D:/shumo/green_direct_e_h2_nh3_model_pack_v2/matlab")
main("D:/qq file/A题/A题", "outputs")
```

MATLAB 版输出位于 `matlab/outputs/tables` 和 `matlab/outputs/figures`，覆盖政策裕度、风险统计、柔性负荷价值、离网储能、储能 E/P 扫描、绿电溯源、联网/离网支撑价值和 TOPSIS 推荐。

## 创新输出对应关系

| 创新点 | 代码输出 |
|---|---|
| 计量边界修正与政策安全裕度 | `policy_margin_heatmap.csv` |
| 合规优先的硬/软约束比较 | `hard_soft_compare.csv` |
| 柔性制氢虚拟储能价值 | `flexible_load_value.csv` |
| 多场景风险统计与 CVaR | `scenario_risk_summary.csv` |
| 第四问 minimax 扩容与储能鲁棒配置 | `q4_minimum_capacity.csv`, `q4_storage_design_recommendations.csv` |
| 储能容量-功率二维扫描 | `storage_2d_scan.csv` |
| 储能绿电溯源 | `storage_trace_report.csv` |
| 联网/离网系统支撑价值 | `grid_support_value.csv` |
| Pareto + TOPSIS 综合推荐 | `topsis_candidates.csv` |

## 验收

Python 主流程会生成 `acceptance_report.csv`，检查：

- Q1 小时表为 24 行；
- Q2 离散场景为 120 行；
- Q3 连续场景为 120 行；
- 功率平衡残差满足精度要求；
- `E_self=E_re-E_sell-E_curtail` 与 `R_green=E_self/E_load` 口径一致。
