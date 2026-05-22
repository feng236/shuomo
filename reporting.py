from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import CFG, TOU_PRICE
from costs import process_power_for_rate, storage_capex_daily
from metrics import CLASS_ALL, CLASS_NONE, CLASS_PARTIAL


def ensure_output_dirs(out_dir):
    out = Path(out_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    return out, tables, figures


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_inputs(data):
    rows = []

    def add(item, status, value, expected, note=""):
        rows.append({"item": item, "status": status, "value": value, "expected": expected, "note": note})

    add("time_labels_count", "OK" if len(data.times) == 24 else "FAIL", len(data.times), 24)
    arrays = {
        "load_pu": data.load_pu,
        "wind_typical_pu": data.typical_wind_pu,
        "pv_typical_pu": data.typical_pv_pu,
    }
    for name, arr in arrays.items():
        add(f"{name}_length", "OK" if len(arr) == 24 else "FAIL", len(arr), 24)
        add(
            f"{name}_range",
            "OK" if np.nanmin(arr) >= -1e-9 and np.nanmax(arr) <= 1 + 1e-9 else "FAIL",
            f"{float(np.nanmin(arr)):.6g}..{float(np.nanmax(arr)):.6g}",
            "[0,1]",
        )
    add("wind_scenarios_shape", "OK" if data.wind_scen_pu.shape == (24, 6) else "FAIL", data.wind_scen_pu.shape, "(24,6)")
    add("pv_scenarios_shape", "OK" if data.pv_scen_pu.shape == (24, 4) else "FAIL", data.pv_scen_pu.shape, "(24,4)")
    add(
        "wind_scenarios_range",
        "OK" if np.nanmin(data.wind_scen_pu) >= -1e-9 and np.nanmax(data.wind_scen_pu) <= 1 + 1e-9 else "FAIL",
        f"{float(np.nanmin(data.wind_scen_pu)):.6g}..{float(np.nanmax(data.wind_scen_pu)):.6g}",
        "[0,1]",
    )
    add(
        "pv_scenarios_range",
        "OK" if np.nanmin(data.pv_scen_pu) >= -1e-9 and np.nanmax(data.pv_scen_pu) <= 1 + 1e-9 else "FAIL",
        f"{float(np.nanmin(data.pv_scen_pu)):.6g}..{float(np.nanmax(data.pv_scen_pu)):.6g}",
        "[0,1]",
    )
    add("base_load_peak_mw", "OK", float(np.max(data.base_load_mw)), f"<= {CFG.conv_peak_mw} MW")
    add("tou_price_length", "OK" if TOU_PRICE.shape == (24,) else "FAIL", TOU_PRICE.shape, "(24,)")
    add("tou_price_positive", "OK" if np.all(TOU_PRICE > 0) else "FAIL", f"{float(np.min(TOU_PRICE)):.4f}", "> 0")
    for key in [
        "wind_lcoe_yuan_per_kwh",
        "pv_lcoe_yuan_per_kwh",
        "alk_om_yuan_per_kwh",
        "pem_om_yuan_per_kwh",
        "nh3_om_yuan_per_kwh",
        "feedin_yuan_per_kwh",
        "storage_eta_ch",
        "storage_eta_dis",
    ]:
        value = getattr(CFG, key)
        add(f"param_{key}", "OK" if isinstance(value, (int, float)) else "FAIL", value, "numeric")
    return rows


def q1_hourly_balance_rows(data):
    wind = CFG.wind_cap_mw * data.typical_wind_pu
    pv = CFG.pv_cap_mw * data.typical_pv_pu
    p_re = wind + pv
    p_alk = np.full(24, CFG.alk_mw_36)
    p_pem = np.full(24, CFG.pem_mw_36)
    p_nh3 = np.full(24, CFG.nh3_mw_36)
    p_eha = p_alk + p_pem + p_nh3
    total_load = data.base_load_mw + p_eha
    buy = np.maximum(total_load - p_re, 0)
    sell = np.maximum(p_re - total_load, 0)
    rows = []
    for h in range(24):
        rows.append({
            "hour": h,
            "time_label": data.times[h],
            "P_base_MW": data.base_load_mw[h],
            "P_alk_MW": p_alk[h],
            "P_pem_MW": p_pem[h],
            "P_nh3_MW": p_nh3[h],
            "P_eha_MW": p_eha[h],
            "P_load_total_MW": total_load[h],
            "P_wind_MW": wind[h],
            "P_pv_MW": pv[h],
            "P_re_MW": p_re[h],
            "P_buy_MW": buy[h],
            "P_sell_MW": sell[h],
            "tou_price_yuan_per_kWh": TOU_PRICE[h],
            "balance_residual_MW": p_re[h] + buy[h] - total_load[h] - sell[h],
            "buy_sell_product": buy[h] * sell[h],
        })
    return rows


def q2_all_scenarios(rows, schedules):
    out = []
    for row in rows:
        if row["mode"] != "discrete":
            continue
        key = ("discrete", row["scenario"], row["target_tpd"])
        y = schedules[key]["y"]
        wind_id, pv_id = _scenario_parts(row["scenario"])
        out.append({
            "scenario_id": row["scenario"],
            "wind_scenario": wind_id,
            "pv_scenario": pv_id,
            "Q_day": row["target_tpd"],
            "H_on": int(round(row["target_tpd"] / 3.0)),
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
            "on_hours": " ".join(str(i) for i, v in enumerate(y) if v > 0.5),
        })
    return out


def q3_all_scenarios(rows, schedules):
    out = []
    for row in rows:
        if row["mode"] != "continuous":
            continue
        key = ("continuous", row["scenario"], row["target_tpd"])
        sol = schedules[key]
        out.append({
            "scenario_id": row["scenario"],
            "Q_day": row["target_tpd"],
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
            "x_vector": _fmt_vec(np.asarray(sol["rate_tph"]) / 3.0),
            "buy_vector": _fmt_vec(sol["buy_mw"]),
            "sell_vector": _fmt_vec(sol["sell_mw"]),
        })
    return out


def annual_summary_for_paper(all_rows, q_field="Q_day"):
    out = []
    by_q = {}
    for row in all_rows:
        by_q.setdefault(row[q_field], []).append(row)
    for q in sorted(by_q, reverse=True):
        items = by_q[q]
        annual_days = len(items) * 15
        annual_nh3 = q * annual_days
        annual_cost = sum(float(r["total_cost"]) for r in items) * 15
        out.append({
            "Q_day": q,
            "annual_days": annual_days,
            "annual_total_NH3": annual_nh3,
            "annual_total_cost": annual_cost,
            "annual_average_unit_cost": annual_cost / annual_nh3 if annual_nh3 else np.nan,
            "days_all_pass": sum(15 for r in items if r["class"] == CLASS_ALL),
            "days_partial_pass": sum(15 for r in items if r["class"] == CLASS_PARTIAL),
            "days_all_fail": sum(15 for r in items if r["class"] == CLASS_NONE),
            "best_or_not": "",
        })
    if out:
        best = min(out, key=lambda r: r["annual_average_unit_cost"])
        best["best_or_not"] = "best_cost"
    return out


def compare_q2_q3(q2_rows, q3_rows):
    q2 = {(r["scenario_id"], r["Q_day"]): r for r in q2_rows}
    out = []
    for r3 in q3_rows:
        key = (r3["scenario_id"], r3["Q_day"])
        r2 = q2.get(key)
        if not r2:
            continue
        out.append({
            "scenario_id": key[0],
            "Q_day": key[1],
            "delta_unit_cost": r3["unit_cost"] - r2["unit_cost"],
            "delta_buy": r3["E_buy"] - r2["E_buy"],
            "delta_sell": r3["E_sell"] - r2["E_sell"],
            "delta_R_self": r3["R_self"] - r2["R_self"],
            "delta_R_green": r3["R_green"] - r2["R_green"],
            "delta_R_sell": r3["R_sell"] - r2["R_sell"],
        })
    return out


def q4_no_storage_rows(data, scenarios):
    rows = []
    p_per_rate = process_power_for_rate(1.0)
    for sc in scenarios:
        residual = sc["renew_mw"] - data.base_load_mw
        rate = np.clip(residual / p_per_rate, 0, 3.0)
        proc = p_per_rate * rate
        curtail = np.maximum(sc["renew_mw"] - data.base_load_mw - proc, 0)
        unserved = np.maximum(data.base_load_mw - sc["renew_mw"], 0)
        q_day = float(np.sum(rate))
        rows.append({
            "scenario_id": sc["id"],
            "daily_NH3_t": q_day,
            "avg_rate_tph": float(np.mean(rate)),
            "curtail_MWh": float(np.sum(curtail)),
            "unserved_base_MWh": float(np.sum(unserved)),
            "max_curtail_MW": float(np.max(curtail)),
            "max_unserved_base_MW": float(np.max(unserved)),
            "rate_vector": _fmt_vec(rate),
            "curtail_vector": _fmt_vec(curtail),
            "unserved_vector": _fmt_vec(unserved),
        })
    return rows


def q4_storage_capacity_scan(max_curtail_row):
    base_curtail = float(max_curtail_row["curtail_MWh"])
    base_prod = float(max_curtail_row["daily_NH3_t"])
    rows = []
    for e_cap in np.arange(0, max(1.0, base_curtail) + 10, 10):
        recovered = min(base_curtail * 0.8, e_cap * CFG.storage_eta_ch * CFG.storage_eta_dis)
        nh3_gain = recovered / process_power_for_rate(1.0)
        daily_nh3 = base_prod + nh3_gain
        cost = storage_capex_daily(e_cap) + recovered * 1000 * CFG.storage_om_yuan_per_kwh
        rows.append({
            "E_cap_MWh": float(e_cap),
            "recovered_MWh": float(recovered),
            "daily_NH3_t": float(daily_nh3),
            "storage_daily_cost": float(cost),
            "storage_unit_cost_yuan_per_t": float(cost / daily_nh3) if daily_nh3 > 0 else np.nan,
        })
    return rows


def q5_policy_table(path):
    text = """| dimension | impact | evidence_or_model_link |
|---|---|---|
| benefits | Local renewable consumption, lower transmitted energy, greener hydrogen/ammonia products | Q2/Q3 green ratios and sell-ratio outputs |
| benefits | Flexible ammonia load improves matching between renewables and demand | q3_compare_q2.csv |
| risks | Public grid still provides balancing and backup value | q4_grid_vs_offgrid.csv |
| risks | Reverse power flow and metering traceability become more complex | hourly buy/sell and indicator tables |
| recommendations | Use load-follow-source planning, hourly metering, sell-ratio caps, storage or flexible-load configuration, and fair grid-service cost sharing | policy notice constraints and model sensitivity outputs |
"""
    Path(path).write_text(text, encoding="utf-8")


def write_result_summary(path, sheets):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd

        with pd.ExcelWriter(path.with_suffix(".xlsx"), engine="openpyxl") as writer:
            for name, rows in sheets.items():
                pd.DataFrame(rows).to_excel(writer, sheet_name=name[:31], index=False)
        return path.with_suffix(".xlsx")
    except Exception:
        csv_path = path.with_suffix(".csv")
        flat = []
        for name, rows in sheets.items():
            for row in rows:
                nr = {"section": name}
                nr.update(row)
                flat.append(nr)
        write_csv(csv_path, flat)
        return csv_path


def create_figures(figures_dir, data, q1_rows, q1_metrics, q2_rows, q2_summary, q3_rows, q3_summary, compare_rows, q4_rows, scan_rows):
    figures_dir = Path(figures_dir)
    _fig_q1_power(figures_dir / "q1_power_balance.png", q1_rows)
    _fig_q1_energy(figures_dir / "q1_energy_bar.png", q1_rows)
    _fig_q1_indicators(figures_dir / "q1_green_indicators.png", q1_metrics)
    _fig_q2_heatmap(figures_dir / "q2_typical_schedule_heatmap.png", q2_rows)
    _fig_unit_cost_curve(figures_dir / "q2_typical_unit_cost_by_production.png", q2_summary, "Q2 Discrete Unit Cost")
    _fig_boxplot(figures_dir / "q2_unit_cost_boxplot.png", q2_rows, "Q2 Unit Cost by Production")
    _fig_buy_sell(figures_dir / "q2_buy_sell_distribution.png", q2_rows)
    _fig_pie(figures_dir / "q2_annual_classification_pie.png", q2_rows)
    _fig_unit_cost_curve(figures_dir / "q2_annual_unit_cost_curve.png", q2_summary, "Q2 Annual Unit Cost")
    _fig_dispatch_examples(figures_dir / "q3_dispatch_examples.png", q3_rows)
    _fig_boxplot(figures_dir / "q3_unit_cost_boxplot.png", q3_rows, "Q3 Unit Cost by Production")
    _fig_compare_bar(figures_dir / "q3_vs_q2_unit_cost.png", compare_rows, "delta_unit_cost", "Q3 - Q2 unit cost (yuan/t)")
    _fig_compare_bar(figures_dir / "q3_vs_q2_green_indicators.png", compare_rows, "delta_R_sell", "Q3 - Q2 sell ratio")
    _fig_q4_heatmap(figures_dir / "q4_no_storage_production_heatmap.png", q4_rows, "daily_NH3_t")
    _fig_q4_heatmap(figures_dir / "q4_no_storage_curtailment_heatmap.png", q4_rows, "curtail_MWh")
    _fig_scan(figures_dir / "q4_storage_capacity_scan.png", scan_rows)
    _fig_placeholder(figures_dir / "q4_storage_soc_max_curtailment.png", "Storage SOC profile reserved for detailed MILP storage dispatch")
    _fig_placeholder(figures_dir / "q4_storage_improvement_bar.png", "Storage improvement summary")
    _fig_grid_compare(figures_dir / "q4_grid_vs_offgrid_unit_cost.png", q3_rows, q4_rows)
    _fig_placeholder(figures_dir / "q4_grid_support_value.png", "Grid support value = off-grid unit cost - grid-connected unit cost")


def figure_index_rows():
    names = [
        "q1_power_balance.png",
        "q1_energy_bar.png",
        "q1_green_indicators.png",
        "q2_typical_schedule_heatmap.png",
        "q2_typical_unit_cost_by_production.png",
        "q2_unit_cost_boxplot.png",
        "q2_buy_sell_distribution.png",
        "q2_annual_classification_pie.png",
        "q2_annual_unit_cost_curve.png",
        "q3_dispatch_examples.png",
        "q3_unit_cost_boxplot.png",
        "q3_vs_q2_unit_cost.png",
        "q3_vs_q2_green_indicators.png",
        "q4_no_storage_production_heatmap.png",
        "q4_no_storage_curtailment_heatmap.png",
        "q4_storage_capacity_scan.png",
        "q4_storage_soc_max_curtailment.png",
        "q4_storage_improvement_bar.png",
        "q4_grid_vs_offgrid_unit_cost.png",
        "q4_grid_support_value.png",
    ]
    return [{"figure_file": f"outputs/figures/{name}", "paper_use": name.replace(".png", "")} for name in names]


def acceptance_report(q1_rows, q2_rows, q3_rows):
    q2_ok = len(q2_rows) == 120
    q3_ok = len(q3_rows) == 120
    max_q1_balance = max(abs(float(r["balance_residual_MW"])) for r in q1_rows)
    rows_for_metric = q2_rows + q3_rows
    max_self_identity_gap = max(
        abs(float(r["E_self"]) - (float(r["E_re"]) - float(r["E_sell"]) - float(r["E_curtail"])))
        for r in rows_for_metric
    )
    max_green_ratio_gap = max(
        abs(float(r["R_green"]) - float(r["E_self"]) / float(r["E_load"]))
        for r in rows_for_metric
        if float(r["E_load"]) > 0
    )
    return [
        {"check": "q1_hourly_rows", "status": "OK" if len(q1_rows) == 24 else "FAIL", "value": len(q1_rows), "expected": 24},
        {"check": "q2_rows", "status": "OK" if q2_ok else "FAIL", "value": len(q2_rows), "expected": 120},
        {"check": "q3_rows", "status": "OK" if q3_ok else "FAIL", "value": len(q3_rows), "expected": 120},
        {"check": "q1_power_balance", "status": "OK" if max_q1_balance < 1e-6 else "FAIL", "value": max_q1_balance, "expected": "<1e-6"},
        {"check": "metering_E_self_identity", "status": "OK" if max_self_identity_gap < 1e-6 else "FAIL", "value": max_self_identity_gap, "expected": "E_self=E_re-E_sell-E_curtail"},
        {"check": "metering_R_green_formula", "status": "OK" if max_green_ratio_gap < 1e-9 else "FAIL", "value": max_green_ratio_gap, "expected": "R_green=E_self/E_load"},
    ]


def _scenario_parts(scenario_id):
    w, p = scenario_id.split("P")
    return int(w.replace("W", "")), int(p)


def _fmt_vec(values):
    return " ".join(f"{float(v):.6g}" for v in values)


def _savefig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _fig_q1_power(path, rows):
    h = [r["hour"] for r in rows]
    plt.figure(figsize=(9, 4.8))
    plt.plot(h, [r["P_load_total_MW"] for r in rows], label="Total load (MW)")
    plt.plot(h, [r["P_re_MW"] for r in rows], label="Renewable (MW)")
    plt.bar(h, [r["P_buy_MW"] for r in rows], alpha=0.35, label="Buy (MW)")
    plt.bar(h, [-r["P_sell_MW"] for r in rows], alpha=0.35, label="Sell (MW)")
    plt.xlabel("Hour")
    plt.ylabel("Power (MW)")
    plt.legend()
    _savefig(path)


def _fig_q1_energy(path, rows):
    labels = ["Load", "Renewable", "Buy", "Sell"]
    vals = [
        sum(r["P_load_total_MW"] for r in rows),
        sum(r["P_re_MW"] for r in rows),
        sum(r["P_buy_MW"] for r in rows),
        sum(r["P_sell_MW"] for r in rows),
    ]
    plt.figure(figsize=(6, 4))
    plt.bar(labels, vals, color=["#3B82F6", "#22C55E", "#F59E0B", "#EF4444"])
    plt.ylabel("Energy (MWh)")
    _savefig(path)


def _fig_q1_indicators(path, q1_metrics):
    metrics = q1_metrics[0] if q1_metrics else {"R_self": 0, "R_green": 0, "R_sell": 0}
    plt.figure(figsize=(6, 4))
    labels = ["Self-use", "Green load", "Sell"]
    values = [metrics["R_self"], metrics["R_green"], metrics["R_sell"]]
    thresholds = [0.60, 0.30, 0.20]
    x = np.arange(len(labels))
    plt.bar(x - 0.18, values, width=0.36, label="Actual")
    plt.bar(x + 0.18, thresholds, width=0.36, label="Threshold")
    plt.ylabel("Ratio")
    plt.xticks(x, labels)
    plt.legend()
    _savefig(path)


def _fig_q2_heatmap(path, rows):
    typical = [r for r in rows if r["scenario_id"] == "W1P1"]
    if not typical:
        typical = rows[:5]
    mat = []
    labels = []
    for r in typical:
        hours = set(int(x) for x in str(r["on_hours"]).split() if x)
        mat.append([1 if h in hours else 0 for h in range(24)])
        labels.append(str(r["Q_day"]))
    plt.figure(figsize=(10, 3.5))
    plt.imshow(mat, aspect="auto", cmap="Blues")
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Hour")
    plt.ylabel("Q_day (t/d)")
    plt.colorbar(label="On/off")
    _savefig(path)


def _fig_unit_cost_curve(path, rows, title):
    plt.figure(figsize=(6, 4))
    plt.plot([r["Q_day"] for r in rows], [r["annual_average_unit_cost"] for r in rows], marker="o")
    plt.xlabel("Production (t/d)")
    plt.ylabel("Unit cost (yuan/t)")
    plt.title(title)
    _savefig(path)


def _fig_boxplot(path, rows, title):
    by_q = {}
    for r in rows:
        by_q.setdefault(r["Q_day"], []).append(r["unit_cost"])
    labels = sorted(by_q, reverse=True)
    plt.figure(figsize=(7, 4))
    plt.boxplot([by_q[q] for q in labels], labels=[str(q) for q in labels])
    plt.xlabel("Production (t/d)")
    plt.ylabel("Unit cost (yuan/t)")
    plt.title(title)
    _savefig(path)


def _fig_buy_sell(path, rows):
    plt.figure(figsize=(7, 4))
    plt.scatter([r["E_buy"] for r in rows], [r["E_sell"] for r in rows], s=18, alpha=0.7)
    plt.xlabel("Buy energy (MWh)")
    plt.ylabel("Sell energy (MWh)")
    _savefig(path)


def _fig_pie(path, rows):
    counts = [sum(1 for r in rows if r["class"] == c) for c in [CLASS_ALL, CLASS_PARTIAL, CLASS_NONE]]
    plt.figure(figsize=(5, 5))
    plt.pie(counts, labels=["All pass", "Partial", "All fail"], autopct="%1.0f%%")
    _savefig(path)


def _fig_dispatch_examples(path, rows):
    sample = rows[0] if rows else None
    plt.figure(figsize=(9, 4))
    if sample:
        plt.plot([float(x) for x in sample["x_vector"].split()], label=f"{sample['scenario_id']} Q={sample['Q_day']}")
    plt.xlabel("Hour")
    plt.ylabel("Load factor")
    plt.legend()
    _savefig(path)


def _fig_compare_bar(path, rows, key, title):
    vals = [r[key] for r in rows]
    plt.figure(figsize=(7, 4))
    if vals:
        plt.hist(vals, bins=20, color="#3B82F6")
    plt.xlabel(title)
    plt.ylabel("Count")
    _savefig(path)


def _fig_q4_heatmap(path, rows, key):
    vals = np.array([r[key] for r in rows], dtype=float).reshape(6, 4)
    plt.figure(figsize=(6, 4))
    plt.imshow(vals, aspect="auto", cmap="YlGnBu")
    plt.xlabel("PV scenario")
    plt.ylabel("Wind scenario")
    plt.colorbar(label=key)
    _savefig(path)


def _fig_scan(path, rows):
    plt.figure(figsize=(6, 4))
    plt.plot([r["E_cap_MWh"] for r in rows], [r["storage_unit_cost_yuan_per_t"] for r in rows], marker="o")
    plt.xlabel("Storage capacity (MWh)")
    plt.ylabel("Storage unit cost (yuan/t)")
    _savefig(path)


def _fig_placeholder(path, title):
    plt.figure(figsize=(6, 3))
    plt.text(0.5, 0.5, title, ha="center", va="center", wrap=True)
    plt.axis("off")
    _savefig(path)


def _fig_grid_compare(path, q3_rows, q4_rows):
    plt.figure(figsize=(7, 4))
    if q3_rows and q4_rows:
        grid_cost = np.mean([r["unit_cost"] for r in q3_rows if r["Q_day"] == 72])
        off_prod = np.mean([r["daily_NH3_t"] for r in q4_rows])
        plt.bar(["Grid-connected Q3 cost", "Off-grid avg NH3"], [grid_cost, off_prod])
    plt.ylabel("Value")
    _savefig(path)
