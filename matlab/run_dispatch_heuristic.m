function row = run_dispatch_heuristic(P_base, sc, qDay, mode, params)
%RUN_DISPATCH_HEURISTIC Deterministic dispatch used for MATLAB cross-check.
rateMax = 3.0;
rateMin = 0.3;
pFull = process_power_for_rate(rateMax, params);
pPerRate = process_power_for_rate(1.0, params);
netSurplus = sc.renew_mw - P_base;

if mode == "discrete"
    onHours = round(qDay / rateMax);
    score = netSurplus - 0.1 * params.tou_price;
    [~, order] = sort(score, "descend");
    y = zeros(24, 1);
    y(order(1:onHours)) = 1;
    rate = rateMax * y;
else
    rate = rateMin * ones(24, 1);
    remaining = qDay - 24 * rateMin;
    score = netSurplus - 0.1 * params.tou_price;
    [~, order] = sort(score, "descend");
    for k = 1:24
        t = order(k);
        add = min(rateMax - rateMin, remaining);
        rate(t) = rate(t) + add;
        remaining = remaining - add;
        if remaining <= 1e-9
            break
        end
    end
end

P_eha = pPerRate * rate;
P_load = P_base + P_eha;
P_buy = max(P_load - sc.renew_mw, 0);
P_sell = max(sc.renew_mw - P_load, 0);
m = calc_policy_metrics(P_load, sc.renew_mw, P_buy, P_sell, zeros(24, 1), params);
cost = daily_cost(sc.wind_mw, sc.pv_mw, P_buy, P_sell, rate, params);
baselineCost = baseline_grid_cost(P_base, params);
incrementalCost = cost - baselineCost;

row = table(sc.id, sc.wind_scenario, sc.pv_scenario, qDay, cost, incrementalCost, cost / qDay, incrementalCost / qDay, ...
    m.E_load, m.E_re, m.E_buy, m.E_sell, m.E_curtail, m.E_self, m.R_self, m.R_green, m.R_sell, string(m.pass_class), ...
    m.pass_self, m.pass_green, m.pass_green_2030, m.pass_sell, join(string(rate'), " "), ...
    VariableNames=["scenario_id","wind_scenario","pv_scenario","Q_day","total_cost","incremental_total_cost","unit_cost","incremental_unit_cost", ...
    "E_load","E_re","E_buy","E_sell","E_curtail","E_self","R_self","R_green","R_sell","class", ...
    "pass_self","pass_green","pass_green_2030","pass_sell","rate_vector"]);

if mode == "discrete"
    row.on_hours = join(string(find(rate > 0)' - 1), " ");
else
    row.on_hours = "";
end
end

function p = process_power_for_rate(rateTph, params)
p = (params.alk_mw_36 + params.pem_mw_36 + params.nh3_mw_36) / params.nh3_rate_tph_36 * rateTph;
end

function cost = daily_cost(P_wind, P_pv, P_buy, P_sell, rate, params)
factor = rate / params.nh3_rate_tph_36;
pAlk = params.alk_mw_36 * factor;
pPem = params.pem_mw_36 * factor;
pNh3 = params.nh3_mw_36 * factor;
costRenew = 1000 * sum(params.wind_lcoe_yuan_per_kwh * P_wind + params.pv_lcoe_yuan_per_kwh * P_pv);
costGrid = 1000 * sum(params.tou_price .* P_buy - params.feedin_yuan_per_kwh * P_sell);
costProc = 1000 * sum(params.alk_om_yuan_per_kwh * pAlk + params.pem_om_yuan_per_kwh * pPem + params.nh3_om_yuan_per_kwh * pNh3);
cost = costRenew + costGrid + costProc + annualized_nh3_capex_daily(72.0, params);
end

function cost = baseline_grid_cost(P_base, params)
cost = 1000 * sum(params.tou_price .* P_base);
end

function cost = annualized_nh3_capex_daily(capacityTpd, params)
kgH2PerHour = 0.2 * capacityTpd * 1000 / 24;
cost = params.nh3_capex_yuan_per_kgH2_per_h * kgH2PerHour / (params.nh3_life_year * 365);
end
