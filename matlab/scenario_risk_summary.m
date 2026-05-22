function rows = scenario_risk_summary(tbl, mode)
qVals = unique(tbl.Q_day, "stable");
outRows = cell(numel(qVals), 1);
for i = 1:numel(qVals)
    q = qVals(i);
    sub = tbl(tbl.Q_day == q, :);
    violation = max(0, 0.60 - sub.R_self) + max(0, 0.30 - sub.R_green) + max(0, sub.R_sell - 0.20);
    newRow = table(string(mode), q, mean(sub.unit_cost), max(sub.unit_cost), percentile(sub.unit_cost, 90), cvar90(sub.unit_cost), ...
        mean(violation), max(violation), percentile(violation, 90), cvar90(violation), ...
        sum(sub.class == "全满足"), sum(sub.class == "部分满足"), sum(sub.class == "全不满足"), ...
        VariableNames=["mode","Q_day","cost_mean","cost_max","cost_p90","cost_cvar90", ...
        "violation_mean","violation_max","violation_p90","violation_cvar90", ...
        "full_pass_count","partial_pass_count","all_fail_count"]);
    outRows{i} = newRow;
end
rows = vertcat(outRows{:});
end

function y = percentile(x, p)
x = sort(x(:));
if isempty(x), y = NaN; return; end
pos = 1 + (numel(x) - 1) * p / 100;
lo = floor(pos);
hi = ceil(pos);
if lo == hi
    y = x(lo);
else
    y = x(lo) + (x(hi) - x(lo)) * (pos - lo);
end
end

function y = cvar90(x)
threshold = percentile(x, 90);
tail = x(x >= threshold);
if isempty(tail)
    y = threshold;
else
    y = mean(tail);
end
end
