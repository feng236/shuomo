function rows = storage_marginal_value_rows(scanRows)
scanRows = sortrows(scanRows, "E_cap_MWh");
if height(scanRows) < 2
    rows = table();
    return
end
outRows = cell(height(scanRows) - 1, 1);
for i = 2:height(scanRows)
    prev = scanRows(i - 1, :);
    cur = scanRows(i, :);
    dE = cur.E_cap_MWh - prev.E_cap_MWh;
    marginal = (prev.storage_unit_cost_yuan_per_t - cur.storage_unit_cost_yuan_per_t) / max(dE, 1e-9);
    outRows{i - 1} = table(prev.E_cap_MWh, cur.E_cap_MWh, marginal, ...
        VariableNames=["E_cap_from_MWh","E_cap_to_MWh","marginal_unit_cost_reduction_yuan_per_t_per_MWh"]);
end
rows = vertcat(outRows{:});
end
