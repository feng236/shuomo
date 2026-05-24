function main(dataDir, outDir)
%MAIN MATLAB reproduction entry for the green direct E-H2-NH3 park model.
if nargin < 1 || strlength(string(dataDir)) == 0
    dataDir = "data";
end
if nargin < 2 || strlength(string(outDir)) == 0
    outDir = "outputs";
end

dataDir = string(dataDir);
outDir = string(outDir);
tablesDir = fullfile(outDir, "tables");
figuresDir = fullfile(outDir, "figures");
if ~exist(tablesDir, "dir"), mkdir(tablesDir); end
if ~exist(figuresDir, "dir"), mkdir(figuresDir); end

params = default_params();
data = load_all_inputs(dataDir, params);
scenarios = build_scenarios(data, params);
qValues = [72, 63, 54, 45, 36];

q1Hourly = q1_balance(data, params);
q1Metrics = calc_policy_metrics(q1Hourly.P_load_total_MW, q1Hourly.P_re_MW, q1Hourly.P_buy_MW, q1Hourly.P_sell_MW, zeros(24, 1), params);

q2Rows = cell(numel(scenarios) * numel(qValues), 1);
q3Rows = cell(numel(scenarios) * numel(qValues), 1);
kRow = 0;
for i = 1:numel(scenarios)
    sc = scenarios(i);
    for q = qValues
        kRow = kRow + 1;
        q2Rows{kRow} = run_dispatch_heuristic(data.base_load_mw, sc, q, "discrete", params);
        q3Rows{kRow} = run_dispatch_heuristic(data.base_load_mw, sc, q, "continuous", params);
    end
end
q2 = vertcat(q2Rows{:});
q3 = vertcat(q3Rows{:});

policyMargin = [policy_margin_rows(q2, "discrete"); policy_margin_rows(q3, "continuous")];
riskSummary = [scenario_risk_summary(q2, "discrete"); scenario_risk_summary(q3, "continuous")];
flexValue = flexible_load_value(q2, q3);
hardSoft = [hard_soft_compare(q2, "discrete"); hard_soft_compare(q3, "continuous")];
q2Annual = annual_summary_for_candidates(q2);
q3Annual = annual_summary_for_candidates(q3);
q4NoStorage = q4_no_storage_rows(data, scenarios, params);
q4MinCapacity = q4_min_capacity_rows(data, params);
[q4Scan, q4WithStorage, q4StorageAnnual, q4GridVs, q4StorageHourly, q4StorageDesigns, q4MinimaxNoStorage] = q4_derived_tables(data, q4NoStorage, q4MinCapacity, q3, params);
stochasticRows = stochastic_representative_rows(data, scenarios, params);
storage2d = storage_2d_scan_rows(q4Scan);
storageMarginal = storage_marginal_value_rows(q4Scan);
storageTrace = storage_trace_report_rows(q4WithStorage);
topsisCandidates = topsis_candidates_rows(q2Annual, q3Annual, q4StorageAnnual, q4GridVs);
acceptance = acceptance_report(q1Hourly, q2, q3, q4WithStorage, q4StorageHourly, stochasticRows);

write_metric_table(fullfile(tablesDir, "q1_metrics.csv"), q1Metrics, q1Hourly, params);
writetable(q1Hourly, fullfile(tablesDir, "q1_hourly_balance.csv"));
writetable(q2, fullfile(tablesDir, "q2_discrete_scenarios.csv"));
writetable(q3, fullfile(tablesDir, "q3_continuous_scenarios.csv"));
writetable(q2Annual, fullfile(tablesDir, "q2_annual_summary.csv"));
writetable(q3Annual, fullfile(tablesDir, "q3_annual_summary.csv"));
writetable(policyMargin, fullfile(tablesDir, "policy_margin_heatmap.csv"));
writetable(riskSummary, fullfile(tablesDir, "scenario_risk_summary.csv"));
writetable(flexValue, fullfile(tablesDir, "flexible_load_value.csv"));
writetable(hardSoft, fullfile(tablesDir, "hard_soft_compare.csv"));
writetable(q4NoStorage, fullfile(tablesDir, "q4_offgrid_no_storage.csv"));
writetable(q4MinimaxNoStorage, fullfile(tablesDir, "q4_minimax_expanded_no_storage.csv"));
writetable(q4Scan, fullfile(tablesDir, "q4_storage_capacity_scan.csv"));
writetable(q4WithStorage, fullfile(tablesDir, "q4_offgrid_with_storage.csv"));
writetable(q4StorageHourly, fullfile(tablesDir, "q4_storage_hourly_dispatch.csv"));
writetable(q4StorageAnnual, fullfile(tablesDir, "q4_storage_annual_summary.csv"));
writetable(q4StorageDesigns, fullfile(tablesDir, "q4_storage_design_recommendations.csv"));
writetable(q4MinCapacity, fullfile(tablesDir, "q4_minimum_capacity.csv"));
writetable(q4GridVs, fullfile(tablesDir, "q4_grid_vs_offgrid.csv"));
writetable(q4GridVs, fullfile(tablesDir, "grid_support_value.csv"));
writetable(stochasticRows, fullfile(tablesDir, "stochastic_representative_scenarios.csv"));
writetable(storage2d, fullfile(tablesDir, "storage_2d_scan.csv"));
writetable(storageMarginal, fullfile(tablesDir, "storage_marginal_value.csv"));
writetable(storageTrace, fullfile(tablesDir, "storage_trace_report.csv"));
writetable(topsisCandidates, fullfile(tablesDir, "topsis_candidates.csv"));
writetable(acceptance, fullfile(tablesDir, "acceptance_report.csv"));

plot_results(q1Hourly, q2, q3, policyMargin, flexValue, storage2d, storageMarginal, q4GridVs, topsisCandidates, figuresDir, ...
    q4NoStorage, q4WithStorage, q4StorageHourly, q4MinCapacity, stochasticRows);
fprintf("Saved MATLAB outputs to %s\n", outDir);
end

function params = default_params()
params.dt_h = 1.0;
params.conv_peak_mw = 6.0;
params.wind_cap_mw = 40.0;
params.pv_cap_mw = 64.0;
params.alk_mw_36 = 10.0;
params.pem_mw_36 = 10.0;
params.nh3_mw_36 = 0.75;
params.nh3_rate_tph_36 = 1.5;
params.wind_lcoe_yuan_per_kwh = 0.15;
params.pv_lcoe_yuan_per_kwh = 0.12;
params.alk_om_yuan_per_kwh = 0.10;
params.pem_om_yuan_per_kwh = 0.15;
params.nh3_om_yuan_per_kwh = 0.002;
params.feedin_yuan_per_kwh = 0.3779;
params.nh3_capex_yuan_per_kgH2_per_h = 60000.0;
params.nh3_life_year = 30.0;
params.storage_capex_yuan_per_kwh = 1000.0;
params.storage_om_yuan_per_kwh = 0.01;
params.storage_life_year = 15.0;
params.storage_eta_ch = 0.90;
params.storage_eta_dis = 0.90;
params.storage_self_loss_per_h = 0.002;
params.tou_price = tou_price();
end

function price = tou_price()
price = zeros(24, 1);
for h = 0:23
    if (h >= 10 && h < 15) || (h >= 18 && h < 21)
        price(h + 1) = 0.8024;
    elseif (h >= 7 && h < 10) || (h >= 15 && h < 18) || (h >= 21 && h < 23)
        price(h + 1) = 0.6074;
    else
        price(h + 1) = 0.3424;
    end
end
end

function scenarios = build_scenarios(data, params)
k = 0;
for wi = 1:6
    for pi = 1:4
        k = k + 1;
        scenarios(k).id = "W" + string(wi) + "P" + string(pi); %#ok<AGROW>
        scenarios(k).wind_scenario = wi; %#ok<AGROW>
        scenarios(k).pv_scenario = pi; %#ok<AGROW>
        scenarios(k).wind_mw = params.wind_cap_mw * data.wind_scen_pu(:, wi); %#ok<AGROW>
        scenarios(k).pv_mw = params.pv_cap_mw * data.pv_scen_pu(:, pi); %#ok<AGROW>
        scenarios(k).renew_mw = scenarios(k).wind_mw + scenarios(k).pv_mw; %#ok<AGROW>
    end
end
end

function rows = q1_balance(data, params)
pWind = params.wind_cap_mw * data.typical_wind_pu;
pPv = params.pv_cap_mw * data.typical_pv_pu;
pRe = pWind + pPv;
pEha = process_power_for_rate(params.nh3_rate_tph_36, params) * ones(24, 1);
pLoad = data.base_load_mw + pEha;
pBuy = max(pLoad - pRe, 0);
pSell = max(pRe - pLoad, 0);
rows = table((0:23)', string(data.times), data.base_load_mw, pEha, pLoad, pWind, pPv, pRe, pBuy, pSell, ...
    VariableNames=["hour","time_label","P_base_MW","P_eha_MW","P_load_total_MW","P_wind_MW","P_pv_MW","P_re_MW","P_buy_MW","P_sell_MW"]);
end

function write_metric_table(path, m, q1Hourly, params)
baselineGridCost = sum(q1Hourly.P_base_MW .* params.tou_price) * 1000;
nh3CapexDaily = annualized_nh3_capex_daily(36.0, params);
totalCost = daily_cost_from_hourly(q1Hourly.P_wind_MW, q1Hourly.P_pv_MW, q1Hourly.P_buy_MW, q1Hourly.P_sell_MW, ...
    params.nh3_rate_tph_36 * ones(24, 1), 36.0, params);
row = table(m.E_load, m.E_re, m.E_buy, m.E_sell, m.E_curtail, m.E_self, m.R_self, m.R_green, m.R_sell, ...
    m.M_self, m.M_green, m.M_green_2030, m.M_sell, m.pass_self, m.pass_green, m.pass_green_2030, m.pass_sell, string(m.pass_class), ...
    totalCost, totalCost - baselineGridCost, totalCost / 36.0, (totalCost - baselineGridCost) / 36.0, ...
    baselineGridCost, nh3CapexDaily, ...
    VariableNames=["E_load","E_re","E_buy","E_sell","E_curtail","E_self","R_self","R_green","R_sell", ...
    "M_self","M_green","M_green_2030","M_sell","pass_self","pass_green","pass_green_2030","pass_sell","class", ...
    "total_cost","incremental_total_cost","unit_cost","incremental_unit_cost","baseline_grid_cost","nh3_capex_daily"]);
writetable(row, path);
end

function cost = daily_cost_from_hourly(P_wind, P_pv, P_buy, P_sell, rate, capacityTpd, params)
factor = rate / params.nh3_rate_tph_36;
pAlk = params.alk_mw_36 * factor;
pPem = params.pem_mw_36 * factor;
pNh3 = params.nh3_mw_36 * factor;
costRenew = 1000 * sum(params.wind_lcoe_yuan_per_kwh * P_wind + params.pv_lcoe_yuan_per_kwh * P_pv);
costGrid = 1000 * sum(params.tou_price .* P_buy - params.feedin_yuan_per_kwh * P_sell);
costProc = 1000 * sum(params.alk_om_yuan_per_kwh * pAlk + params.pem_om_yuan_per_kwh * pPem + params.nh3_om_yuan_per_kwh * pNh3);
cost = costRenew + costGrid + costProc + annualized_nh3_capex_daily(capacityTpd, params);
end

function cost = annualized_nh3_capex_daily(capacityTpd, params)
kgH2PerHour = 0.2 * capacityTpd * 1000 / 24;
cost = params.nh3_capex_yuan_per_kgH2_per_h * kgH2PerHour / (params.nh3_life_year * 365);
end
