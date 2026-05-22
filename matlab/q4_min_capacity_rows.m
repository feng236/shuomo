function rows = q4_min_capacity_rows(data, params)
%Q4_MIN_CAPACITY_ROWS Minimum renewable capacity estimates for off-grid full-load operation.
req = data.base_load_mw + process_power_for_rate(3.0, params);

best = linprog_min_capacity(data.wind_scen_pu, data.pv_scen_pu, req);
scale = 0;
for wi = 1:6
    for pi = 1:4
        current = params.wind_cap_mw * data.wind_scen_pu(:, wi) + params.pv_cap_mw * data.pv_scen_pu(:, pi);
        scale = max(scale, max(req ./ max(current, 1e-9)));
    end
end

rows = table( ...
    ["LP_min_total_wind_pv_capacity"; "fixed_wind_pv_ratio_scale"], ...
    [best.wind_mw; params.wind_cap_mw * scale], ...
    [best.pv_mw; params.pv_cap_mw * scale], ...
    [best.wind_mw + best.pv_mw; (params.wind_cap_mw + params.pv_cap_mw) * scale], ...
    [(best.wind_mw + best.pv_mw) / (params.wind_cap_mw + params.pv_cap_mw); scale], ...
    ["minimize wind_MW + pv_MW while meeting base load plus full 72 t/d process load in all 24 scenarios"; ...
     "keep 40:64 wind/PV ratio and scale until all hours and scenarios are self-sufficient"], ...
    VariableNames=["method","wind_MW","pv_MW","total_MW","scale_vs_current","note"]);
end

function best = linprog_min_capacity(windPu, pvPu, req)
if exist("linprog", "file") == 2
    A = [];
    b = [];
    for wi = 1:6
        for pi = 1:4
            for h = 1:24
                A(end + 1, :) = [-windPu(h, wi), -pvPu(h, pi)]; %#ok<AGROW>
                b(end + 1, 1) = -req(h); %#ok<AGROW>
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

% Portable fallback: coarse wind/PV mix scan.
best.wind_mw = inf;
best.pv_mw = inf;
best.sum_mw = inf;
for share = linspace(0.05, 0.95, 181)
    scaleNeed = 0;
    for wi = 1:6
        for pi = 1:4
            profile = share * windPu(:, wi) + (1 - share) * pvPu(:, pi);
            scaleNeed = max(scaleNeed, max(req ./ max(profile, 1e-9)));
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
