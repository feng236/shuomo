# 电工杯冲奖代码与结果检查报告

## 已补强的关键结果

1. 第四问储能模型已由启发式估算升级为小时级 MILP 调度。
   - 输出表：`python/outputs/tables/q4_storage_capacity_scan.csv`
   - 输出表：`python/outputs/tables/q4_storage_hourly_dispatch.csv`
   - 输出图：`python/outputs/figures/q4_storage_soc_max_curtailment.png`
   - 验收项：`q4_storage_power_balance` 残差为 `7.105e-15`，满足数值精度。

2. 第四问已按老师反馈改为 minimax 鲁棒口径。
   - 第 4(1) 先保留现有 `40MW` 风电、`64MW` 光伏下的自给性分析。
   - 再按 24 个风光场景中最坏场景确定突破装机规模。
   - 储能配置不再基于原始 `40/64MW`，而是基于 minimax 扩容后的风光系统。

3. 第四问储能方案不再只给单点答案，而给出多准则设计建议。
   - 输出表：`python/outputs/tables/q4_storage_design_recommendations.csv`
   - Minimax 鲁棒方案：扩容至约 `307.06MW` 风电、`491.30MW` 光伏，并配置 `130 MWh / 32.5 MW` 储能。
   - 该方案使 24 个风光场景下最坏日产氨缺口为 `0`，全年折算产氨量为 `25920 t`。
   - 经济型储能对照：`10 MWh / 2.5 MW`，边际储能成本最低，但不能保证最坏场景满产。

4. 离网最小风光装机估算已接入结果。
   - 输出表：`python/outputs/tables/q4_minimum_capacity.csv`
   - 输出图：`python/outputs/figures/q4_minimum_capacity.png`

5. 随机代表场景已接入主流程。
   - 输出表：`python/outputs/tables/stochastic_representative_scenarios.csv`
   - 输出图：`python/outputs/figures/stochastic_representative_scenarios.png`
   - 8 个代表场景概率和为 `1.0`。

6. 联网与离网经济性、系统支撑价值已形成闭环。
   - 输出表：`python/outputs/tables/q4_grid_vs_offgrid.csv`
   - 输出图：`python/outputs/figures/q4_grid_vs_offgrid_unit_cost.png`
   - 输出图：`python/outputs/figures/q4_grid_support_value.png`

## 当前代码验收

`python/outputs/tables/acceptance_report.csv` 全部为 OK：

- Q1 小时表 24 行；
- Q2 离散场景 120 行；
- Q3 连续场景 120 行；
- Q1、Q4 功率平衡残差达标；
- 绿电直连指标口径 `E_self=E_re-E_sell-E_curtail`、`R_green=E_self/E_load` 达标；
- Q4 储能输出 24 个场景、576 条小时调度；
- 随机代表场景 8 行，概率闭合。

## 论文还必须补强的部分

1. 指标口径说明要写清楚。
   - 主口径采用计量边界：`E_self = E_RE - E_sell - E_curtail`。
   - 同时给出题面文字公式复核，解释日内同时购电和上网时两种口径差异。

2. 第四问必须明确写成 minimax 问题。
   - 决策变量：风电装机、光伏装机、储能容量与功率、小时级产氨负荷。
   - 目标：最小化 24 个风光场景中的最坏日产氨缺口，并在缺口为 0 的方案中选择储能成本较低者。
   - 论文不要继续写“只对 W4P1 配储能”，否则与老师反馈冲突。

3. 最小风光装机结果需要解释极端性。
   - `LP_min_total_wind_pv_capacity` 会偏向风电，是因为全场景逐小时满足负荷时，夜间光伏无出力。
   - 固定 40:64 风光比例放大得到更大的总装机，应作为工程可实施的对照方案。

4. 政策建议要和模型证据一一对应。
   - 上网比例约束：引用 `policy_margin_heatmap.csv`。
   - 负荷柔性价值：引用 `flexible_load_value.csv`。
   - 储能消纳价值：引用 `q4_storage_capacity_scan.csv`。
   - 公网支撑价值：引用 `q4_grid_vs_offgrid.csv`。

## 进一步冲特等奖建议

1. 正文图建议优先使用 `fig_01` 到 `fig_11`，第四问补充使用 `q4_storage_soc_max_curtailment.png`、`q4_minimum_capacity.png`。
2. 摘要中必须出现可复核数字：推荐生产强度、全满足天数、单位成本、储能容量、系统支撑价值。
3. 模型章节要明确 MILP 变量、约束和目标函数，尤其是购售电互斥、10%-100%负荷、储能 SOC 循环约束。
4. 附录放 `acceptance_report.csv` 和 `data_validation_report.csv`，这是拉开普通论文和强论文的细节。
