function rows = annual_summary_for_candidates(tbl)
qVals = unique(tbl.Q_day, "stable");
outRows = cell(numel(qVals), 1);
for i = 1:numel(qVals)
    q = qVals(i);
    sub = tbl(tbl.Q_day == q, :);
    annualDays = height(sub) * 15;
    annualNH3 = q * annualDays;
    annualCost = sum(sub.total_cost) * 15;
    if ismember("incremental_total_cost", string(sub.Properties.VariableNames))
        annualIncrementalCost = sum(sub.incremental_total_cost) * 15;
    else
        annualIncrementalCost = NaN;
    end
    passCount = double(sub.pass_self) + double(sub.pass_green) + double(sub.pass_sell);
    bestFlag = "";
    outRows{i} = table(q, annualDays, annualNH3, annualCost, annualIncrementalCost, ...
        annualCost / max(annualNH3, 1e-9), annualIncrementalCost / max(annualNH3, 1e-9), ...
        sum(passCount == 3) * 15, sum(passCount > 0 & passCount < 3) * 15, sum(passCount == 0) * 15, bestFlag, ...
        VariableNames=["Q_day","annual_days","annual_total_NH3","annual_total_cost","annual_incremental_total_cost", ...
        "annual_average_unit_cost","annual_average_incremental_unit_cost","days_all_pass","days_partial_pass","days_all_fail","best_or_not"]);
end
rows = vertcat(outRows{:});
[~, idx] = min(rows.annual_average_unit_cost);
rows.best_or_not(idx) = "best_cost";
end
