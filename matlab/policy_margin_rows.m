function rows = policy_margin_rows(tbl, mode)
rows = table();
if height(tbl) == 0, return; end
rows.mode = repmat(string(mode), height(tbl), 1);
rows.scenario_id = tbl.scenario_id;
rows.Q_day = tbl.Q_day;
rows.M_self = tbl.R_self - 0.60;
rows.M_green = tbl.R_green - 0.30;
rows.M_green_2030 = tbl.R_green - 0.35;
rows.M_sell = 0.20 - tbl.R_sell;
rows.min_policy_margin = min([rows.M_self, rows.M_green, rows.M_sell], [], 2);
rows.violation_score = max(0, -rows.M_self) + max(0, -rows.M_green) + max(0, -rows.M_sell);
end
