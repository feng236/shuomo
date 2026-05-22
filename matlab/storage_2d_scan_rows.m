function rows = storage_2d_scan_rows(baseScanRows)
pRatios = [0.125, 0.25, 0.5];
outRows = cell(height(baseScanRows) * numel(pRatios), 1);
k = 0;
for i = 1:height(baseScanRows)
    base = baseScanRows(i, :);
    eCap = base.E_cap_MWh;
    for j = 1:numel(pRatios)
        ratio = pRatios(j);
        pCap = eCap * ratio;
        if ismember("P_cap_MW", string(baseScanRows.Properties.VariableNames)) && base.P_cap_MW > 0
            utilization = min(1.0, pCap / base.P_cap_MW);
        else
            utilization = min(1.0, ratio);
        end
        dailyCost = base.storage_daily_cost * (1.0 + 0.03 * max(ratio - 1.0, 0.0));
        if eCap > 0
            dailyNH3 = base.daily_NH3_t * utilization;
        else
            dailyNH3 = base.daily_NH3_t;
        end
        if pCap > 0
            duration = eCap / pCap;
        else
            duration = NaN;
        end
        k = k + 1;
        outRows{k} = table(eCap, pCap, duration, dailyNH3, dailyCost, dailyCost / max(dailyNH3, 1e-9), ...
            VariableNames=["E_cap_MWh","P_cap_MW","duration_h","daily_NH3_t","storage_daily_cost","storage_unit_cost_yuan_per_t"]);
    end
end
rows = vertcat(outRows{:});
end
