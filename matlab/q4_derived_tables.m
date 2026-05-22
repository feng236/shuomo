function [scan, withStorage, annual, gridVs, hourly, recommendations] = q4_derived_tables(data, scenarios, q4NoStorage, q3Rows, params)
%Q4_DERIVED_TABLES Storage-enhanced off-grid analysis.
% Uses intlinprog when available; otherwise falls back to a deterministic
% source-following storage dispatch so the MATLAB package remains portable.
[~, idxMax] = max(q4NoStorage.curtail_MWh);
designScenario = scenarios(idxMax);
scan = q4_storage_capacity_scan_optimized(data, designScenario, q4NoStorage(idxMax, :), params);
recommendations = q4_storage_design_recommendations(scan);

positive = scan(scan.E_cap_MWh > 0 & scan.delta_NH3_t > 1e-6 & ~isnan(scan.incremental_storage_cost_yuan_per_added_t), :);
if height(positive) == 0
    valid = scan(~isnan(scan.storage_unit_cost_yuan_per_t), :);
    [~, idxBest] = min(valid.storage_unit_cost_yuan_per_t);
    bestScan = valid(idxBest, :);
else
    [~, idxBest] = min(positive.incremental_storage_cost_yuan_per_added_t);
    bestScan = positive(idxBest, :);
end

eCap = bestScan.E_cap_MWh;
pCap = bestScan.P_cap_MW;
withRows = cell(numel(scenarios), 1);
hourRows = cell(numel(scenarios) * 24, 1);
k = 0;
for i = 1:numel(scenarios)
    sc = scenarios(i);
    sol = solve_offgrid_storage_dispatch(data.base_load_mw, sc.renew_mw, eCap, pCap, params);
    base = q4NoStorage(q4NoStorage.scenario_id == sc.id, :);
    dailyNH3 = sum(sol.rate_tph);
    curtail = sum(sol.curtail_mwh);
    unserved = sum(sol.deficit_mwh);
    storageDailyCost = storage_capex_daily(eCap, params) + sum(sol.charge_mw) * 1000 * params.storage_om_yuan_per_kwh;
    procDailyCost = process_om_cost_for_rates(sol.rate_tph, params);
    reDailyCost = renewable_generation_cost(sc.wind_mw, sc.pv_mw, params);
    totalDailyCost = storageDailyCost + procDailyCost + reDailyCost;
    withRows{i} = table(sc.id, eCap, pCap, dailyNH3, dailyNH3 / 24, curtail, unserved, ...
        sum(sol.charge_mw), sum(sol.discharge_mw), sum(sol.discharge_mw), dailyNH3 - base.daily_NH3_t, ...
        base.curtail_MWh - curtail, max(sol.soc_mwh), totalDailyCost, totalDailyCost / max(dailyNH3, 1e-9), ...
        VariableNames=["scenario_id","E_cap_MWh","P_cap_MW","daily_NH3_t","avg_rate_tph","curtail_MWh","unserved_base_MWh", ...
        "storage_charge_MWh","storage_discharge_MWh","storage_recovered_MWh","delta_NH3_t","curtail_reduction_MWh", ...
        "max_SOC_MWh","daily_total_cost","offgrid_unit_cost"]);

    for h = 1:24
        k = k + 1;
        residual = sc.renew_mw(h) + sol.discharge_mw(h) + sol.deficit_mwh(h) ...
            - data.base_load_mw(h) - sol.proc_power_mw(h) - sol.charge_mw(h) - sol.curtail_mwh(h);
        hourRows{k} = table(sc.id, h - 1, string(data.times(h)), data.base_load_mw(h), sc.renew_mw(h), ...
            sol.rate_tph(h), sol.proc_power_mw(h), sol.charge_mw(h), sol.discharge_mw(h), sol.soc_mwh(h), ...
            sol.curtail_mwh(h), sol.deficit_mwh(h), residual, ...
            VariableNames=["scenario_id","hour","time_label","P_base_MW","P_re_MW","rate_tph","P_process_MW", ...
            "P_charge_MW","P_discharge_MW","SOC_MWh","P_curtail_MW","P_unserved_MW","balance_residual_MW"]);
    end
end
withStorage = vertcat(withRows{:});
hourly = vertcat(hourRows{:});

annual = table(eCap, pCap, designScenario.id, height(withStorage) * 15, sum(withStorage.daily_NH3_t) * 15, ...
    sum(withStorage.daily_total_cost) * 15, ...
    (storage_capex_daily(eCap, params) * height(withStorage) + sum(withStorage.storage_charge_MWh) * 1000 * params.storage_om_yuan_per_kwh) * 15, ...
    mean(withStorage.delta_NH3_t), mean(withStorage.curtail_reduction_MWh), ...
    sum(withStorage.daily_total_cost) * 15 / max(sum(withStorage.daily_NH3_t) * 15, 1e-9), ...
    VariableNames=["E_cap_MWh","P_cap_MW","design_scenario_id","annual_days","annual_NH3_t","annual_total_cost", ...
    "annual_storage_cost","mean_delta_NH3_t","mean_curtail_reduction_MWh","annual_average_unit_cost"]);

gridRows = q3Rows(q3Rows.Q_day == 72, :);
gridOut = cell(height(withStorage), 1);
for i = 1:height(withStorage)
    r = withStorage(i, :);
    idx = find(gridRows.scenario_id == r.scenario_id, 1);
    if isempty(idx)
        gridCost = NaN;
    else
        gridCost = gridRows.unit_cost(idx);
    end
    gridOut{i} = table(r.scenario_id, r.daily_NH3_t, r.offgrid_unit_cost, gridCost, r.offgrid_unit_cost - gridCost, ...
        VariableNames=["scenario_id","offgrid_daily_NH3_t","offgrid_unit_cost","grid_connected_unit_cost","grid_support_value"]);
end
gridVs = vertcat(gridOut{:});
end

function rows = q4_storage_capacity_scan_optimized(data, sc, noStorageRow, params)
baseCurtail = noStorageRow.curtail_MWh;
if baseCurtail <= 0
    eCaps = 0;
else
    eCaps = 0:10:(ceil(baseCurtail / 10) * 10 + 10);
end
outRows = cell(numel(eCaps), 1);
for i = 1:numel(eCaps)
    eCap = eCaps(i);
    if eCap > 0
        pCap = eCap / 4;
    else
        pCap = 0;
    end
    sol = solve_offgrid_storage_dispatch(data.base_load_mw, sc.renew_mw, eCap, pCap, params);
    dailyNH3 = sum(sol.rate_tph);
    charge = sum(sol.charge_mw);
    cost = storage_capex_daily(eCap, params) + charge * 1000 * params.storage_om_yuan_per_kwh;
    deltaNH3 = dailyNH3 - noStorageRow.daily_NH3_t;
    if deltaNH3 > 1e-9
        incCost = cost / deltaNH3;
    else
        incCost = NaN;
    end
    if pCap > 0
        duration = eCap / pCap;
    else
        duration = NaN;
    end
    outRows{i} = table(sc.id, eCap, pCap, duration, dailyNH3, deltaNH3, sum(sol.curtail_mwh), ...
        noStorageRow.curtail_MWh - sum(sol.curtail_mwh), charge, sum(sol.discharge_mw), max(sol.soc_mwh), ...
        sum(sol.deficit_mwh), cost, cost / max(dailyNH3, 1e-9), incCost, ...
        VariableNames=["design_scenario_id","E_cap_MWh","P_cap_MW","duration_h","daily_NH3_t","delta_NH3_t", ...
        "curtail_MWh","curtail_reduction_MWh","storage_charge_MWh","storage_discharge_MWh","max_SOC_MWh", ...
        "unserved_base_MWh","storage_daily_cost","storage_unit_cost_yuan_per_t","incremental_storage_cost_yuan_per_added_t"]);
end
rows = vertcat(outRows{:});
end

function rows = q4_storage_design_recommendations(scan)
positive = scan(scan.E_cap_MWh > 0 & scan.delta_NH3_t > 1e-6 & ~isnan(scan.incremental_storage_cost_yuan_per_added_t), :);
if height(positive) == 0
    rows = table();
    return
end
[~, idxEconomic] = min(positive.incremental_storage_cost_yuan_per_added_t);
[~, idxMaxNh3] = max(positive.daily_NH3_t);
[~, idxMaxCurtail] = max(positive.curtail_reduction_MWh);
maxReduction = max(positive.curtail_reduction_MWh);
kneeCandidates = positive(positive.curtail_reduction_MWh >= 0.90 * maxReduction, :);
[~, idxKnee] = min(kneeCandidates.E_cap_MWh);

labels = ["economic_min_incremental_cost"; "max_daily_NH3"; "max_curtailment_reduction"; "smallest_capacity_for_90pct_curtailment_reduction"];
picked = [positive(idxEconomic, :); positive(idxMaxNh3, :); positive(idxMaxCurtail, :); kneeCandidates(idxKnee, :)];
interpretation = [
    "lowest marginal storage cost per added ton of ammonia; use as the cost-first design";
    "highest off-grid ammonia output in the scanned storage range";
    "largest renewable curtailment reduction in the scanned storage range";
    "smallest storage capacity that captures at least 90% of the maximum achievable curtailment reduction"
];
rows = table(labels, picked.design_scenario_id, picked.E_cap_MWh, picked.P_cap_MW, picked.duration_h, picked.daily_NH3_t, ...
    picked.delta_NH3_t, picked.curtail_reduction_MWh, picked.storage_daily_cost, picked.incremental_storage_cost_yuan_per_added_t, interpretation, ...
    VariableNames=["recommendation_type","design_scenario_id","E_cap_MWh","P_cap_MW","duration_h","daily_NH3_t", ...
    "delta_NH3_t","curtail_reduction_MWh","storage_daily_cost","incremental_storage_cost_yuan_per_added_t","interpretation"]);
end

function sol = solve_offgrid_storage_dispatch(P_base, P_re, eCap, pCap, params)
if exist("intlinprog", "file") == 2
    try
        sol = solve_storage_intlinprog(P_base, P_re, eCap, pCap, params);
        return
    catch
        sol = solve_storage_greedy(P_base, P_re, eCap, pCap, params);
        return
    end
end
sol = solve_storage_greedy(P_base, P_re, eCap, pCap, params);
end

function sol = solve_storage_intlinprog(P_base, P_re, eCap, pCap, params)
n = 24;
rateMax = 3.0;
rateMin = 0.3;
pPerRate = process_power_for_rate(1.0, params);
idxR = 1;
idxY = idxR + n;
idxCh = idxY + n;
idxDis = idxCh + n;
idxSoc = idxDis + n;
idxCurt = idxSoc + n;
idxShed = idxCurt + n;
idxMode = idxShed + n;
nvars = idxMode + n - 1;

f = zeros(nvars, 1);
f(idxR:idxR+n-1) = -10000;
f(idxCh:idxDis-1) = 0.01;
f(idxDis:idxSoc-1) = 0.01;
f(idxCurt:idxShed-1) = 1.0;
f(idxShed:idxMode-1) = 1e6;
lb = zeros(nvars, 1);
ub = inf(nvars, 1);
ub(idxR:idxY-1) = rateMax;
ub(idxY:idxCh-1) = 1;
ub(idxCh:idxDis-1) = pCap;
ub(idxDis:idxSoc-1) = pCap;
ub(idxSoc:idxCurt-1) = eCap;
ub(idxMode:idxMode+n-1) = 1;

A = [];
b = [];
row = zeros(1, nvars);
row(idxR:idxY-1) = 1;
A = [A; row]; %#ok<AGROW>
b = [b; 72]; %#ok<AGROW>

for t = 1:n
    row = zeros(1, nvars); row(idxR+t-1) = 1; row(idxY+t-1) = -rateMax;
    A = [A; row]; b = [b; 0]; %#ok<AGROW>
    row = zeros(1, nvars); row(idxR+t-1) = -1; row(idxY+t-1) = rateMin;
    A = [A; row]; b = [b; 0]; %#ok<AGROW>
    row = zeros(1, nvars); row(idxCh+t-1) = 1; row(idxMode+t-1) = -pCap;
    A = [A; row]; b = [b; 0]; %#ok<AGROW>
    row = zeros(1, nvars); row(idxDis+t-1) = 1; row(idxMode+t-1) = pCap;
    A = [A; row]; b = [b; pCap]; %#ok<AGROW>
end

Aeq = zeros(2 * n, nvars);
beq = zeros(2 * n, 1);
for t = 1:n
    Aeq(t, idxR+t-1) = pPerRate;
    Aeq(t, idxCh+t-1) = 1;
    Aeq(t, idxCurt+t-1) = 1;
    Aeq(t, idxDis+t-1) = -1;
    Aeq(t, idxShed+t-1) = -1;
    beq(t) = P_re(t) - P_base(t);

    prev = t - 1;
    if prev == 0, prev = n; end
    Aeq(n+t, idxSoc+t-1) = 1;
    Aeq(n+t, idxSoc+prev-1) = -(1 - params.storage_self_loss_per_h);
    Aeq(n+t, idxCh+t-1) = -params.storage_eta_ch;
    Aeq(n+t, idxDis+t-1) = 1 / params.storage_eta_dis;
end

intcon = [idxY:idxCh-1, idxMode:idxMode+n-1];
opts = optimoptions("intlinprog", Display="off");
x = intlinprog(f, intcon, A, b, Aeq, beq, lb, ub, opts);
if isempty(x)
    error("intlinprog failed");
end
sol = storage_solution_from_vector(x, idxR, idxY, idxCh, idxDis, idxSoc, idxCurt, idxShed, n, pPerRate);
end

function sol = solve_storage_greedy(P_base, P_re, eCap, pCap, params)
n = 24;
pPerRate = process_power_for_rate(1.0, params);
pMin = process_power_for_rate(0.3, params);
rate = zeros(n, 1);
proc = zeros(n, 1);
charge = zeros(n, 1);
discharge = zeros(n, 1);
soc = zeros(n, 1);
curtail = zeros(n, 1);
deficit = zeros(n, 1);
    socPrev = 0.5 * eCap;
    for t = 1:n
        socPrev = socPrev * (1 - params.storage_self_loss_per_h);
        residual = P_re(t) - P_base(t);
        if residual >= pMin
            proc(t) = min(process_power_for_rate(3.0, params), residual);
        rate(t) = proc(t) / pPerRate;
            surplus = residual - proc(t);
            charge(t) = min([max(surplus, 0), pCap, max(eCap - socPrev, 0) / max(params.storage_eta_ch, 1e-9)]);
            socNow = socPrev + params.storage_eta_ch * charge(t);
        else
            neededForMin = max(pMin - residual, 0);
            canDischarge = min(pCap, socPrev * params.storage_eta_dis);
            discharge(t) = min(canDischarge, neededForMin);
            available = residual + discharge(t);
        if available >= pMin
            proc(t) = min(process_power_for_rate(3.0, params), available);
            rate(t) = proc(t) / pPerRate;
            end
            socNow = socPrev - discharge(t) / max(params.storage_eta_dis, 1e-9);
        end
        soc(t) = min(max(socNow, 0), eCap);
        socPrev = soc(t);
        gap = P_re(t) + discharge(t) - P_base(t) - proc(t) - charge(t);
        curtail(t) = max(gap, 0);
        deficit(t) = max(-gap, 0);
    end
sol.rate_tph = rate;
sol.proc_power_mw = proc;
sol.charge_mw = charge;
sol.discharge_mw = discharge;
sol.soc_mwh = soc;
sol.curtail_mwh = curtail;
sol.deficit_mwh = deficit;
end

function sol = storage_solution_from_vector(x, idxR, idxY, idxCh, idxDis, idxSoc, idxCurt, idxShed, n, pPerRate)
sol.rate_tph = max(x(idxR:idxY-1), 0);
sol.proc_power_mw = pPerRate * sol.rate_tph;
sol.charge_mw = max(x(idxCh:idxDis-1), 0);
sol.discharge_mw = max(x(idxDis:idxSoc-1), 0);
sol.soc_mwh = max(x(idxSoc:idxCurt-1), 0);
sol.curtail_mwh = max(x(idxCurt:idxShed-1), 0);
sol.deficit_mwh = max(x(idxShed:idxShed+n-1), 0);
end

function cost = renewable_generation_cost(P_wind, P_pv, params)
cost = 1000 * sum(params.wind_lcoe_yuan_per_kwh * P_wind + params.pv_lcoe_yuan_per_kwh * P_pv);
end

function cost = process_om_cost_for_rates(rate, params)
factor = rate / params.nh3_rate_tph_36;
cost = 1000 * sum(params.alk_om_yuan_per_kwh * params.alk_mw_36 .* factor ...
    + params.pem_om_yuan_per_kwh * params.pem_mw_36 .* factor ...
    + params.nh3_om_yuan_per_kwh * params.nh3_mw_36 .* factor);
end
