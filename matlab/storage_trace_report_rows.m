function rows = storage_trace_report_rows(q4WithStorage)
outRows = cell(height(q4WithStorage), 1);
for i = 1:height(q4WithStorage)
    r = q4WithStorage(i, :);
    recovered = r.storage_recovered_MWh;
    outRows{i} = table(r.scenario_id, recovered, 0.0, recovered, 0.0, ...
        "offgrid_storage_charged_by_project_renewables", recovered, ...
        VariableNames=["scenario_id","SOC_green_in_MWh","SOC_grid_in_MWh","green_discharge_MWh","grid_discharge_MWh", ...
        "trace_rule","counted_as_project_green_energy_MWh"]);
end
rows = vertcat(outRows{:});
end
