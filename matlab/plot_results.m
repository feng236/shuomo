function plot_results(q1Hourly, q3, policyMargin, figuresDir)
if ~exist(figuresDir, "dir"), mkdir(figuresDir); end

fig = figure("Visible", "off");
plot(q1Hourly.hour, q1Hourly.P_load_total_MW, LineWidth=1.5); hold on;
plot(q1Hourly.hour, q1Hourly.P_re_MW, LineWidth=1.5);
bar(q1Hourly.hour, q1Hourly.P_buy_MW, FaceAlpha=0.25);
bar(q1Hourly.hour, -q1Hourly.P_sell_MW, FaceAlpha=0.25);
xlabel("Hour"); ylabel("Power (MW)");
legend(["Total load","Renewable","Buy","Sell"], Location="best");
saveas(fig, fullfile(figuresDir, "matlab_q1_power_balance.png"));
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
close(fig);
end
