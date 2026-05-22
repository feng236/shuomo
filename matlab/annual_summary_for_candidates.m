function rows = annual_summary_for_candidates(tbl)
qVals = unique(tbl.Q_day, "stable");
outRows = cell(numel(qVals), 1);
for i = 1:numel(qVals)
    q = qVals(i);
    sub = tbl(tbl.Q_day == q, :);
    annualDays = height(sub) * 15;
    annualNH3 = q * annualDays;
    annualCost = sum(sub.total_cost) * 15;
    bestFlag = "";
    outRows{i} = table(q, annualDays, annualNH3, annualCost, annualCost / max(annualNH3, 1e-9), ...
        sum(sub.class == "全满足") * 15, sum(sub.class == "部分满足") * 15, sum(sub.class == "全不满足") * 15, bestFlag, ...
        VariableNames=["Q_day","annual_days","annual_total_NH3","annual_total_cost","annual_average_unit_cost", ...
        "days_all_pass","days_partial_pass","days_all_fail","best_or_not"]);
end
rows = vertcat(outRows{:});
[~, idx] = min(rows.annual_average_unit_cost);
rows.best_or_not(idx) = "best_cost";
end
