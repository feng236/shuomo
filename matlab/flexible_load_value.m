function rows = flexible_load_value(q2, q3)
keys2 = q2.scenario_id + "_" + string(q2.Q_day);
outRows = {};
for i = 1:height(q3)
    key = q3.scenario_id(i) + "_" + string(q3.Q_day(i));
    idx = find(keys2 == key, 1);
    if isempty(idx), continue; end
    newRow = table(q3.scenario_id(i), q3.Q_day(i), ...
        q2.unit_cost(idx) - q3.unit_cost(i), q2.E_buy(idx) - q3.E_buy(i), q2.E_sell(idx) - q3.E_sell(i), ...
        q3.R_self(i) - q2.R_self(idx), q3.R_green(i) - q2.R_green(idx), q2.R_sell(idx) - q3.R_sell(i), ...
        VariableNames=["scenario_id","Q_day","unit_cost_reduction","buy_reduction_MWh","sell_reduction_MWh", ...
        "self_ratio_gain","green_ratio_gain","sell_ratio_reduction"]);
    outRows{end + 1, 1} = newRow; %#ok<AGROW>
end
if isempty(outRows)
    rows = table();
else
    rows = vertcat(outRows{:});
end
end
