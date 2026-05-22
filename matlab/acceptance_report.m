function rows = acceptance_report(q1Hourly, q2, q3)
balance = q1Hourly.P_re_MW + q1Hourly.P_buy_MW - q1Hourly.P_load_total_MW - q1Hourly.P_sell_MW;
identityGap = max(abs([q2.E_self; q3.E_self] - ([q2.E_re; q3.E_re] - [q2.E_sell; q3.E_sell] - [q2.E_curtail; q3.E_curtail])));
rows = table(["q1_hourly_rows";"q2_rows";"q3_rows";"q1_power_balance";"metering_E_self_identity"], ...
    ["OK"; status_of(height(q2) == 120); status_of(height(q3) == 120); status_of(max(abs(balance)) < 1e-6); status_of(identityGap < 1e-6)], ...
    [height(q1Hourly); height(q2); height(q3); max(abs(balance)); identityGap], ...
    ["24";"120";"120";"<1e-6";"E_self=E_re-E_sell-E_curtail"], ...
    VariableNames=["check","status","value","expected"]);
end

function s = status_of(flag)
if flag
    s = "OK";
else
    s = "FAIL";
end
end
