function rows = q4_no_storage_rows(data, scenarios, params)
pPerRate = process_power_for_rate(1.0, params);
pMin = process_power_for_rate(0.3, params);
outRows = cell(numel(scenarios), 1);
for i = 1:numel(scenarios)
    sc = scenarios(i);
    residual = sc.renew_mw - data.base_load_mw;
    rate = zeros(24, 1);
    feasible = residual >= pMin;
    rate(feasible) = min(residual(feasible) / pPerRate, 3.0);
    proc = pPerRate * rate;
    curtail = max(sc.renew_mw - data.base_load_mw - proc, 0);
    unserved = max(data.base_load_mw - sc.renew_mw, 0);
    outRows{i} = table(sc.id, sc.wind_scenario, sc.pv_scenario, sum(rate), mean(rate), sum(curtail), sum(unserved), ...
        max(curtail), max(unserved), vec_to_string(rate), vec_to_string(curtail), vec_to_string(unserved), ...
        VariableNames=["scenario_id","wind_scenario","pv_scenario","daily_NH3_t","avg_rate_tph","curtail_MWh", ...
        "unserved_base_MWh","max_curtail_MW","max_unserved_base_MW","rate_vector","curtail_vector","unserved_vector"]);
end
rows = vertcat(outRows{:});
end

function s = vec_to_string(x)
s = join(string(round(x(:)', 6)), " ");
end
