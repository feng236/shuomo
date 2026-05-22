function [scan, withStorage, annual, gridVs] = q4_derived_tables(q4NoStorage, q3Rows, params)
[~, idxMax] = max(q4NoStorage.curtail_MWh);
maxCurtailRow = q4NoStorage(idxMax, :);
scan = q4_storage_capacity_scan(maxCurtailRow, params);

valid = scan(~isnan(scan.storage_unit_cost_yuan_per_t) & scan.E_cap_MWh > 0, :);
if height(valid) == 0
    valid = scan(~isnan(scan.storage_unit_cost_yuan_per_t), :);
end
[~, idxBest] = min(valid.storage_unit_cost_yuan_per_t);
bestScan = valid(idxBest, :);

outRows = cell(height(q4NoStorage), 1);
for i = 1:height(q4NoStorage)
    r = q4NoStorage(i, :);
    recovered = min(r.curtail_MWh * 0.8, bestScan.E_cap_MWh * params.storage_eta_ch * params.storage_eta_dis);
    nh3Gain = recovered / process_power_for_rate(1.0, params);
    outRows{i} = table(r.scenario_id, bestScan.E_cap_MWh, r.daily_NH3_t + nh3Gain, max(r.curtail_MWh - recovered, 0), ...
        r.unserved_base_MWh, recovered, ...
        VariableNames=["scenario_id","E_cap_MWh","daily_NH3_t","curtail_MWh","unserved_base_MWh","storage_recovered_MWh"]);
end
withStorage = vertcat(outRows{:});

annual = table(bestScan.E_cap_MWh, height(withStorage) * 15, sum(withStorage.daily_NH3_t) * 15, ...
    storage_capex_daily(bestScan.E_cap_MWh, params) * height(withStorage) * 15, ...
    VariableNames=["E_cap_MWh","annual_days","annual_NH3_t","annual_storage_cost"]);

gridRows = q3Rows(q3Rows.Q_day == 72, :);
outGrid = cell(height(withStorage), 1);
storageDailyCost = storage_capex_daily(bestScan.E_cap_MWh, params);
for i = 1:height(withStorage)
    r = withStorage(i, :);
    idx = find(gridRows.scenario_id == r.scenario_id, 1);
    if isempty(idx)
        gridCost = NaN;
    else
        gridCost = gridRows.unit_cost(idx);
    end
    offCost = storageDailyCost / max(r.daily_NH3_t, 1e-9);
    outGrid{i} = table(r.scenario_id, r.daily_NH3_t, offCost, gridCost, offCost - gridCost, ...
        VariableNames=["scenario_id","offgrid_daily_NH3_t","offgrid_unit_cost","grid_connected_unit_cost","grid_support_value"]);
end
gridVs = vertcat(outGrid{:});
end

function rows = q4_storage_capacity_scan(maxCurtailRow, params)
baseCurtail = maxCurtailRow.curtail_MWh;
baseProd = maxCurtailRow.daily_NH3_t;
eCaps = 0:10:(max(1.0, baseCurtail) + 10);
outRows = cell(numel(eCaps), 1);
for i = 1:numel(eCaps)
    eCap = eCaps(i);
    recovered = min(baseCurtail * 0.8, eCap * params.storage_eta_ch * params.storage_eta_dis);
    nh3Gain = recovered / process_power_for_rate(1.0, params);
    dailyNH3 = baseProd + nh3Gain;
    cost = storage_capex_daily(eCap, params) + recovered * 1000 * params.storage_om_yuan_per_kwh;
    outRows{i} = table(eCap, recovered, dailyNH3, cost, cost / max(dailyNH3, 1e-9), ...
        VariableNames=["E_cap_MWh","recovered_MWh","daily_NH3_t","storage_daily_cost","storage_unit_cost_yuan_per_t"]);
end
rows = vertcat(outRows{:});
end
