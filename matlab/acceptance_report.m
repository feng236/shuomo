function rows = acceptance_report(q1Hourly, q2, q3, q4WithStorage, q4Hourly, stochasticRows)
if nargin < 4, q4WithStorage = table(); end
if nargin < 5, q4Hourly = table(); end
if nargin < 6, stochasticRows = table(); end
balance = q1Hourly.P_re_MW + q1Hourly.P_buy_MW - q1Hourly.P_load_total_MW - q1Hourly.P_sell_MW;
identityGap = max(abs([q2.E_self; q3.E_self] - ([q2.E_re; q3.E_re] - [q2.E_sell; q3.E_sell] - [q2.E_curtail; q3.E_curtail])));
if height(q4Hourly) > 0
    q4Balance = max(abs(q4Hourly.balance_residual_MW));
else
    q4Balance = inf;
end
if height(q4WithStorage) > 0
    hasStorage = any(q4WithStorage.E_cap_MWh > 0);
    improvesStorage = any(q4WithStorage.delta_NH3_t > 1e-6);
else
    hasStorage = false;
    improvesStorage = false;
end
if height(stochasticRows) > 0
    stochasticProb = sum(stochasticRows.probability);
else
    stochasticProb = NaN;
end
rows = table(["q1_hourly_rows";"q2_rows";"q3_rows";"q1_power_balance";"metering_E_self_identity"; ...
        "q4_storage_rows";"q4_storage_hourly_rows";"q4_storage_power_balance";"q4_storage_nonzero_capacity"; ...
        "q4_storage_improves_NH3";"stochastic_representative_rows";"stochastic_probability_sum"], ...
    ["OK"; status_of(height(q2) == 120); status_of(height(q3) == 120); status_of(max(abs(balance)) < 1e-6); status_of(identityGap < 1e-6); ...
        status_of(height(q4WithStorage) == 24); status_of(height(q4Hourly) == 576); status_of(q4Balance < 1e-6); ...
        status_of(hasStorage); status_of(improvesStorage); status_of(height(stochasticRows) == 8); status_of(abs(stochasticProb - 1.0) < 1e-9)], ...
    [height(q1Hourly); height(q2); height(q3); max(abs(balance)); identityGap; height(q4WithStorage); height(q4Hourly); q4Balance; ...
        double(hasStorage); double(improvesStorage); height(stochasticRows); stochasticProb], ...
    ["24";"120";"120";"<1e-6";"E_self=E_re-E_sell-E_curtail";"24";"576";"<1e-6";"true";"true";"8";"1.0"], ...
    VariableNames=["check","status","value","expected"]);
end

function s = status_of(flag)
if flag
    s = "OK";
else
    s = "FAIL";
end
end
