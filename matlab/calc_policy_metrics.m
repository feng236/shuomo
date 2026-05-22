function m = calc_policy_metrics(P_load_total, P_re, P_buy, P_sell, P_curtail, params)
%CALC_POLICY_METRICS Correct metering boundary indicators.
if nargin < 5 || isempty(P_curtail)
    P_curtail = zeros(size(P_re));
end
dt = params.dt_h;
m.E_load = sum(P_load_total) * dt;
m.E_re = sum(P_re) * dt;
m.E_buy = sum(P_buy) * dt;
m.E_sell = sum(P_sell) * dt;
m.E_curtail = sum(P_curtail) * dt;
m.E_self = m.E_re - m.E_sell - m.E_curtail;
epsv = 1e-9;
m.R_self = m.E_self / max(m.E_re, epsv);
m.R_green = m.E_self / max(m.E_load, epsv);
m.R_sell = m.E_sell / max(m.E_re, epsv);
m.M_self = m.R_self - 0.60;
m.M_green = m.R_green - 0.30;
m.M_green_2030 = m.R_green - 0.35;
m.M_sell = 0.20 - m.R_sell;
m.pass_self = m.R_self >= 0.60 - 1e-9;
m.pass_green = m.R_green >= 0.30 - 1e-9;
m.pass_green_2030 = m.R_green >= 0.35 - 1e-9;
m.pass_sell = m.R_sell <= 0.20 + 1e-9;
cnt = double(m.pass_self) + double(m.pass_green) + double(m.pass_sell);
if cnt == 3
    m.pass_class = "全满足";
elseif cnt == 0
    m.pass_class = "全不满足";
else
    m.pass_class = "部分满足";
end
end
