from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from advanced_algorithms import pareto_filter, topsis_rank
from config import CFG, TOU_PRICE
from costs import (
    annualized_nh3_capex_daily,
    process_om_cost_for_rate,
    process_power_for_rate,
    renewable_generation_cost,
    storage_capex_daily,
)
from data_loader import build_scenarios, load_all_attachments, typical_scenario
from metrics import CLASS_ALL, CLASS_NONE, CLASS_PARTIAL, classify_metering, green_direct_metrics_metering, green_direct_metrics_statement
from optimizers import solve_continuous_on_grid, solve_discrete_on_grid
from reporting import (
    acceptance_report,
    annual_summary_for_paper,
    compare_q2_q3,
    create_figures,
    ensure_output_dirs,
    figure_index_rows,
    flexible_load_value_rows,
    hard_soft_compare_rows,
    q1_hourly_balance_rows,
    q2_all_scenarios,
    q3_all_scenarios,
    q4_no_storage_rows,
    q4_storage_capacity_scan,
    q5_policy_table,
    policy_margin_rows,
    scenario_risk_summary_rows,
    storage_2d_scan_rows,
    storage_marginal_value_rows,
    storage_trace_report_rows,
    topsis_candidates_rows,
    validate_inputs,
    write_csv,
    write_result_summary,
)


def total_cost(wind, pv, buy, sell, target_tpd, rates=None, y=None, capacity_tpd=72):
    cost_re = renewable_generation_cost(wind, pv)
    cost_buy = float(np.sum(buy * TOU_PRICE) * 1000)
    revenue = float(np.sum(sell) * CFG.feedin_yuan_per_kwh * 1000)
    if rates is not None:
        cost_proc = sum(process_om_cost_for_rate(float(r)) for r in rates)
    elif y is not None:
        cost_proc = sum(process_om_cost_for_rate(3.0) for v in y if v > 0.5)
    else:
        cost_proc = 0.0
    return cost_re + cost_buy + cost_proc + annualized_nh3_capex_daily(capacity_tpd) - revenue


def solve_row(data, sc, q, mode):
    if mode == "discrete":
        sol = solve_discrete_on_grid(data.base_load_mw, sc["renew_mw"], q)
        cost = total_cost(sc["wind_mw"], sc["pv_mw"], sol["buy_mw"], sol["sell_mw"], q, y=sol["y"])
    elif mode == "continuous":
        sol = solve_continuous_on_grid(data.base_load_mw, sc["renew_mw"], q)
        cost = total_cost(sc["wind_mw"], sc["pv_mw"], sol["buy_mw"], sol["sell_mw"], q, rates=sol["rate_tph"])
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    mt = green_direct_metrics_metering(sol["load_mw"], sc["renew_mw"], sol["buy_mw"], sol["sell_mw"])
    st = green_direct_metrics_statement(sol["load_mw"], sc["renew_mw"], sol["buy_mw"], sol["sell_mw"])
    return {
        "mode": mode,
        "scenario": sc["id"],
        "target_tpd": q,
        "total_cost_yuan": cost,
        "ton_cost_yuan_per_t": cost / q,
        **mt,
        **st,
        "class_metering": classify_metering(mt),
    }, sol


def q1_metrics(data):
    hourly = q1_hourly_balance_rows(data)
    load = np.array([r["P_load_total_MW"] for r in hourly], dtype=float)
    re = np.array([r["P_re_MW"] for r in hourly], dtype=float)
    buy = np.array([r["P_buy_MW"] for r in hourly], dtype=float)
    sell = np.array([r["P_sell_MW"] for r in hourly], dtype=float)
    mt = green_direct_metrics_metering(load, re, buy, sell)
    st = green_direct_metrics_statement(load, re, buy, sell)
    cost = total_cost(
        np.array([r["P_wind_MW"] for r in hourly], dtype=float),
        np.array([r["P_pv_MW"] for r in hourly], dtype=float),
        buy,
        sell,
        36.0,
        rates=np.full(24, CFG.nh3_rate_tph_36),
    )
    return [{
        "E_load": mt["E_load_MWh"],
        "E_re": mt["E_RE_MWh"],
        "E_buy": mt["E_buy_MWh"],
        "E_sell": mt["E_sell_MWh"],
        "E_curtail": mt["E_curtail_MWh"],
        "E_self": mt["E_self_use_MWh"],
        "R_self": mt["self_use_gen_ratio"],
        "R_green": mt["green_load_ratio"],
        "R_sell": mt["sell_ratio"],
        "statement_R_self": st["statement_self_use_ratio"],
        "pass_self": mt["pass_self"],
        "pass_green": mt["pass_green"],
        "pass_green_2030": mt["pass_green_2030"],
        "pass_sell": mt["pass_sell"],
        "class": classify_metering(mt),
        "total_cost": cost,
        "unit_cost": cost / 36.0,
    }]


def input_parameter_rows(data):
    source_by_name = {
        "wind_lcoe_yuan_per_kwh": "attachment5",
        "pv_lcoe_yuan_per_kwh": "attachment5",
        "alk_om_yuan_per_kwh": "attachment5",
        "pem_om_yuan_per_kwh": "attachment5",
        "storage_capex_yuan_per_kwh": "attachment6",
        "nh3_capex_yuan_per_kgH2_per_h": "attachment6",
        "storage_om_yuan_per_kwh": "attachment6",
        "nh3_om_yuan_per_kwh": "attachment6",
        "storage_life_year": "attachment6",
        "nh3_life_year": "attachment6",
        "storage_eta_ch": "attachment6",
        "storage_eta_dis": "attachment6",
        "storage_self_loss_per_h": "attachment6",
        "feedin_yuan_per_kwh": "attachment8",
    }
    rows = [
        {"name": key, "value": getattr(CFG, key), "source": source_by_name.get(key, "default")}
        for key in sorted(CFG.__dict__.keys())
    ]
    for hour, price in enumerate(TOU_PRICE):
        rows.append({"name": f"tou_price_h{hour:02d}", "value": float(price), "source": "attachment7"})
    if data.parameter_sources:
        for key, value in data.parameter_sources.items():
            rows.append({"name": key, "value": value, "source": "parameter_source_file"})
    return rows


def recommendation_rows(rows):
    qualified = [r for r in rows if r["class_metering"] == CLASS_ALL]
    candidates = qualified if qualified else rows
    pareto = pareto_filter(
        candidates,
        minimize_cols=("ton_cost_yuan_per_t", "sell_ratio", "E_buy_MWh"),
        maximize_cols=("self_use_gen_ratio", "green_load_ratio"),
    )
    ranked = topsis_rank(
        pareto,
        benefit_cols=("self_use_gen_ratio", "green_load_ratio"),
        cost_cols=("ton_cost_yuan_per_t", "sell_ratio", "E_buy_MWh"),
        weights=(0.25, 0.25, 0.30, 0.15, 0.05),
    )
    fields = [
        "mode",
        "scenario",
        "target_tpd",
        "class_metering",
        "total_cost_yuan",
        "ton_cost_yuan_per_t",
        "self_use_gen_ratio",
        "green_load_ratio",
        "sell_ratio",
        "E_buy_MWh",
        "E_sell_MWh",
        "E_self_use_MWh",
        "E_curtail_MWh",
        "topsis_score",
    ]
    return [{k: r[k] for k in fields} for r in ranked]


def q2_typical_tables(data, q_values):
    sc = typical_scenario(data)
    rows = []
    hourly = []
    schedules = {}
    for q in q_values:
        row, sol = solve_row(data, sc, q, "discrete")
        schedules[q] = sol
        rows.append({
            "Q_day": q,
            "H_on": int(round(q / 3.0)),
            "total_cost": row["total_cost_yuan"],
            "unit_cost": row["ton_cost_yuan_per_t"],
            "E_load": row["E_load_MWh"],
            "E_re": row["E_RE_MWh"],
            "E_buy": row["E_buy_MWh"],
            "E_sell": row["E_sell_MWh"],
            "E_curtail": row["E_curtail_MWh"],
            "E_self": row["E_self_use_MWh"],
            "R_self": row["self_use_gen_ratio"],
            "R_green": row["green_load_ratio"],
            "R_sell": row["sell_ratio"],
            "class": row["class_metering"],
            "pass_self": row["pass_self"],
            "pass_green": row["pass_green"],
            "pass_green_2030": row["pass_green_2030"],
            "pass_sell": row["pass_sell"],
            "on_hours": " ".join(str(i) for i, v in enumerate(sol["y"]) if v > 0.5),
        })
        for h in range(24):
            hourly.append({
                "Q_day": q,
                "hour": h,
                "time_label": data.times[h],
                "u_t": int(sol["y"][h]),
                "P_eha_MW": process_power_for_rate(3.0) * int(sol["y"][h]),
                "P_buy_MW": sol["buy_mw"][h],
                "P_sell_MW": sol["sell_mw"][h],
            })
    return rows, hourly, schedules


def annual_summary_legacy(rows, mode, q_values):
    out = []
    for q in q_values:
        items = [r for r in rows if r["mode"] == mode and r["target_tpd"] == q]
        out.append({
            "Q": q,
            "avg_ton_cost": _mean(items, "ton_cost_yuan_per_t"),
            "all": sum(1 for r in items if r["class_metering"] == CLASS_ALL),
            "partial": sum(1 for r in items if r["class_metering"] == CLASS_PARTIAL),
            "none": sum(1 for r in items if r["class_metering"] == CLASS_NONE),
            "mean_self_use_gen": _mean(items, "self_use_gen_ratio"),
            "mean_green_load": _mean(items, "green_load_ratio"),
            "mean_sell_ratio": _mean(items, "sell_ratio"),
            "mean_buy": _mean(items, "E_buy_MWh"),
            "mean_sell": _mean(items, "E_sell_MWh"),
        })
    return out


def q4_derived_tables(q4_no_storage, q3_rows):
    max_row = max(q4_no_storage, key=lambda r: r["curtail_MWh"])
    scan = q4_storage_capacity_scan(max_row)
    best_scan = min([r for r in scan if not np.isnan(r["storage_unit_cost_yuan_per_t"])], key=lambda r: r["storage_unit_cost_yuan_per_t"])
    with_storage = []
    for r in q4_no_storage:
        recovered = min(r["curtail_MWh"] * 0.8, best_scan["E_cap_MWh"] * CFG.storage_eta_ch * CFG.storage_eta_dis)
        nh3_gain = recovered / process_power_for_rate(1.0)
        with_storage.append({
            "scenario_id": r["scenario_id"],
            "E_cap_MWh": best_scan["E_cap_MWh"],
            "daily_NH3_t": r["daily_NH3_t"] + nh3_gain,
            "curtail_MWh": max(r["curtail_MWh"] - recovered, 0),
            "unserved_base_MWh": r["unserved_base_MWh"],
            "storage_recovered_MWh": recovered,
        })
    annual = [{
        "E_cap_MWh": best_scan["E_cap_MWh"],
        "annual_days": len(with_storage) * 15,
        "annual_NH3_t": sum(r["daily_NH3_t"] for r in with_storage) * 15,
        "annual_storage_cost": storage_capex_daily(best_scan["E_cap_MWh"]) * len(with_storage) * 15,
    }]
    grid_cost_by_scenario = {}
    for r in q3_rows:
        if r["Q_day"] == 72:
            grid_cost_by_scenario[r["scenario_id"]] = r["unit_cost"]
    grid_vs = []
    storage_daily_cost = storage_capex_daily(best_scan["E_cap_MWh"])
    for r in with_storage:
        off_cost = storage_daily_cost / r["daily_NH3_t"] if r["daily_NH3_t"] > 0 else np.nan
        grid_cost = grid_cost_by_scenario.get(r["scenario_id"], np.nan)
        grid_vs.append({
            "scenario_id": r["scenario_id"],
            "offgrid_daily_NH3_t": r["daily_NH3_t"],
            "offgrid_unit_cost": off_cost,
            "grid_connected_unit_cost": grid_cost,
            "grid_support_value": off_cost - grid_cost if not np.isnan(grid_cost) else np.nan,
        })
    return scan, with_storage, annual, grid_vs


def run(data_dir, out_dir):
    out, tables, figures = ensure_output_dirs(out_dir)
    data = load_all_attachments(data_dir)
    scenarios = build_scenarios(data)
    q_values = [72, 63, 54, 45, 36]

    rows = []
    schedules = {}
    for mode in ["discrete", "continuous"]:
        for sc in scenarios:
            for q in q_values:
                row, sol = solve_row(data, sc, q, mode)
                rows.append(row)
                schedules[(mode, sc["id"], q)] = sol

    q1_hourly = q1_hourly_balance_rows(data)
    q1_metric_rows = q1_metrics(data)
    q2_typical, q2_typical_hourly, _ = q2_typical_tables(data, q_values)
    q2_rows = q2_all_scenarios(rows, schedules)
    q3_rows = q3_all_scenarios(rows, schedules)
    q2_annual = annual_summary_for_paper(q2_rows)
    q3_annual = annual_summary_for_paper(q3_rows)
    q3_vs_q2 = compare_q2_q3(q2_rows, q3_rows)
    q4_no_storage = q4_no_storage_rows(data, scenarios)
    q4_scan, q4_with_storage, q4_storage_annual, q4_grid_vs = q4_derived_tables(q4_no_storage, q3_rows)
    policy_margin = policy_margin_rows(q2_rows, "discrete") + policy_margin_rows(q3_rows, "continuous")
    scenario_risk = scenario_risk_summary_rows(q2_rows, "discrete") + scenario_risk_summary_rows(q3_rows, "continuous")
    flexible_value = flexible_load_value_rows(q3_vs_q2)
    storage_2d = storage_2d_scan_rows(q4_scan)
    storage_marginal = storage_marginal_value_rows(q4_scan)
    storage_trace = storage_trace_report_rows(q4_with_storage)
    topsis_candidates = topsis_candidates_rows(q2_annual, q3_annual, q4_storage_annual, q4_grid_vs)
    hard_soft = hard_soft_compare_rows(rows)

    table_files = {
        "input_parameters_v2.csv": input_parameter_rows(data),
        "data_validation_report.csv": validate_inputs(data),
        "q1_hourly_balance.csv": q1_hourly,
        "q1_metrics.csv": q1_metric_rows,
        "q2_typical_by_production.csv": q2_typical,
        "q2_typical_hourly_schedule.csv": q2_typical_hourly,
        "q2_all_scenarios.csv": q2_rows,
        "q2_annual_summary.csv": q2_annual,
        "q3_all_scenarios.csv": q3_rows,
        "q3_annual_summary.csv": q3_annual,
        "q3_compare_q2.csv": q3_vs_q2,
        "q4_offgrid_no_storage.csv": q4_no_storage,
        "q4_storage_capacity_scan.csv": q4_scan,
        "q4_offgrid_with_storage.csv": q4_with_storage,
        "q4_storage_annual_summary.csv": q4_storage_annual,
        "q4_grid_vs_offgrid.csv": q4_grid_vs,
        "grid_support_value.csv": q4_grid_vs,
        "policy_margin_heatmap.csv": policy_margin,
        "scenario_risk_summary.csv": scenario_risk,
        "flexible_load_value.csv": flexible_value,
        "storage_2d_scan.csv": storage_2d,
        "storage_marginal_value.csv": storage_marginal,
        "storage_trace_report.csv": storage_trace,
        "topsis_candidates.csv": topsis_candidates,
        "hard_soft_compare.csv": hard_soft,
        "figure_index.csv": figure_index_rows(),
        "acceptance_report.csv": acceptance_report(q1_hourly, q2_rows, q3_rows),
        "pareto_topsis_recommendations_v2_metering.csv": recommendation_rows(rows),
        "all_results_v2_metering.csv": rows,
    }
    for name, data_rows in table_files.items():
        write_csv(tables / name, data_rows)
        print(f"Saved {tables / name}")

    # Backward-compatible root-level outputs used by earlier iterations.
    write_csv(out / "all_results_v2_metering.csv", rows)
    write_csv(out / "q1_summary_v2_metering.csv", _legacy_q1(q1_metric_rows))
    write_csv(out / "q2_discrete_annual_summary_v2_metering.csv", annual_summary_legacy(rows, "discrete", q_values))
    write_csv(out / "q3_continuous_annual_summary_v2_metering.csv", annual_summary_legacy(rows, "continuous", q_values))
    write_csv(out / "pareto_topsis_recommendations_v2_metering.csv", recommendation_rows(rows))

    q5_policy_table(tables / "q5_policy_impact_table.md")
    summary_path = write_result_summary(
        tables / "result_summary_for_paper",
        {
            "q1_metrics": q1_metric_rows,
            "q2_typical": q2_typical,
            "q2_annual": q2_annual,
            "q3_annual": q3_annual,
            "q3_vs_q2": q3_vs_q2,
            "q4_no_storage": q4_no_storage,
            "q4_storage": q4_with_storage,
            "q4_grid_vs_offgrid": q4_grid_vs,
            "policy_margin": policy_margin,
            "scenario_risk": scenario_risk,
            "flexible_value": flexible_value,
            "storage_2d_scan": storage_2d,
            "storage_marginal": storage_marginal,
            "storage_trace": storage_trace,
            "topsis_candidates": topsis_candidates,
            "hard_soft": hard_soft,
            "figure_index": figure_index_rows(),
        },
    )
    print(f"Saved {summary_path}")

    create_figures(
        figures,
        data,
        q1_hourly,
        q1_metric_rows,
        q2_rows,
        q2_annual,
        q3_rows,
        q3_annual,
        q3_vs_q2,
        q4_no_storage,
        q4_scan,
        policy_margin,
        storage_2d,
        topsis_candidates,
    )


def _legacy_q1(q1_rows):
    r = q1_rows[0]
    return [{
        "E_load_MWh": r["E_load"],
        "E_RE_MWh": r["E_re"],
        "E_buy_MWh": r["E_buy"],
        "E_sell_MWh": r["E_sell"],
        "E_curtail_MWh": r["E_curtail"],
        "E_self_MWh": r["E_self"],
        "self_use_gen_ratio_metering": r["R_self"],
        "green_load_ratio_metering": r["R_green"],
        "sell_ratio": r["R_sell"],
        "statement_self_ratio_for_check": r["statement_R_self"],
        "ton_cost_yuan_per_t": r["unit_cost"],
        "qualification_metering": r["class"],
    }]


def _mean(rows, key):
    return float(np.mean([float(r[key]) for r in rows])) if rows else float("nan")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="data")
    ap.add_argument("--out_dir", default="./outputs")
    args = ap.parse_args()
    run(args.data_dir, args.out_dir)
