from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from advanced_algorithms import monte_carlo_kmeans_scenario_design, pareto_filter, topsis_rank
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
from optimizers import estimate_min_capacity_hourly, solve_offgrid_storage_dispatch
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


def total_cost(wind, pv, buy, sell, target_tpd, rates=None, y=None, capacity_tpd=None):
    if capacity_tpd is None:
        capacity_tpd = target_tpd
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


def baseline_grid_cost(base_load_mw):
    return float(np.sum(np.asarray(base_load_mw, dtype=float) * TOU_PRICE) * 1000)


def solve_row(data, sc, q, mode):
    installed_capacity_tpd = 72.0
    if mode == "discrete":
        sol = solve_discrete_on_grid(data.base_load_mw, sc["renew_mw"], q)
        cost = total_cost(sc["wind_mw"], sc["pv_mw"], sol["buy_mw"], sol["sell_mw"], q, y=sol["y"], capacity_tpd=installed_capacity_tpd)
    elif mode == "continuous":
        sol = solve_continuous_on_grid(data.base_load_mw, sc["renew_mw"], q)
        cost = total_cost(sc["wind_mw"], sc["pv_mw"], sol["buy_mw"], sol["sell_mw"], q, rates=sol["rate_tph"], capacity_tpd=installed_capacity_tpd)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    mt = green_direct_metrics_metering(sol["load_mw"], sc["renew_mw"], sol["buy_mw"], sol["sell_mw"])
    st = green_direct_metrics_statement(sol["load_mw"], sc["renew_mw"], sol["buy_mw"], sol["sell_mw"])
    baseline_cost = baseline_grid_cost(data.base_load_mw)
    return {
        "mode": mode,
        "scenario": sc["id"],
        "target_tpd": q,
        "total_cost_yuan": cost,
        "incremental_total_cost_yuan": cost - baseline_cost,
        "ton_cost_yuan_per_t": cost / q,
        "incremental_ton_cost_yuan_per_t": (cost - baseline_cost) / q,
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
        capacity_tpd=36.0,
    )
    baseline_cost = baseline_grid_cost(data.base_load_mw)
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
        "baseline_grid_cost": baseline_cost,
        "nh3_capex_daily": annualized_nh3_capex_daily(36.0),
        "total_cost": cost,
        "incremental_total_cost": cost - baseline_cost,
        "unit_cost": cost / 36.0,
        "incremental_unit_cost": (cost - baseline_cost) / 36.0,
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
        "incremental_total_cost_yuan",
        "ton_cost_yuan_per_t",
        "incremental_ton_cost_yuan_per_t",
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
            "incremental_total_cost": row["incremental_total_cost_yuan"],
            "unit_cost": row["ton_cost_yuan_per_t"],
            "incremental_unit_cost": row["incremental_ton_cost_yuan_per_t"],
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
            "avg_incremental_ton_cost": _mean(items, "incremental_ton_cost_yuan_per_t"),
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


def q4_storage_optimized_tables(data, scenarios, q4_no_storage, q3_rows):
    max_row = max(q4_no_storage, key=lambda r: r["curtail_MWh"])
    scenario_by_id = {sc["id"]: sc for sc in scenarios}
    worst_sc = scenario_by_id[max_row["scenario_id"]]
    scan = q4_storage_capacity_scan_optimized(data, worst_sc)
    feasible_scan = [
        r for r in scan
        if float(r["E_cap_MWh"]) > 0
        and float(r["delta_NH3_t"]) > 1e-6
        and np.isfinite(float(r["incremental_storage_cost_yuan_per_added_t"]))
    ]
    if not feasible_scan:
        feasible_scan = [r for r in scan if np.isfinite(float(r["storage_unit_cost_yuan_per_t"]))]
    best_scan = min(
        feasible_scan,
        key=lambda r: (float(r.get("incremental_storage_cost_yuan_per_added_t", np.inf)), -float(r["daily_NH3_t"])),
    )
    e_cap = float(best_scan["E_cap_MWh"])
    p_cap = float(best_scan["P_cap_MW"])

    with_storage = []
    hourly = []
    no_storage_by_id = {r["scenario_id"]: r for r in q4_no_storage}
    for sc in scenarios:
        sol = solve_offgrid_storage_dispatch(data.base_load_mw, sc["renew_mw"], e_cap, p_cap)
        base = no_storage_by_id[sc["id"]]
        daily_nh3 = float(sol["daily_nh3_t"])
        curtail = float(np.sum(sol["curtail_mwh"]))
        unserved = float(np.sum(sol["deficit_mwh"]))
        storage_daily_cost = storage_capex_daily(e_cap) + float(np.sum(sol["charge_mw"])) * 1000 * CFG.storage_om_yuan_per_kwh
        proc_daily_cost = sum(process_om_cost_for_rate(float(r)) for r in sol["rate_tph"])
        re_daily_cost = renewable_generation_cost(sc["wind_mw"], sc["pv_mw"])
        total_daily_cost = storage_daily_cost + proc_daily_cost + re_daily_cost + annualized_nh3_capex_daily(72.0)
        with_storage.append({
            "scenario_id": sc["id"],
            "E_cap_MWh": e_cap,
            "P_cap_MW": p_cap,
            "daily_NH3_t": daily_nh3,
            "avg_rate_tph": daily_nh3 / 24.0,
            "curtail_MWh": curtail,
            "unserved_base_MWh": unserved,
            "storage_charge_MWh": float(np.sum(sol["charge_mw"])),
            "storage_discharge_MWh": float(np.sum(sol["discharge_mw"])),
            "storage_recovered_MWh": float(np.sum(sol["discharge_mw"])),
            "delta_NH3_t": daily_nh3 - float(base["daily_NH3_t"]),
            "curtail_reduction_MWh": float(base["curtail_MWh"]) - curtail,
            "max_SOC_MWh": float(np.max(sol["soc_mwh"])),
            "daily_total_cost": total_daily_cost,
            "offgrid_unit_cost": total_daily_cost / daily_nh3 if daily_nh3 > 0 else np.nan,
        })
        for h in range(24):
            hourly.append({
                "scenario_id": sc["id"],
                "hour": h,
                "time_label": data.times[h],
                "P_base_MW": data.base_load_mw[h],
                "P_re_MW": sc["renew_mw"][h],
                "rate_tph": sol["rate_tph"][h],
                "P_process_MW": sol["proc_power_mw"][h],
                "P_charge_MW": sol["charge_mw"][h],
                "P_discharge_MW": sol["discharge_mw"][h],
                "SOC_MWh": sol["soc_mwh"][h],
                "P_curtail_MW": sol["curtail_mwh"][h],
                "P_unserved_MW": sol["deficit_mwh"][h],
                "balance_residual_MW": sc["renew_mw"][h] + sol["discharge_mw"][h] + sol["deficit_mwh"][h]
                    - data.base_load_mw[h] - sol["proc_power_mw"][h] - sol["charge_mw"][h] - sol["curtail_mwh"][h],
            })

    annual = [{
        "E_cap_MWh": e_cap,
        "P_cap_MW": p_cap,
        "design_scenario_id": max_row["scenario_id"],
        "annual_days": len(with_storage) * 15,
        "annual_NH3_t": sum(r["daily_NH3_t"] for r in with_storage) * 15,
        "annual_total_cost": sum(r["daily_total_cost"] for r in with_storage) * 15,
        "annual_storage_cost": (storage_capex_daily(e_cap) * len(with_storage) * 15)
            + sum(r["storage_charge_MWh"] * 1000 * CFG.storage_om_yuan_per_kwh for r in with_storage) * 15,
        "mean_delta_NH3_t": float(np.mean([r["delta_NH3_t"] for r in with_storage])),
        "mean_curtail_reduction_MWh": float(np.mean([r["curtail_reduction_MWh"] for r in with_storage])),
        "annual_average_unit_cost": (
            sum(r["daily_total_cost"] for r in with_storage) * 15
            / max(sum(r["daily_NH3_t"] for r in with_storage) * 15, 1e-9)
        ),
    }]

    grid_cost_by_scenario = {}
    for r in q3_rows:
        if r["Q_day"] == 72:
            grid_cost_by_scenario[r["scenario_id"]] = r["unit_cost"]
    grid_vs = []
    for r in with_storage:
        off_cost = r["offgrid_unit_cost"]
        grid_cost = grid_cost_by_scenario.get(r["scenario_id"], np.nan)
        grid_vs.append({
            "scenario_id": r["scenario_id"],
            "offgrid_daily_NH3_t": r["daily_NH3_t"],
            "offgrid_unit_cost": off_cost,
            "grid_connected_unit_cost": grid_cost,
            "grid_support_value": off_cost - grid_cost if not np.isnan(grid_cost) else np.nan,
        })
    return scan, with_storage, annual, grid_vs, hourly


def q4_storage_capacity_scan_optimized(data, scenario):
    no_storage = q4_no_storage_rows(data, [scenario])[0]
    base_curtail = float(no_storage["curtail_MWh"])
    if base_curtail <= 0:
        candidates = [0.0]
    else:
        step = 10.0
        candidates = list(np.arange(0.0, np.ceil(base_curtail / step) * step + step, step))
    rows = []
    for e_cap in candidates:
        p_cap = e_cap / 4.0 if e_cap > 0 else 0.0
        sol = solve_offgrid_storage_dispatch(data.base_load_mw, scenario["renew_mw"], e_cap, p_cap)
        charge = float(np.sum(sol["charge_mw"]))
        daily_nh3 = float(sol["daily_nh3_t"])
        cost = storage_capex_daily(e_cap) + charge * 1000 * CFG.storage_om_yuan_per_kwh
        rows.append({
            "design_scenario_id": scenario["id"],
            "E_cap_MWh": float(e_cap),
            "P_cap_MW": float(p_cap),
            "duration_h": float(e_cap / p_cap) if p_cap > 0 else np.nan,
            "daily_NH3_t": daily_nh3,
            "delta_NH3_t": daily_nh3 - float(no_storage["daily_NH3_t"]),
            "curtail_MWh": float(np.sum(sol["curtail_mwh"])),
            "curtail_reduction_MWh": float(no_storage["curtail_MWh"]) - float(np.sum(sol["curtail_mwh"])),
            "storage_charge_MWh": charge,
            "storage_discharge_MWh": float(np.sum(sol["discharge_mw"])),
            "max_SOC_MWh": float(np.max(sol["soc_mwh"])),
            "unserved_base_MWh": float(np.sum(sol["deficit_mwh"])),
            "storage_daily_cost": float(cost),
            "storage_unit_cost_yuan_per_t": float(cost / daily_nh3) if daily_nh3 > 0 else np.nan,
            "incremental_storage_cost_yuan_per_added_t": float(cost / (daily_nh3 - float(no_storage["daily_NH3_t"])))
                if daily_nh3 > float(no_storage["daily_NH3_t"]) + 1e-9 else np.nan,
        })
    return rows


def q4_storage_design_recommendations(scan_rows):
    positive = [
        r for r in scan_rows
        if float(r["E_cap_MWh"]) > 0
        and float(r["delta_NH3_t"]) > 1e-6
        and np.isfinite(float(r["incremental_storage_cost_yuan_per_added_t"]))
    ]
    if not positive:
        return []

    picks = [
        ("economic_min_incremental_cost", min(positive, key=lambda r: float(r["incremental_storage_cost_yuan_per_added_t"]))),
        ("max_daily_NH3", max(positive, key=lambda r: float(r["daily_NH3_t"]))),
        ("max_curtailment_reduction", max(positive, key=lambda r: float(r["curtail_reduction_MWh"]))),
    ]
    max_reduction = max(float(r["curtail_reduction_MWh"]) for r in positive)
    knee = min(
        [r for r in positive if float(r["curtail_reduction_MWh"]) >= 0.90 * max_reduction],
        key=lambda r: float(r["E_cap_MWh"]),
    )
    picks.append(("smallest_capacity_for_90pct_curtailment_reduction", knee))

    out = []
    seen = set()
    for label, r in picks:
        key = (label, float(r["E_cap_MWh"]), float(r["P_cap_MW"]))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "recommendation_type": label,
            "design_scenario_id": r["design_scenario_id"],
            "E_cap_MWh": r["E_cap_MWh"],
            "P_cap_MW": r["P_cap_MW"],
            "duration_h": r["duration_h"],
            "daily_NH3_t": r["daily_NH3_t"],
            "delta_NH3_t": r["delta_NH3_t"],
            "curtail_reduction_MWh": r["curtail_reduction_MWh"],
            "storage_daily_cost": r["storage_daily_cost"],
            "incremental_storage_cost_yuan_per_added_t": r["incremental_storage_cost_yuan_per_added_t"],
            "interpretation": _storage_recommendation_text(label),
        })
    return out


def _storage_recommendation_text(label):
    text = {
        "economic_min_incremental_cost": "lowest marginal storage cost per added ton of ammonia; use as the cost-first design",
        "max_daily_NH3": "highest off-grid ammonia output in the scanned storage range",
        "max_curtailment_reduction": "largest renewable curtailment reduction in the scanned storage range",
        "smallest_capacity_for_90pct_curtailment_reduction": "smallest storage capacity that captures at least 90% of the maximum achievable curtailment reduction",
    }
    return text.get(label, "")


def q4_min_capacity_rows(data):
    unconstrained = estimate_min_capacity_hourly(data.base_load_mw, data.wind_scen_pu, data.pv_scen_pu, keep_ratio=False)
    proportional = estimate_min_capacity_hourly(data.base_load_mw, data.wind_scen_pu, data.pv_scen_pu, keep_ratio=True)
    return [
        {
            "method": "LP_min_total_wind_pv_capacity",
            "wind_MW": unconstrained["wind_mw"],
            "pv_MW": unconstrained["pv_mw"],
            "total_MW": unconstrained["sum_mw"],
            "scale_vs_current": unconstrained["sum_mw"] / (CFG.wind_cap_mw + CFG.pv_cap_mw),
            "note": "minimize wind_MW + pv_MW while meeting base load plus full 72 t/d process load in all 24 scenarios",
        },
        {
            "method": "fixed_wind_pv_ratio_scale",
            "wind_MW": proportional["wind_mw"],
            "pv_MW": proportional["pv_mw"],
            "total_MW": proportional["wind_mw"] + proportional["pv_mw"],
            "scale_vs_current": proportional["scale"],
            "note": "keep 40:64 wind/PV ratio and scale until all hours and scenarios are self-sufficient",
        },
    ]


def stochastic_representative_rows(data):
    design = monte_carlo_kmeans_scenario_design(
        data.wind_scen_pu,
        data.pv_scen_pu,
        n_samples=1200,
        n_clusters=8,
        random_state=2026,
    )
    rows = []
    for i, prob in enumerate(design["probability"], 1):
        wind = CFG.wind_cap_mw * design["wind_pu"][i - 1]
        pv = CFG.pv_cap_mw * design["pv_pu"][i - 1]
        sol = solve_continuous_on_grid(data.base_load_mw, wind + pv, 72)
        mt = green_direct_metrics_metering(sol["load_mw"], wind + pv, sol["buy_mw"], sol["sell_mw"])
        cost = total_cost(wind, pv, sol["buy_mw"], sol["sell_mw"], 72, rates=sol["rate_tph"])
        rows.append({
            "cluster_id": i,
            "probability": float(prob),
            "expected_days": float(prob * 360),
            "daily_NH3_t": 72,
            "unit_cost": cost / 72,
            "R_self": mt["self_use_gen_ratio"],
            "R_green": mt["green_load_ratio"],
            "R_sell": mt["sell_ratio"],
            "class": classify_metering(mt),
            "E_buy_MWh": mt["E_buy_MWh"],
            "E_sell_MWh": mt["E_sell_MWh"],
            "wind_mean_pu": float(np.mean(design["wind_pu"][i - 1])),
            "pv_mean_pu": float(np.mean(design["pv_pu"][i - 1])),
        })
    return rows


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
    q4_scan, q4_with_storage, q4_storage_annual, q4_grid_vs, q4_storage_hourly = q4_storage_optimized_tables(
        data,
        scenarios,
        q4_no_storage,
        q3_rows,
    )
    q4_storage_recommendations = q4_storage_design_recommendations(q4_scan)
    q4_min_capacity = q4_min_capacity_rows(data)
    stochastic_rows = stochastic_representative_rows(data)
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
        "q4_storage_hourly_dispatch.csv": q4_storage_hourly,
        "q4_storage_annual_summary.csv": q4_storage_annual,
        "q4_storage_design_recommendations.csv": q4_storage_recommendations,
        "q4_minimum_capacity.csv": q4_min_capacity,
        "q4_grid_vs_offgrid.csv": q4_grid_vs,
        "grid_support_value.csv": q4_grid_vs,
        "stochastic_representative_scenarios.csv": stochastic_rows,
        "policy_margin_heatmap.csv": policy_margin,
        "scenario_risk_summary.csv": scenario_risk,
        "flexible_load_value.csv": flexible_value,
        "storage_2d_scan.csv": storage_2d,
        "storage_marginal_value.csv": storage_marginal,
        "storage_trace_report.csv": storage_trace,
        "topsis_candidates.csv": topsis_candidates,
        "hard_soft_compare.csv": hard_soft,
        "figure_index.csv": figure_index_rows(),
        "acceptance_report.csv": acceptance_report(q1_hourly, q2_rows, q3_rows, q4_with_storage, q4_storage_hourly, stochastic_rows),
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
            "q4_storage_hourly": q4_storage_hourly,
            "q4_storage_designs": q4_storage_recommendations,
            "q4_min_capacity": q4_min_capacity,
            "q4_grid_vs_offgrid": q4_grid_vs,
            "stochastic_scenarios": stochastic_rows,
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
        q4_with_storage,
        q4_storage_hourly,
        q4_grid_vs,
        q4_min_capacity,
        stochastic_rows,
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
        "incremental_ton_cost_yuan_per_t": r["incremental_unit_cost"],
        "baseline_grid_cost": r["baseline_grid_cost"],
        "nh3_capex_daily": r["nh3_capex_daily"],
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
