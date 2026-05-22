function rows = topsis_candidates_rows(q2Annual, q3Annual, q4StorageAnnual, q4GridVs)
schemes = strings(0, 1);
unitCost = [];
fullPassDays = [];
annualNH3 = [];
storageProxy = [];
gridValue = [];

for i = 1:height(q2Annual)
    schemes(end + 1, 1) = "discrete_Q" + string(q2Annual.Q_day(i)); %#ok<AGROW>
    unitCost(end + 1, 1) = q2Annual.annual_average_unit_cost(i); %#ok<AGROW>
    fullPassDays(end + 1, 1) = q2Annual.days_all_pass(i); %#ok<AGROW>
    annualNH3(end + 1, 1) = q2Annual.annual_total_NH3(i); %#ok<AGROW>
    storageProxy(end + 1, 1) = 0.0; %#ok<AGROW>
    gridValue(end + 1, 1) = 0.0; %#ok<AGROW>
end
for i = 1:height(q3Annual)
    schemes(end + 1, 1) = "continuous_Q" + string(q3Annual.Q_day(i)); %#ok<AGROW>
    unitCost(end + 1, 1) = q3Annual.annual_average_unit_cost(i); %#ok<AGROW>
    fullPassDays(end + 1, 1) = q3Annual.days_all_pass(i); %#ok<AGROW>
    annualNH3(end + 1, 1) = q3Annual.annual_total_NH3(i); %#ok<AGROW>
    storageProxy(end + 1, 1) = 0.0; %#ok<AGROW>
    gridValue(end + 1, 1) = 0.0; %#ok<AGROW>
end
if height(q4StorageAnnual) > 0
    schemes(end + 1, 1) = "offgrid_storage";
    unitCost(end + 1, 1) = q4StorageAnnual.annual_storage_cost(1) / max(q4StorageAnnual.annual_NH3_t(1), 1e-9);
    fullPassDays(end + 1, 1) = 0.0;
    annualNH3(end + 1, 1) = q4StorageAnnual.annual_NH3_t(1);
    storageProxy(end + 1, 1) = q4StorageAnnual.E_cap_MWh(1);
    gridValue(end + 1, 1) = nanmean_safe(q4GridVs.grid_support_value);
end

rows = table(schemes, unitCost, fullPassDays, annualNH3, storageProxy, gridValue, ...
    VariableNames=["scheme","unit_cost","full_pass_days","annual_NH3","storage_investment_proxy","grid_support_value"]);
rows = topsis_rank(rows);
end

function rows = topsis_rank(rows)
cols = ["unit_cost","full_pass_days","annual_NH3","storage_investment_proxy","grid_support_value"];
X = zeros(height(rows), numel(cols));
for j = 1:numel(cols)
    X(:, j) = rows.(cols(j));
end
X(isnan(X)) = 0;
denom = sqrt(sum(X .^ 2, 1));
denom(denom == 0) = 1;
V = X ./ denom;
weights = [0.30, 0.25, 0.15, 0.15, 0.15];
V = V .* weights;
benefit = [false, true, true, false, true];
idealPos = zeros(1, numel(cols));
idealNeg = zeros(1, numel(cols));
for j = 1:numel(cols)
    if benefit(j)
        idealPos(j) = max(V(:, j));
        idealNeg(j) = min(V(:, j));
    else
        idealPos(j) = min(V(:, j));
        idealNeg(j) = max(V(:, j));
    end
end
dPos = sqrt(sum((V - idealPos) .^ 2, 2));
dNeg = sqrt(sum((V - idealNeg) .^ 2, 2));
rows.topsis_score = dNeg ./ (dPos + dNeg + 1e-12);
rows = sortrows(rows, "topsis_score", "descend");
rows.rank = (1:height(rows))';
end

function v = nanmean_safe(x)
x = x(~isnan(x));
if isempty(x)
    v = 0.0;
else
    v = mean(x);
end
end
