function plot_results(q1Hourly, q2, q3, policyMargin, flexValue, storage2d, storageMarginal, q4GridVs, topsisCandidates, figuresDir, ...
    q4NoStorage, q4WithStorage, q4StorageHourly, q4MinCapacity, stochasticRows)
if nargin < 11, q4NoStorage = table(); end
if nargin < 12, q4WithStorage = table(); end
if nargin < 13, q4StorageHourly = table(); end
if nargin < 14, q4MinCapacity = table(); end
if nargin < 15, stochasticRows = table(); end
if ~exist(figuresDir, "dir"), mkdir(figuresDir); end

fig = figure("Visible", "off");
plot(q1Hourly.hour, q1Hourly.P_load_total_MW, LineWidth=1.5); hold on;
plot(q1Hourly.hour, q1Hourly.P_re_MW, LineWidth=1.5);
bar(q1Hourly.hour, q1Hourly.P_buy_MW, FaceAlpha=0.25);
bar(q1Hourly.hour, -q1Hourly.P_sell_MW, FaceAlpha=0.25);
xlabel("Hour"); ylabel("Power (MW)");
legend(["Total load","Renewable","Buy","Sell"], Location="best");
saveas(fig, fullfile(figuresDir, "matlab_q1_power_balance.png"));
saveas(fig, fullfile(figuresDir, "fig_01_typical_power_balance.png"));
close(fig);

fig = figure("Visible", "off");
sample = q2(q2.scenario_id == "W1P1", :);
if height(sample) == 0, sample = q2(1:min(5, height(q2)), :); end
mat = zeros(height(sample), 24);
for i = 1:height(sample)
    hours = str2double(split(sample.on_hours(i)));
    hours = hours(~isnan(hours));
    mat(i, hours + 1) = 1;
end
imagesc(mat); colorbar;
xlabel("Hour"); ylabel("Q_day row"); title("Discrete schedule");
saveas(fig, fullfile(figuresDir, "fig_02_discrete_schedule_heatmap.png"));
close(fig);

fig = figure("Visible", "off");
sample = q3(q3.scenario_id == "W1P1", :);
if height(sample) == 0, sample = q3(1:min(5, height(q3)), :); end
mat = zeros(height(sample), 24);
for i = 1:height(sample)
    vals = str2double(split(sample.rate_vector(i))) / 3.0;
    mat(i, :) = vals(:)';
end
imagesc(mat); colorbar;
xlabel("Hour"); ylabel("Q_day row"); title("Continuous load factor");
saveas(fig, fullfile(figuresDir, "fig_03_continuous_schedule_heatmap.png"));
close(fig);

fig = figure("Visible", "off");
costMat = nan(6, 4);
sub = q3(q3.Q_day == 72, :);
for i = 1:height(sub)
    costMat(sub.wind_scenario(i), sub.pv_scenario(i)) = sub.unit_cost(i);
end
imagesc(costMat); colorbar;
xlabel("PV scenario"); ylabel("Wind scenario"); title("Q3 unit cost, Q=72");
saveas(fig, fullfile(figuresDir, "matlab_q2_cost_heatmap.png"));
saveas(fig, fullfile(figuresDir, "fig_04_6x4_cost_heatmap.png"));
close(fig);

fig = figure("Visible", "off");
marginMat = nan(6, 4);
sub = policyMargin(policyMargin.mode == "continuous" & policyMargin.Q_day == 72, :);
for i = 1:height(sub)
    parts = regexp(sub.scenario_id(i), "W(\d+)P(\d+)", "tokens");
    wi = str2double(parts{1}{1});
    pi = str2double(parts{1}{2});
    marginMat(wi, pi) = sub.min_policy_margin(i);
end
imagesc(marginMat); colorbar;
xlabel("PV scenario"); ylabel("Wind scenario"); title("Policy margin, Q=72");
saveas(fig, fullfile(figuresDir, "matlab_policy_margin_heatmap.png"));
saveas(fig, fullfile(figuresDir, "fig_05_6x4_policy_margin_heatmap.png"));
close(fig);

fig = figure("Visible", "off");
histogram(flexValue.unit_cost_reduction, 20);
xlabel("Unit cost reduction (yuan/t)"); ylabel("Count"); title("Flexible load value");
saveas(fig, fullfile(figuresDir, "fig_06_flexible_load_value.png"));
close(fig);

fig = figure("Visible", "off");
eVals = unique(storage2d.E_cap_MWh);
pVals = unique(storage2d.P_cap_MW);
mat = nan(numel(pVals), numel(eVals));
for i = 1:height(storage2d)
    [~, ei] = ismember(storage2d.E_cap_MWh(i), eVals);
    [~, pi] = ismember(storage2d.P_cap_MW(i), pVals);
    mat(pi, ei) = storage2d.storage_unit_cost_yuan_per_t(i);
end
imagesc(mat); colorbar;
xticks(1:numel(eVals)); xticklabels(string(round(eVals)));
yticks(1:numel(pVals)); yticklabels(string(round(pVals)));
xlabel("Energy capacity (MWh)"); ylabel("Power capacity (MW)");
title("Storage E/P scan");
saveas(fig, fullfile(figuresDir, "fig_07_storage_E_P_contour.png"));
close(fig);

fig = figure("Visible", "off");
if height(storageMarginal) > 0
    plot(storageMarginal.E_cap_to_MWh, storageMarginal.marginal_unit_cost_reduction_yuan_per_t_per_MWh, "-o");
end
xlabel("Storage capacity (MWh)"); ylabel("Marginal value");
title("Storage marginal value");
saveas(fig, fullfile(figuresDir, "fig_08_storage_marginal_value.png"));
close(fig);

fig = figure("Visible", "off");
bar([mean(q4GridVs.offgrid_unit_cost, "omitnan"), mean(q4GridVs.grid_connected_unit_cost, "omitnan")]);
xticklabels(["Off-grid", "Grid-connected"]);
ylabel("Unit cost (yuan/t)"); title("Grid support value");
saveas(fig, fullfile(figuresDir, "fig_09_grid_vs_offgrid_cost.png"));
close(fig);

fig = figure("Visible", "off");
margin = min([q3.R_self - 0.60, q3.R_green - 0.30, 0.20 - q3.R_sell], [], 2);
scatter(q3.unit_cost, margin, 18, "filled");
xlabel("Unit cost (yuan/t)"); ylabel("Minimum policy margin"); title("Pareto view");
saveas(fig, fullfile(figuresDir, "fig_10_pareto_cost_compliance.png"));
close(fig);

fig = figure("Visible", "off");
if height(topsisCandidates) > 0
    top = topsisCandidates(1, :);
    vals = [1 / max(top.unit_cost, 1e-9), top.full_pass_days, top.annual_NH3, 1 / (1 + top.storage_investment_proxy), max(top.grid_support_value, 0)];
    vals = vals / max(vals);
    polarplot([linspace(0, 2*pi, numel(vals) + 1)], [vals, vals(1)], "-o");
    title("TOPSIS best candidate");
end
saveas(fig, fullfile(figuresDir, "fig_11_topsis_radar.png"));
close(fig);

if height(q4StorageHourly) > 0
    fig = figure("Visible", "off");
    scen = q4StorageHourly.scenario_id(1);
    if ismember("SOC_MWh", string(q4StorageHourly.Properties.VariableNames))
        scenList = unique(q4StorageHourly.scenario_id);
        maxSoc = zeros(numel(scenList), 1);
        for i = 1:numel(scenList)
            maxSoc(i) = max(q4StorageHourly.SOC_MWh(q4StorageHourly.scenario_id == scenList(i)));
        end
        [~, idx] = max(maxSoc);
        scen = scenList(idx);
    end
    sub = q4StorageHourly(q4StorageHourly.scenario_id == scen, :);
    plot(sub.hour, sub.SOC_MWh, "-o"); hold on;
    bar(sub.hour, sub.P_charge_MW, FaceAlpha=0.25);
    bar(sub.hour, -sub.P_discharge_MW, FaceAlpha=0.25);
    plot(sub.hour, sub.P_curtail_MW, "--");
    xlabel("Hour"); ylabel("Power / energy"); title("Storage SOC and dispatch");
    legend(["SOC","Charge","Discharge","Curtailment"], Location="best");
    saveas(fig, fullfile(figuresDir, "q4_storage_soc_max_curtailment.png"));
    close(fig);
end

if height(q4NoStorage) > 0 && height(q4WithStorage) > 0
    fig = figure("Visible", "off");
    joined = innerjoin(q4NoStorage, q4WithStorage, Keys="scenario_id");
    [~, order] = sort(joined.delta_NH3_t, "descend");
    order = order(1:min(8, numel(order)));
    labels = joined.scenario_id(order);
    gain = joined.delta_NH3_t(order);
    curtailDrop = joined.curtail_reduction_MWh(order);
    bar(categorical(labels), [gain, curtailDrop]);
    ylabel("Improvement"); title("Storage improvement");
    legend(["NH3 gain (t/d)","Curtailment reduction (MWh)"], Location="best");
    saveas(fig, fullfile(figuresDir, "q4_storage_improvement_bar.png"));
    close(fig);
end

if height(q4GridVs) > 0
    fig = figure("Visible", "off");
    scatter(q4GridVs.grid_connected_unit_cost, q4GridVs.offgrid_unit_cost, 30, "filled"); hold on;
    lims = [min([q4GridVs.grid_connected_unit_cost; q4GridVs.offgrid_unit_cost]), max([q4GridVs.grid_connected_unit_cost; q4GridVs.offgrid_unit_cost])];
    plot(lims, lims, "--");
    xlabel("Grid-connected unit cost (yuan/t)"); ylabel("Off-grid unit cost (yuan/t)");
    title("Grid vs off-grid cost");
    saveas(fig, fullfile(figuresDir, "q4_grid_vs_offgrid_unit_cost.png"));
    close(fig);

    fig = figure("Visible", "off");
    bar(categorical(q4GridVs.scenario_id), q4GridVs.grid_support_value);
    yline(0);
    ylabel("Off-grid minus grid cost (yuan/t)"); title("Grid support value");
    saveas(fig, fullfile(figuresDir, "q4_grid_support_value.png"));
    close(fig);
end

if height(q4MinCapacity) > 0
    fig = figure("Visible", "off");
    bar(categorical(q4MinCapacity.method), [q4MinCapacity.wind_MW, q4MinCapacity.pv_MW], "stacked");
    ylabel("Required capacity (MW)"); title("Minimum off-grid renewable capacity");
    legend(["Wind","PV"], Location="best");
    saveas(fig, fullfile(figuresDir, "q4_minimum_capacity.png"));
    close(fig);
end

if height(stochasticRows) > 0
    fig = figure("Visible", "off");
    yyaxis left;
    bar(categorical("C" + string(stochasticRows.cluster_id)), stochasticRows.probability);
    ylabel("Probability");
    yyaxis right;
    plot(categorical("C" + string(stochasticRows.cluster_id)), stochasticRows.unit_cost, "-o");
    ylabel("Unit cost (yuan/t)");
    title("Representative stochastic scenarios");
    saveas(fig, fullfile(figuresDir, "stochastic_representative_scenarios.png"));
    close(fig);
end
end
