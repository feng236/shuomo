function rows = stochastic_representative_rows(data, scenarios, params)
%STOCHASTIC_REPRESENTATIVE_ROWS Deterministic representative-scenario table.
% The Python implementation uses Monte Carlo + K-Means. This MATLAB version
% keeps the same evidence interface without toolbox dependence by ranking the
% 24 provided wind/PV combinations and aggregating them into 8 probability bins.
energy = zeros(numel(scenarios), 1);
for i = 1:numel(scenarios)
    energy(i) = sum(scenarios(i).renew_mw);
end
[~, order] = sort(energy, "descend");
groups = cell(8, 1);
for i = 1:numel(order)
    g = mod(i - 1, 8) + 1;
    groups{g}(end + 1) = order(i); %#ok<AGROW>
end

outRows = cell(8, 1);
for g = 1:8
    idxs = groups{g};
    prob = numel(idxs) / numel(scenarios);
    wind = zeros(24, 1);
    pv = zeros(24, 1);
    for idx = idxs
        wind = wind + scenarios(idx).wind_mw;
        pv = pv + scenarios(idx).pv_mw;
    end
    wind = wind / numel(idxs);
    pv = pv / numel(idxs);
    sc.id = "C" + string(g);
    sc.wind_scenario = g;
    sc.pv_scenario = g;
    sc.wind_mw = wind;
    sc.pv_mw = pv;
    sc.renew_mw = wind + pv;
    row = run_dispatch_heuristic(data.base_load_mw, sc, 72, "continuous", params);
    outRows{g} = table(g, prob, prob * 360, 72, row.unit_cost, row.R_self, row.R_green, row.R_sell, row.class, ...
        row.E_buy, row.E_sell, mean(wind / params.wind_cap_mw), mean(pv / params.pv_cap_mw), ...
        VariableNames=["cluster_id","probability","expected_days","daily_NH3_t","unit_cost","R_self","R_green","R_sell", ...
        "class","E_buy_MWh","E_sell_MWh","wind_mean_pu","pv_mean_pu"]);
end
rows = vertcat(outRows{:});
rows.probability = rows.probability / sum(rows.probability);
rows.expected_days = rows.probability * 360;
end
