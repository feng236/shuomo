function rows = q4_min_capacity_rows(data, params)
%Q4_MIN_CAPACITY_ROWS Minimax renewable capacity estimates for Q4.
reqHourly = data.base_load_mw + process_power_for_rate(3.0, params);
reqDaily = sum(reqHourly);

dailyBest = linprog_min_daily_capacity(data.wind_scen_pu, data.pv_scen_pu, reqDaily);
[dailyScale, dailyWorst] = fixed_ratio_daily_scale(data, params, reqDaily);
etaRt = params.storage_eta_ch * params.storage_eta_dis;
dailyScaleLoss = dailyScale / etaRt;

hourlyBest = linprog_min_hourly_capacity(data.wind_scen_pu, data.pv_scen_pu, reqHourly);
[hourlyScale, hourlyWorst] = fixed_ratio_hourly_scale(data, params, reqHourly);

method = [
    "minimax_daily_energy_LP";
    "minimax_daily_energy_fixed_ratio";
    "minimax_daily_energy_fixed_ratio_storage_loss_margin";
    "minimax_hourly_LP_no_storage";
    "minimax_hourly_fixed_ratio_no_storage"
];
wind = [
    dailyBest.wind_mw;
    params.wind_cap_mw * dailyScale;
    params.wind_cap_mw * dailyScaleLoss;
    hourlyBest.wind_mw;
    params.wind_cap_mw * hourlyScale
];
pv = [
    dailyBest.pv_mw;
    params.pv_cap_mw * dailyScale;
    params.pv_cap_mw * dailyScaleLoss;
    hourlyBest.pv_mw;
    params.pv_cap_mw * hourlyScale
];
total = wind + pv;
role = [
    "mathematical_lower_bound";
    "storage_design_basis";
    "storage_design_basis";
    "strict_no_storage_boundary";
    "strict_no_storage_boundary"
];
worst = [
    dailyBest.worst_case_scenario_id;
    dailyWorst;
    dailyWorst;
    "";
    hourlyWorst
];
note = [
    "minimax daily-energy capacity: minimize wind_MW + pv_MW while meeting daily base load plus 72 t/d process energy in every scenario; storage is still needed for hourly mismatch";
    "minimax fixed-ratio capacity; W/P keeps original 40:64 mix and takes worst scenario scale";
    "engineering storage-design basis: fixed-ratio minimax daily energy with round-trip storage-loss margin";
    "strict hourly no-storage lower boundary: every hour in every scenario must meet base load plus full 72 t/d process load";
    "strict hourly no-storage fixed-ratio boundary; much larger because PV has no night output"
];

rows = table(method, wind, pv, total, total / (params.wind_cap_mw + params.pv_cap_mw), ...
    repmat(reqDaily, numel(method), 1), worst, role, note, ...
    VariableNames=["method","wind_MW","pv_MW","total_MW","scale_vs_current", ...
    "required_daily_MWh","worst_case_scenario_id","basis_role","note"]);
end

function best = linprog_min_daily_capacity(windPu, pvPu, reqDaily)
windDaily = sum(windPu, 1);
pvDaily = sum(pvPu, 1);
if exist("linprog", "file") == 2
    A = [];
    b = [];
    for wi = 1:6
        for pi = 1:4
            A(end + 1, :) = [-windDaily(wi), -pvDaily(pi)]; %#ok<AGROW>
            b(end + 1, 1) = -reqDaily; %#ok<AGROW>
        end
    end
    opts = optimoptions("linprog", Display="off");
    [x, fval, exitflag] = linprog([1; 1], A, b, [], [], [0; 0], [], opts);
    if exitflag > 0
        best.wind_mw = x(1);
        best.pv_mw = x(2);
        best.sum_mw = fval;
        [~, idx] = min_capacity_slack_scenario(windDaily, pvDaily, x(1), x(2), reqDaily);
        best.worst_case_scenario_id = scenario_id_from_index(idx);
        return
    end
end

best.wind_mw = inf;
best.pv_mw = inf;
best.sum_mw = inf;
best.worst_case_scenario_id = "";
for share = unique([0, linspace(0.05, 0.95, 181), 1])
    scaleNeed = 0;
    worstIdx = 1;
    for wi = 1:6
        for pi = 1:4
            idx = (wi - 1) * 4 + pi;
            profile = share * windDaily(wi) + (1 - share) * pvDaily(pi);
            scale = reqDaily / max(profile, 1e-9);
            if scale > scaleNeed
                scaleNeed = scale;
                worstIdx = idx;
            end
        end
    end
    wind = scaleNeed * share;
    pv = scaleNeed * (1 - share);
    if wind + pv < best.sum_mw
        best.wind_mw = wind;
        best.pv_mw = pv;
        best.sum_mw = wind + pv;
        best.worst_case_scenario_id = scenario_id_from_index(worstIdx);
    end
end
end

function best = linprog_min_hourly_capacity(windPu, pvPu, reqHourly)
if exist("linprog", "file") == 2
    A = [];
    b = [];
    for wi = 1:6
        for pi = 1:4
            for h = 1:24
                A(end + 1, :) = [-windPu(h, wi), -pvPu(h, pi)]; %#ok<AGROW>
                b(end + 1, 1) = -reqHourly(h); %#ok<AGROW>
            end
        end
    end
    opts = optimoptions("linprog", Display="off");
    [x, fval, exitflag] = linprog([1; 1], A, b, [], [], [0; 0], [], opts);
    if exitflag > 0
        best.wind_mw = x(1);
        best.pv_mw = x(2);
        best.sum_mw = fval;
        return
    end
end

best.wind_mw = inf;
best.pv_mw = inf;
best.sum_mw = inf;
for share = unique([0, linspace(0.05, 0.95, 181), 1])
    scaleNeed = 0;
    for wi = 1:6
        for pi = 1:4
            profile = share * windPu(:, wi) + (1 - share) * pvPu(:, pi);
            scaleNeed = max(scaleNeed, max(reqHourly ./ max(profile, 1e-9)));
        end
    end
    wind = scaleNeed * share;
    pv = scaleNeed * (1 - share);
    if wind + pv < best.sum_mw
        best.wind_mw = wind;
        best.pv_mw = pv;
        best.sum_mw = wind + pv;
    end
end
end

function [scale, worstId] = fixed_ratio_daily_scale(data, params, reqDaily)
scale = 0;
worstId = "";
for wi = 1:6
    for pi = 1:4
        current = params.wind_cap_mw * data.wind_scen_pu(:, wi) + params.pv_cap_mw * data.pv_scen_pu(:, pi);
        need = reqDaily / max(sum(current), 1e-9);
        if need > scale
            scale = need;
            worstId = "W" + string(wi) + "P" + string(pi);
        end
    end
end
end

function [scale, worstId] = fixed_ratio_hourly_scale(data, params, reqHourly)
scale = 0;
worstId = "";
for wi = 1:6
    for pi = 1:4
        current = params.wind_cap_mw * data.wind_scen_pu(:, wi) + params.pv_cap_mw * data.pv_scen_pu(:, pi);
        need = max(reqHourly ./ max(current, 1e-9));
        if need > scale
            scale = need;
            worstId = "W" + string(wi) + "P" + string(pi);
        end
    end
end
end

function [slack, idx] = min_capacity_slack_scenario(windDaily, pvDaily, wind, pv, reqDaily)
slack = inf;
idx = 1;
for wi = 1:6
    for pi = 1:4
        currentIdx = (wi - 1) * 4 + pi;
        thisSlack = wind * windDaily(wi) + pv * pvDaily(pi) - reqDaily;
        if thisSlack < slack
            slack = thisSlack;
            idx = currentIdx;
        end
    end
end
end

function id = scenario_id_from_index(idx)
wi = floor((idx - 1) / 4) + 1;
pi = mod(idx - 1, 4) + 1;
id = "W" + string(wi) + "P" + string(pi);
end
