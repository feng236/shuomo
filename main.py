from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from advanced_algorithms import pareto_filter, topsis_rank
from config import CFG, TOU_PRICE
from costs import (
    annualized_nh3_capex_daily,
    process_om_cost_for_rate,
    process_power_for_rate,
    renewable_generation_cost,
)
from data_loader import build_scenarios, load_all_attachments, typical_scenario
from metrics import green_direct_metrics_metering, green_direct_metrics_statement, classify_metering
from optimizers import solve_continuous_on_grid, solve_discrete_on_grid


CLASS_ALL = classify_metering({"self_use_gen_ratio": 1.0, "green_load_ratio": 1.0, "sell_ratio": 0.0})
CLASS_PARTIAL = classify_metering({"self_use_gen_ratio": 1.0, "green_load_ratio": 0.0, "sell_ratio": 0.0})
CLASS_NONE = classify_metering({"self_use_gen_ratio": 0.0, "green_load_ratio": 0.0, "sell_ratio": 1.0})


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
        cost = total_cost(
            sc["wind_mw"],
            sc["pv_mw"],
            sol["buy_mw"],
            sol["sell_mw"],
            q,
            rates=sol["rate_tph"],
        )
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
    }


def q1_typical_summary(data):
    sc = typical_scenario(data)
    target_tpd = 36.0
    rate_tph = CFG.nh3_rate_tph_36
    load = data.base_load_mw + process_power_for_rate(rate_tph)
    buy = np.maximum(load - sc["renew_mw"], 0)
    sell = np.maximum(sc["renew_mw"] - load, 0)
    mt = green_direct_metrics_metering(load, sc["renew_mw"], buy, sell)
    st = green_direct_metrics_statement(load, sc["renew_mw"], buy, sell)
    cost = total_cost(
        sc["wind_mw"],
        sc["pv_mw"],
        buy,
        sell,
        target_tpd,
        rates=np.full(24, rate_tph),
    )
    return [{
        "E_load_MWh": mt["E_load_MWh"],
        "E_RE_MWh": mt["E_RE_MWh"],
        "E_buy_MWh": mt["E_buy_MWh"],
        "E_sell_MWh": mt["E_sell_MWh"],
        "self_use_gen_ratio_metering": mt["self_use_gen_ratio"],
        "green_load_ratio_metering": mt["green_load_ratio"],
        "sell_ratio": mt["sell_ratio"],
        "statement_self_ratio_for_check": st["statement_self_use_ratio"],
        "ton_cost_yuan_per_t": cost / target_tpd,
        "qualification_metering": classify_metering(mt),
    }]


def annual_summary(rows, mode, q_values):
    grouped = defaultdict(list)
    for row in rows:
        if row["mode"] == mode:
            grouped[row["target_tpd"]].append(row)

    out = []
    for q in q_values:
        items = grouped[q]
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
        "topsis_score",
    ]
    return [{k: r[k] for k in fields} for r in ranked]


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


def write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _mean(rows, key):
    return float(np.mean([float(r[key]) for r in rows])) if rows else float("nan")


def run(data_dir, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_all_attachments(data_dir)
    scenarios = build_scenarios(data)
    q_values = [72, 63, 54, 45, 36]
    rows = []
    for mode in ["discrete", "continuous"]:
        for sc in scenarios:
            for q in q_values:
                rows.append(solve_row(data, sc, q, mode))

    files = [
        (out / "input_parameters_v2.csv", input_parameter_rows(data)),
        (out / "q1_summary_v2_metering.csv", q1_typical_summary(data)),
        (out / "all_results_v2_metering.csv", rows),
        (out / "q2_discrete_annual_summary_v2_metering.csv", annual_summary(rows, "discrete", q_values)),
        (out / "q3_continuous_annual_summary_v2_metering.csv", annual_summary(rows, "continuous", q_values)),
        (out / "pareto_topsis_recommendations_v2_metering.csv", recommendation_rows(rows)),
    ]
    for path, data_rows in files:
        write_csv(path, data_rows)
        print(f"Saved {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--out_dir", default="./outputs")
    args = ap.parse_args()
    run(args.data_dir, args.out_dir)
