from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from config import CFG, TOU_PRICE
from costs import process_power_for_rate, storage_capex_daily
from metrics import CLASS_ALL, CLASS_NONE, CLASS_PARTIAL


FIELD_CN = {
    "item": "检查项",
    "check": "验收项",
    "status": "状态",
    "value": "实际值",
    "expected": "期望值",
    "note": "备注",
    "name": "参数名",
    "source": "数据来源",
    "hour": "时刻",
    "time_label": "时间",
    "mode": "运行模式",
    "method": "方法",
    "scenario": "场景编号",
    "scenario_id": "场景编号",
    "wind_scenario": "风电场景",
    "pv_scenario": "光伏场景",
    "wind_MW": "风电装机(MW)",
    "pv_MW": "光伏装机(MW)",
    "total_MW": "总装机(MW)",
    "scale_vs_current": "相对现有装机倍数",
    "target_tpd": "目标日产氨量(吨)",
    "Q": "日产氨量(吨)",
    "Q_day": "日产氨量(吨)",
    "H_on": "运行小时数",
    "total_cost": "日总成本(元)",
    "total_cost_yuan": "日总成本(元)",
    "incremental_total_cost": "日增量成本(元)",
    "incremental_total_cost_yuan": "日增量成本(元)",
    "unit_cost": "吨氨成本(元/吨)",
    "ton_cost_yuan_per_t": "吨氨成本(元/吨)",
    "incremental_unit_cost": "增量吨氨成本(元/吨)",
    "incremental_ton_cost_yuan_per_t": "增量吨氨成本(元/吨)",
    "baseline_grid_cost": "常规负荷基准电费(元)",
    "nh3_capex_daily": "合成氨装置日折旧(元)",
    "annual_days": "折算年天数",
    "annual_total_NH3": "全年合成氨产量(吨)",
    "annual_NH3_t": "全年合成氨产量(吨)",
    "annual_total_cost": "全年总成本(元)",
    "annual_incremental_total_cost": "全年增量成本(元)",
    "annual_storage_cost": "全年储能成本(元)",
    "annual_average_unit_cost": "全年平均吨氨成本(元/吨)",
    "annual_average_incremental_unit_cost": "全年平均增量吨氨成本(元/吨)",
    "days_all_pass": "全满足天数",
    "days_partial_pass": "部分满足天数",
    "days_all_fail": "全不满足天数",
    "best_or_not": "是否推荐",
    "class": "合格情况",
    "class_metering": "合格情况",
    "qualification_metering": "计量口径合格情况",
    "pass_self": "自发自用率达标",
    "pass_green": "绿电占比达标",
    "pass_green_2030": "2030绿电占比达标",
    "pass_sell": "上网比例达标",
    "P_base_MW": "常规负荷(MW)",
    "P_alk_MW": "碱性电解槽功率(MW)",
    "P_pem_MW": "PEM电解槽功率(MW)",
    "P_nh3_MW": "合成氨功率(MW)",
    "P_eha_MW": "电氢氨负荷(MW)",
    "P_load_total_MW": "总负荷(MW)",
    "P_wind_MW": "风电出力(MW)",
    "P_pv_MW": "光伏出力(MW)",
    "P_re_MW": "新能源出力(MW)",
    "P_buy_MW": "网购功率(MW)",
    "P_sell_MW": "上网功率(MW)",
    "P_charge_MW": "储能充电功率(MW)",
    "P_discharge_MW": "储能放电功率(MW)",
    "P_process_MW": "制氨负荷功率(MW)",
    "P_curtail_MW": "弃电功率(MW)",
    "P_unserved_MW": "未满足功率(MW)",
    "tou_price_yuan_per_kWh": "分时电价(元/kWh)",
    "balance_residual_MW": "功率平衡残差(MW)",
    "buy_sell_product": "购售电互斥检查",
    "E_load": "总用电量(MWh)",
    "E_load_MWh": "总用电量(MWh)",
    "E_re": "新能源发电量(MWh)",
    "E_RE_MWh": "新能源发电量(MWh)",
    "E_buy": "网购电量(MWh)",
    "E_buy_MWh": "网购电量(MWh)",
    "E_sell": "上网电量(MWh)",
    "E_sell_MWh": "上网电量(MWh)",
    "E_curtail": "弃电量(MWh)",
    "E_curtail_MWh": "弃电量(MWh)",
    "E_self": "自用新能源电量(MWh)",
    "E_self_MWh": "自用新能源电量(MWh)",
    "E_self_use_MWh": "自用新能源电量(MWh)",
    "R_self": "自发自用率",
    "self_use_gen_ratio": "自发自用率",
    "R_green": "绿电用电比例",
    "green_load_ratio": "绿电用电比例",
    "R_sell": "上网比例",
    "sell_ratio": "上网比例",
    "statement_R_self": "题面公式自用率",
    "statement_self_use_ratio": "题面公式自用率",
    "M_self": "自发自用率裕度",
    "M_green": "绿电比例裕度",
    "M_green_2030": "2030绿电比例裕度",
    "M_sell": "上网比例裕度",
    "min_policy_margin": "最小政策裕度",
    "violation_score": "违规程度",
    "u_t": "开停机状态",
    "on_hours": "开机时段",
    "x_vector": "负荷率序列",
    "rate_vector": "产氨速率序列(吨/小时)",
    "buy_vector": "网购功率序列(MW)",
    "sell_vector": "上网功率序列(MW)",
    "curtail_vector": "弃电序列(MWh)",
    "unserved_vector": "未满足序列(MWh)",
    "rate_tph": "产氨速率(吨/小时)",
    "daily_NH3_t": "日合成氨产量(吨)",
    "avg_rate_tph": "平均产氨速率(吨/小时)",
    "curtail_MWh": "弃电量(MWh)",
    "unserved_base_MWh": "未满足负荷电量(MWh)",
    "max_curtail_MW": "最大弃电功率(MW)",
    "max_unserved_base_MW": "最大未满足功率(MW)",
    "E_cap_MWh": "储能容量(MWh)",
    "P_cap_MW": "储能功率(MW)",
    "duration_h": "储能时长(小时)",
    "design_scenario_id": "设计场景",
    "capacity_basis_method": "储能配置基准方法",
    "wind_cap_MW": "储能配置风电装机(MW)",
    "pv_cap_MW": "储能配置光伏装机(MW)",
    "delta_NH3_t": "产量提升(吨/日)",
    "mean_daily_NH3_t": "平均日合成氨产量(吨)",
    "mean_delta_NH3_t": "平均产量提升(吨/日)",
    "shortfall_to_72_t": "距离72吨缺口(吨/日)",
    "worst_shortfall_t": "最坏场景产量缺口(吨/日)",
    "worst_daily_NH3_t": "最坏场景日产氨量(吨)",
    "worst_case_scenario_id": "最坏场景编号",
    "curtail_reduction_MWh": "弃电减少量(MWh)",
    "mean_curtail_MWh": "平均弃电量(MWh)",
    "storage_charge_MWh": "储能充电量(MWh)",
    "storage_discharge_MWh": "储能放电量(MWh)",
    "storage_recovered_MWh": "储能回收电量(MWh)",
    "max_SOC_MWh": "最大荷电量(MWh)",
    "SOC_MWh": "荷电量(MWh)",
    "storage_daily_cost": "储能日成本(元)",
    "storage_unit_cost_yuan_per_t": "储能单位成本(元/吨)",
    "incremental_storage_cost_yuan_per_added_t": "新增吨氨储能成本(元/吨)",
    "daily_total_cost": "日总成本(元)",
    "offgrid_unit_cost": "离网吨氨成本(元/吨)",
    "offgrid_daily_NH3_t": "离网日合成氨产量(吨)",
    "grid_connected_unit_cost": "联网吨氨成本(元/吨)",
    "grid_support_value": "电网支撑价值(元/吨)",
    "hard_policy_feasible": "硬约束可行",
    "soft_violation_score": "软约束违规度",
    "unit_cost_reduction": "吨氨成本下降(元/吨)",
    "buy_reduction_MWh": "网购电量减少(MWh)",
    "sell_reduction_MWh": "上网电量减少(MWh)",
    "self_ratio_gain": "自发自用率提升",
    "green_ratio_gain": "绿电比例提升",
    "sell_ratio_reduction": "上网比例下降",
    "cost_mean": "成本均值(元/吨)",
    "cost_max": "成本最大值(元/吨)",
    "cost_p90": "成本90分位(元/吨)",
    "cost_cvar90": "成本CVaR90(元/吨)",
    "violation_mean": "违规度均值",
    "violation_max": "违规度最大值",
    "violation_p90": "违规度90分位",
    "violation_cvar90": "违规度CVaR90",
    "full_pass_count": "全满足场景数",
    "partial_pass_count": "部分满足场景数",
    "all_fail_count": "全不满足场景数",
    "cluster_id": "代表场景编号",
    "probability": "概率",
    "expected_days": "折算天数",
    "wind_mean_pu": "平均风电标幺",
    "pv_mean_pu": "平均光伏标幺",
    "scheme": "方案",
    "full_pass_days": "全满足天数",
    "annual_NH3": "全年合成氨产量(吨)",
    "storage_investment_proxy": "储能投资代理变量",
    "topsis_score": "TOPSIS得分",
    "rank": "排序",
    "recommendation_type": "推荐类型",
    "interpretation": "解释",
    "required_daily_MWh": "日能量需求(MWh)",
    "basis_role": "基准用途",
    "figure_file": "图片文件",
    "paper_use": "论文用途",
}

VALUE_CN = {
    "discrete": "离散开停机",
    "continuous": "连续调节",
    "best_cost": "成本最优",
    "minimax_daily_energy_LP": "日能量Minimax线性规划",
    "minimax_daily_energy_fixed_ratio": "日能量Minimax固定风光比例",
    "minimax_daily_energy_fixed_ratio_storage_loss_margin": "日能量Minimax固定比例含储能损耗裕度",
    "minimax_hourly_LP_no_storage": "逐小时Minimax无储能线性规划",
    "minimax_hourly_fixed_ratio_no_storage": "逐小时Minimax固定比例无储能",
    "mathematical_lower_bound": "数学下界",
    "storage_design_basis": "储能设计基准",
    "strict_no_storage_boundary": "严格无储能边界",
    "ALL_MINIMAX": "全部场景Minimax",
    "max_curtailment_original_capacity": "原始装机最大弃电场景",
    "minimax_robust_dispatch": "Minimax鲁棒调度",
    "minimizes the worst-case daily ammonia shortfall across all 24 wind/PV scenarios": "最小化24个风光场景中的最坏日产氨缺口",
    "recommended_max_curtailment_storage": "最大弃电场景推荐配置",
    "economic_min_incremental_cost": "经济型最低边际成本",
    "max_daily_NH3": "最大日产量",
    "max_curtailment_reduction": "最大弃电削减",
    "smallest_capacity_for_90pct_curtailment_reduction": "90%弃电削减最小容量",
    "lowest marginal storage cost per added ton of ammonia; use as the cost-first design": "新增吨氨储能成本最低，适合作为成本优先方案",
    "highest off-grid ammonia output in the scanned storage range": "扫描范围内离网日产氨量最高",
    "largest renewable curtailment reduction in the scanned storage range": "扫描范围内弃电削减量最大",
    "smallest storage capacity that captures at least 90% of the maximum achievable curtailment reduction": "达到最大可削减弃电量90%所需的最小储能容量",
    "minimum positive storage capacity that improves the maximum-curtailment scenario; use as the main answer": "能改善最大弃电场景的最小正储能容量，作为主答案",
    "lowest marginal storage cost per added ton in the maximum-curtailment scenario; use as the main storage design": "最大弃电场景下新增吨氨储能成本最低，作为主推荐储能方案",
    "highest ammonia output in the maximum-curtailment scenario across the scanned storage range": "最大弃电场景下扫描范围内日产氨量最高",
    "largest curtailment reduction in the maximum-curtailment scenario across the scanned storage range": "最大弃电场景下扫描范围内弃电削减量最大",
    "smallest storage capacity that captures at least 90% of the maximum-curtailment scenario reduction": "达到最大弃电场景可削减弃电量90%所需的最小储能容量",
    "OK": "通过",
    "FAIL": "未通过",
}


def _setup_chinese_font():
    candidates = [
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for font_path in candidates:
        path = Path(font_path)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            font_name = font_manager.FontProperties(fname=str(path)).get_name()
            plt.rcParams["font.sans-serif"] = [font_name, "Microsoft YaHei", "SimHei", "Arial Unicode MS"]
            break
    plt.rcParams["axes.unicode_minus"] = False


_setup_chinese_font()


def ensure_output_dirs(out_dir):
    out = Path(out_dir)
    tables = out / "tables"
    figures = out / "figures"
    tables_cn = out / "tables_cn"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    tables_cn.mkdir(parents=True, exist_ok=True)
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


def write_csv_cn(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    cn_rows = [_row_to_cn(row, fieldnames) for row in rows]
    cn_fields = [_field_to_cn(field) for field in fieldnames]
    write_csv(path, cn_rows, cn_fields)


def _field_to_cn(field):
    return FIELD_CN.get(field, field)


def _value_to_cn(value):
    if isinstance(value, (bool, np.bool_)):
        return "是" if bool(value) else "否"
    if value is None:
        return ""
    return VALUE_CN.get(value, VALUE_CN.get(str(value), value))


def _row_to_cn(row, fieldnames):
    return {_field_to_cn(field): _value_to_cn(row.get(field, "")) for field in fieldnames}


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
        annual_incremental_cost = sum(float(r.get("incremental_total_cost", r["total_cost"])) for r in items) * 15
        out.append({
            "Q_day": q,
            "annual_days": annual_days,
            "annual_total_NH3": annual_nh3,
            "annual_total_cost": annual_cost,
            "annual_incremental_total_cost": annual_incremental_cost,
            "annual_average_unit_cost": annual_cost / annual_nh3 if annual_nh3 else np.nan,
            "annual_average_incremental_unit_cost": annual_incremental_cost / annual_nh3 if annual_nh3 else np.nan,
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


def policy_margin_rows(rows, mode):
    out = []
    for r in rows:
        margin_self = float(r["R_self"]) - 0.60
        margin_green = float(r["R_green"]) - 0.30
        margin_green_2030 = float(r["R_green"]) - 0.35
        margin_sell = 0.20 - float(r["R_sell"])
        violation_score = sum(max(0.0, -v) for v in [margin_self, margin_green, margin_sell])
        out.append({
            "mode": mode,
            "scenario_id": r["scenario_id"],
            "Q_day": r["Q_day"],
            "M_self": margin_self,
            "M_green": margin_green,
            "M_green_2030": margin_green_2030,
            "M_sell": margin_sell,
            "min_policy_margin": min(margin_self, margin_green, margin_sell),
            "violation_score": violation_score,
        })
    return out


def scenario_risk_summary_rows(rows, mode):
    out = []
    by_q = {}
    for r in rows:
        by_q.setdefault(r["Q_day"], []).append(r)
    for q, items in sorted(by_q.items(), reverse=True):
        costs = np.array([float(r["unit_cost"]) for r in items], dtype=float)
        violation = np.array([
            max(0.0, 0.60 - float(r["R_self"]))
            + max(0.0, 0.30 - float(r["R_green"]))
            + max(0.0, float(r["R_sell"]) - 0.20)
            for r in items
        ])
        out.append({
            "mode": mode,
            "Q_day": q,
            "cost_mean": float(np.mean(costs)),
            "cost_max": float(np.max(costs)),
            "cost_p90": float(np.quantile(costs, 0.90)),
            "cost_cvar90": _cvar90(costs),
            "violation_mean": float(np.mean(violation)),
            "violation_max": float(np.max(violation)),
            "violation_p90": float(np.quantile(violation, 0.90)),
            "violation_cvar90": _cvar90(violation),
            "full_pass_count": sum(1 for r in items if r["class"] == CLASS_ALL),
            "partial_pass_count": sum(1 for r in items if r["class"] == CLASS_PARTIAL),
            "all_fail_count": sum(1 for r in items if r["class"] == CLASS_NONE),
        })
    return out


def flexible_load_value_rows(compare_rows):
    out = []
    for r in compare_rows:
        out.append({
            "scenario_id": r["scenario_id"],
            "Q_day": r["Q_day"],
            "unit_cost_reduction": -float(r["delta_unit_cost"]),
            "buy_reduction_MWh": -float(r["delta_buy"]),
            "sell_reduction_MWh": -float(r["delta_sell"]),
            "self_ratio_gain": float(r["delta_R_self"]),
            "green_ratio_gain": float(r["delta_R_green"]),
            "sell_ratio_reduction": -float(r["delta_R_sell"]),
        })
    return out


def storage_2d_scan_rows(base_scan_rows):
    rows = []
    p_caps = [0.125, 0.25, 0.5]
    for r in base_scan_rows:
        e_cap = float(r["E_cap_MWh"])
        for ratio in p_caps:
            p_cap = e_cap * ratio
            base_p_cap = float(r.get("P_cap_MW", 0.0))
            utilization_factor = min(1.0, p_cap / base_p_cap) if base_p_cap > 0 else 1.0
            storage_daily_cost = float(r["storage_daily_cost"]) * (1.0 + 0.03 * max(ratio - 1.0, 0.0))
            daily_nh3 = float(r["daily_NH3_t"]) * utilization_factor if e_cap > 0 else float(r["daily_NH3_t"])
            rows.append({
                "E_cap_MWh": e_cap,
                "P_cap_MW": p_cap,
                "duration_h": e_cap / p_cap if p_cap > 0 else np.nan,
                "daily_NH3_t": daily_nh3,
                "storage_daily_cost": storage_daily_cost,
                "storage_unit_cost_yuan_per_t": storage_daily_cost / daily_nh3 if daily_nh3 > 0 else np.nan,
            })
    return rows


def storage_marginal_value_rows(scan_rows):
    out = []
    ordered = sorted(scan_rows, key=lambda r: float(r["E_cap_MWh"]))
    for prev, cur in zip(ordered, ordered[1:]):
        d_e = float(cur["E_cap_MWh"]) - float(prev["E_cap_MWh"])
        prev_cost = float(prev["storage_unit_cost_yuan_per_t"])
        cur_cost = float(cur["storage_unit_cost_yuan_per_t"])
        out.append({
            "E_cap_from_MWh": float(prev["E_cap_MWh"]),
            "E_cap_to_MWh": float(cur["E_cap_MWh"]),
            "marginal_unit_cost_reduction_yuan_per_t_per_MWh": (prev_cost - cur_cost) / d_e if d_e else np.nan,
        })
    return out


def topsis_candidates_rows(q2_annual, q3_annual, q4_storage_annual, q4_grid_vs):
    rows = []
    for source, items in [("discrete", q2_annual), ("continuous", q3_annual)]:
        for r in items:
            rows.append({
                "scheme": f"{source}_Q{r['Q_day']}",
                "unit_cost": r["annual_average_unit_cost"],
                "full_pass_days": r["days_all_pass"],
                "annual_NH3": r["annual_total_NH3"],
                "storage_investment_proxy": 0.0,
                "grid_support_value": 0.0,
            })
    if q4_storage_annual:
        s = q4_storage_annual[0]
        rows.append({
            "scheme": "offgrid_storage",
            "unit_cost": s.get("annual_average_unit_cost", s["annual_storage_cost"] / max(s["annual_NH3_t"], 1e-9)),
            "full_pass_days": 0,
            "annual_NH3": s["annual_NH3_t"],
            "storage_investment_proxy": s["E_cap_MWh"],
            "grid_support_value": float(np.nanmean([r["grid_support_value"] for r in q4_grid_vs])),
        })
    return _topsis_rank(rows)


def storage_trace_report_rows(q4_with_storage):
    out = []
    for r in q4_with_storage:
        recovered = float(r["storage_recovered_MWh"])
        out.append({
            "scenario_id": r["scenario_id"],
            "SOC_green_in_MWh": recovered,
            "SOC_grid_in_MWh": 0.0,
            "green_discharge_MWh": recovered,
            "grid_discharge_MWh": 0.0,
            "trace_rule": "offgrid_storage_charged_by_project_renewables",
            "counted_as_project_green_energy_MWh": recovered,
        })
    return out


def hard_soft_compare_rows(rows):
    out = []
    for r in rows:
        margins = [float(r["self_use_gen_ratio"]) - 0.60, float(r["green_load_ratio"]) - 0.30, 0.20 - float(r["sell_ratio"])]
        out.append({
            "mode": r["mode"],
            "scenario_id": r["scenario"],
            "Q_day": r["target_tpd"],
            "hard_policy_feasible": all(m >= -1e-9 for m in margins),
            "soft_violation_score": sum(max(0.0, -m) for m in margins),
            "unit_cost": r["ton_cost_yuan_per_t"],
        })
    return out


def q4_no_storage_rows(data, scenarios):
    rows = []
    p_per_rate = process_power_for_rate(1.0)
    for sc in scenarios:
        residual = sc["renew_mw"] - data.base_load_mw
        rate = np.clip(residual / p_per_rate, 0.3, 3.0)
        proc = p_per_rate * rate
        curtail = np.maximum(sc["renew_mw"] - data.base_load_mw - proc, 0)
        unserved = np.maximum(data.base_load_mw + proc - sc["renew_mw"], 0)
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


def create_figures(
    figures_dir,
    data,
    q1_rows,
    q1_metrics,
    q2_rows,
    q2_summary,
    q3_rows,
    q3_summary,
    compare_rows,
    q4_rows,
    scan_rows,
    q4_storage_rows,
    q4_storage_hourly,
    q4_grid_vs,
    q4_min_capacity,
    stochastic_rows,
    policy_margin,
    storage_2d,
    topsis_candidates,
):
    figures_dir = Path(figures_dir)
    _fig_q1_power(figures_dir / "q1_power_balance.png", q1_rows)
    _fig_q1_power(figures_dir / "fig_01_typical_power_balance.png", q1_rows)
    _fig_q1_energy(figures_dir / "q1_energy_bar.png", q1_rows)
    _fig_q1_indicators(figures_dir / "q1_green_indicators.png", q1_metrics)
    _fig_q2_heatmap(figures_dir / "q2_typical_schedule_heatmap.png", q2_rows)
    _fig_q2_heatmap(figures_dir / "fig_02_discrete_schedule_heatmap.png", q2_rows)
    _fig_continuous_heatmap(figures_dir / "fig_03_continuous_schedule_heatmap.png", q3_rows)
    _fig_6x4_cost(figures_dir / "fig_04_6x4_cost_heatmap.png", q3_rows)
    _fig_policy_margin(figures_dir / "fig_05_6x4_policy_margin_heatmap.png", policy_margin)
    _fig_flexible_value(figures_dir / "fig_06_flexible_load_value.png", compare_rows)
    _fig_storage_2d(figures_dir / "fig_07_storage_E_P_contour.png", storage_2d)
    _fig_storage_marginal(figures_dir / "fig_08_storage_marginal_value.png", scan_rows)
    _fig_grid_compare(figures_dir / "fig_09_grid_vs_offgrid_cost.png", q4_grid_vs)
    _fig_pareto(figures_dir / "fig_10_pareto_cost_compliance.png", q3_rows)
    _fig_topsis(figures_dir / "fig_11_topsis_radar.png", topsis_candidates)
    _fig_unit_cost_curve(figures_dir / "q2_typical_unit_cost_by_production.png", q2_summary, "问题二离散开停机吨氨成本")
    _fig_boxplot(figures_dir / "q2_unit_cost_boxplot.png", q2_rows, "问题二不同日产量成本分布")
    _fig_buy_sell(figures_dir / "q2_buy_sell_distribution.png", q2_rows)
    _fig_pie(figures_dir / "q2_annual_classification_pie.png", q2_rows)
    _fig_unit_cost_curve(figures_dir / "q2_annual_unit_cost_curve.png", q2_summary, "问题二全年平均吨氨成本")
    _fig_dispatch_examples(figures_dir / "q3_dispatch_examples.png", q3_rows)
    _fig_boxplot(figures_dir / "q3_unit_cost_boxplot.png", q3_rows, "问题三连续调节成本分布")
    _fig_compare_bar(figures_dir / "q3_vs_q2_unit_cost.png", compare_rows, "delta_unit_cost", "问题三相对问题二吨氨成本变化(元/吨)")
    _fig_compare_bar(figures_dir / "q3_vs_q2_green_indicators.png", compare_rows, "delta_R_sell", "问题三相对问题二上网比例变化")
    _fig_q4_heatmap(figures_dir / "q4_no_storage_production_heatmap.png", q4_rows, "daily_NH3_t")
    _fig_q4_heatmap(figures_dir / "q4_no_storage_curtailment_heatmap.png", q4_rows, "curtail_MWh")
    _fig_scan(figures_dir / "q4_storage_capacity_scan.png", scan_rows)
    _fig_minimax_scan(figures_dir / "q4_minimax_storage_scan.png", scan_rows)
    _fig_storage_soc(figures_dir / "q4_storage_soc_max_curtailment.png", q4_storage_hourly)
    _fig_storage_improvement(figures_dir / "q4_storage_improvement_bar.png", q4_rows, q4_storage_rows)
    _fig_grid_cost_scatter(figures_dir / "q4_grid_vs_offgrid_unit_cost.png", q4_grid_vs)
    _fig_grid_support_value(figures_dir / "q4_grid_support_value.png", q4_grid_vs)
    _fig_min_capacity(figures_dir / "q4_minimum_capacity.png", q4_min_capacity)
    _fig_stochastic(figures_dir / "stochastic_representative_scenarios.png", stochastic_rows)


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
        "q4_minimax_storage_scan.png",
        "q4_storage_soc_max_curtailment.png",
        "q4_storage_improvement_bar.png",
        "q4_grid_vs_offgrid_unit_cost.png",
        "q4_grid_support_value.png",
        "q4_minimum_capacity.png",
        "stochastic_representative_scenarios.png",
        "fig_01_typical_power_balance.png",
        "fig_02_discrete_schedule_heatmap.png",
        "fig_03_continuous_schedule_heatmap.png",
        "fig_04_6x4_cost_heatmap.png",
        "fig_05_6x4_policy_margin_heatmap.png",
        "fig_06_flexible_load_value.png",
        "fig_07_storage_E_P_contour.png",
        "fig_08_storage_marginal_value.png",
        "fig_09_grid_vs_offgrid_cost.png",
        "fig_10_pareto_cost_compliance.png",
        "fig_11_topsis_radar.png",
    ]
    return [{"figure_file": f"outputs/figures/{name}", "paper_use": name.replace(".png", "")} for name in names]


def acceptance_report(q1_rows, q2_rows, q3_rows, q4_storage_rows=None, q4_storage_hourly=None, stochastic_rows=None):
    q4_storage_rows = q4_storage_rows or []
    q4_storage_hourly = q4_storage_hourly or []
    stochastic_rows = stochastic_rows or []
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
    max_q4_balance = max((abs(float(r["balance_residual_MW"])) for r in q4_storage_hourly), default=0.0)
    min_q3_load_factor = min((
        min(float(x) for x in str(r["x_vector"]).split())
        for r in q3_rows
    ), default=np.nan)
    min_q4_storage_rate = min((float(r["rate_tph"]) for r in q4_storage_hourly), default=np.nan)
    storage_has_capacity = any(float(r.get("E_cap_MWh", 0.0)) > 0 for r in q4_storage_rows)
    storage_improves = any(float(r.get("delta_NH3_t", 0.0)) > 1e-6 for r in q4_storage_rows)
    stochastic_prob_sum = sum(float(r.get("probability", 0.0)) for r in stochastic_rows)
    return [
        {"check": "q1_hourly_rows", "status": "OK" if len(q1_rows) == 24 else "FAIL", "value": len(q1_rows), "expected": 24},
        {"check": "q2_rows", "status": "OK" if q2_ok else "FAIL", "value": len(q2_rows), "expected": 120},
        {"check": "q3_rows", "status": "OK" if q3_ok else "FAIL", "value": len(q3_rows), "expected": 120},
        {"check": "q1_power_balance", "status": "OK" if max_q1_balance < 1e-6 else "FAIL", "value": max_q1_balance, "expected": "<1e-6"},
        {"check": "metering_E_self_identity", "status": "OK" if max_self_identity_gap < 1e-6 else "FAIL", "value": max_self_identity_gap, "expected": "E_self=E_re-E_sell-E_curtail"},
        {"check": "metering_R_green_formula", "status": "OK" if max_green_ratio_gap < 1e-9 else "FAIL", "value": max_green_ratio_gap, "expected": "R_green=E_self/E_load"},
        {"check": "q3_continuous_no_shutdown", "status": "OK" if min_q3_load_factor >= 0.1 - 1e-6 else "FAIL", "value": min_q3_load_factor, "expected": "load factor >= 0.1"},
        {"check": "q4_storage_rows", "status": "OK" if len(q4_storage_rows) == 24 else "FAIL", "value": len(q4_storage_rows), "expected": 24},
        {"check": "q4_storage_hourly_rows", "status": "OK" if len(q4_storage_hourly) == 576 else "FAIL", "value": len(q4_storage_hourly), "expected": 576},
        {"check": "q4_storage_power_balance", "status": "OK" if max_q4_balance < 1e-6 else "FAIL", "value": max_q4_balance, "expected": "<1e-6"},
        {"check": "q4_storage_no_shutdown", "status": "OK" if min_q4_storage_rate >= 0.3 - 1e-6 else "FAIL", "value": min_q4_storage_rate, "expected": "rate_tph >= 0.3"},
        {"check": "q4_storage_nonzero_capacity", "status": "OK" if storage_has_capacity else "FAIL", "value": storage_has_capacity, "expected": True},
        {"check": "q4_storage_improves_NH3", "status": "OK" if storage_improves else "FAIL", "value": storage_improves, "expected": True},
        {"check": "stochastic_representative_rows", "status": "OK" if len(stochastic_rows) == 8 else "FAIL", "value": len(stochastic_rows), "expected": 8},
        {"check": "stochastic_probability_sum", "status": "OK" if abs(stochastic_prob_sum - 1.0) < 1e-9 else "FAIL", "value": stochastic_prob_sum, "expected": 1.0},
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
    plt.plot(h, [r["P_load_total_MW"] for r in rows], label="总负荷(MW)")
    plt.plot(h, [r["P_re_MW"] for r in rows], label="新能源出力(MW)")
    plt.bar(h, [r["P_buy_MW"] for r in rows], alpha=0.35, label="网购功率(MW)")
    plt.bar(h, [-r["P_sell_MW"] for r in rows], alpha=0.35, label="上网功率(MW)")
    plt.xlabel("时刻")
    plt.ylabel("功率(MW)")
    plt.legend()
    _savefig(path)


def _fig_q1_energy(path, rows):
    labels = ["总用电量", "新能源发电量", "网购电量", "上网电量"]
    vals = [
        sum(r["P_load_total_MW"] for r in rows),
        sum(r["P_re_MW"] for r in rows),
        sum(r["P_buy_MW"] for r in rows),
        sum(r["P_sell_MW"] for r in rows),
    ]
    plt.figure(figsize=(6, 4))
    plt.bar(labels, vals, color=["#3B82F6", "#22C55E", "#F59E0B", "#EF4444"])
    plt.ylabel("电量(MWh)")
    _savefig(path)


def _fig_q1_indicators(path, q1_metrics):
    metrics = q1_metrics[0] if q1_metrics else {"R_self": 0, "R_green": 0, "R_sell": 0}
    plt.figure(figsize=(6, 4))
    labels = ["自发自用率", "绿电用电比例", "上网比例"]
    values = [metrics["R_self"], metrics["R_green"], metrics["R_sell"]]
    thresholds = [0.60, 0.30, 0.20]
    x = np.arange(len(labels))
    plt.bar(x - 0.18, values, width=0.36, label="实际值")
    plt.bar(x + 0.18, thresholds, width=0.36, label="政策阈值")
    plt.ylabel("比例")
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
    plt.xlabel("时刻")
    plt.ylabel("日产氨量(吨/日)")
    plt.colorbar(label="开机状态")
    _savefig(path)


def _fig_unit_cost_curve(path, rows, title):
    plt.figure(figsize=(6, 4))
    plt.plot([r["Q_day"] for r in rows], [r["annual_average_unit_cost"] for r in rows], marker="o")
    plt.xlabel("日产氨量(吨/日)")
    plt.ylabel("吨氨成本(元/吨)")
    plt.title(title)
    _savefig(path)


def _fig_boxplot(path, rows, title):
    by_q = {}
    for r in rows:
        by_q.setdefault(r["Q_day"], []).append(r["unit_cost"])
    labels = sorted(by_q, reverse=True)
    plt.figure(figsize=(7, 4))
    plt.boxplot([by_q[q] for q in labels], labels=[str(q) for q in labels])
    plt.xlabel("日产氨量(吨/日)")
    plt.ylabel("吨氨成本(元/吨)")
    plt.title(title)
    _savefig(path)


def _fig_buy_sell(path, rows):
    plt.figure(figsize=(7, 4))
    plt.scatter([r["E_buy"] for r in rows], [r["E_sell"] for r in rows], s=18, alpha=0.7)
    plt.xlabel("网购电量(MWh)")
    plt.ylabel("上网电量(MWh)")
    _savefig(path)


def _fig_pie(path, rows):
    counts = [sum(1 for r in rows if r["class"] == c) for c in [CLASS_ALL, CLASS_PARTIAL, CLASS_NONE]]
    plt.figure(figsize=(5, 5))
    plt.pie(counts, labels=["全满足", "部分满足", "全不满足"], autopct="%1.0f%%")
    _savefig(path)


def _fig_dispatch_examples(path, rows):
    sample = rows[0] if rows else None
    plt.figure(figsize=(9, 4))
    if sample:
        plt.plot([float(x) for x in sample["x_vector"].split()], label=f"{sample['scenario_id']} 日产量={sample['Q_day']}吨")
    plt.xlabel("时刻")
    plt.ylabel("负荷率")
    plt.legend()
    _savefig(path)


def _fig_continuous_heatmap(path, rows):
    typical = [r for r in rows if r["scenario_id"] == "W1P1"]
    if not typical:
        typical = rows[:5]
    mat = []
    labels = []
    for r in typical:
        mat.append([float(x) for x in str(r["x_vector"]).split()])
        labels.append(str(r["Q_day"]))
    plt.figure(figsize=(10, 3.5))
    plt.imshow(mat, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("时刻")
    plt.ylabel("日产氨量(吨/日)")
    plt.colorbar(label="负荷率")
    _savefig(path)


def _fig_6x4_cost(path, rows):
    subset = [r for r in rows if r["Q_day"] == 72]
    mat = np.full((6, 4), np.nan)
    for r in subset:
        wi, pi = _scenario_parts(r["scenario_id"])
        mat[wi - 1, pi - 1] = r["unit_cost"]
    plt.figure(figsize=(6, 4))
    plt.imshow(mat, aspect="auto", cmap="viridis")
    plt.xlabel("光伏场景")
    plt.ylabel("风电场景")
    plt.colorbar(label="吨氨成本(元/吨)")
    _savefig(path)


def _fig_policy_margin(path, rows):
    subset = [r for r in rows if r["mode"] == "continuous" and r["Q_day"] == 72]
    mat = np.full((6, 4), np.nan)
    for r in subset:
        wi, pi = _scenario_parts(r["scenario_id"])
        mat[wi - 1, pi - 1] = r["min_policy_margin"]
    plt.figure(figsize=(6, 4))
    plt.imshow(mat, aspect="auto", cmap="RdYlGn")
    plt.xlabel("光伏场景")
    plt.ylabel("风电场景")
    plt.colorbar(label="最小政策裕度")
    _savefig(path)


def _fig_flexible_value(path, rows):
    vals = [-float(r["delta_unit_cost"]) for r in rows]
    plt.figure(figsize=(7, 4))
    if vals:
        plt.hist(vals, bins=20, color="#22C55E")
    plt.xlabel("连续调节带来的吨氨成本下降(元/吨)")
    plt.ylabel("场景数")
    _savefig(path)


def _fig_storage_2d(path, rows):
    if not rows:
        _fig_placeholder(path, "No storage scan rows")
        return
    e_vals = sorted(set(float(r["E_cap_MWh"]) for r in rows))
    p_vals = sorted(set(float(r["P_cap_MW"]) for r in rows))
    mat = np.full((len(p_vals), len(e_vals)), np.nan)
    for r in rows:
        i = p_vals.index(float(r["P_cap_MW"]))
        j = e_vals.index(float(r["E_cap_MWh"]))
        mat[i, j] = float(r["storage_unit_cost_yuan_per_t"])
    plt.figure(figsize=(7, 4))
    plt.imshow(mat, aspect="auto", origin="lower", cmap="magma")
    plt.xticks(range(len(e_vals)), [f"{v:.0f}" for v in e_vals], rotation=45)
    plt.yticks(range(len(p_vals)), [f"{v:.0f}" for v in p_vals])
    plt.xlabel("储能容量(MWh)")
    plt.ylabel("储能功率(MW)")
    plt.colorbar(label="储能单位成本(元/吨)")
    _savefig(path)


def _fig_storage_marginal(path, rows):
    ordered = sorted(rows, key=lambda r: float(r["E_cap_MWh"]))
    plt.figure(figsize=(7, 4))
    if len(ordered) > 1:
        e = [float(r["E_cap_MWh"]) for r in ordered]
        c = [float(r["storage_unit_cost_yuan_per_t"]) for r in ordered]
        marginal = [(c[i - 1] - c[i]) / (e[i] - e[i - 1]) for i in range(1, len(e)) if e[i] != e[i - 1]]
        plt.plot(e[1:1 + len(marginal)], marginal, marker="o")
    plt.xlabel("储能容量(MWh)")
    plt.ylabel("边际单位成本变化")
    _savefig(path)


def _fig_pareto(path, rows):
    plt.figure(figsize=(7, 4))
    if rows:
        cost = [r["unit_cost"] for r in rows]
        margin = [min(r["R_self"] - 0.60, r["R_green"] - 0.30, 0.20 - r["R_sell"]) for r in rows]
        plt.scatter(cost, margin, s=18, alpha=0.7)
    plt.xlabel("吨氨成本(元/吨)")
    plt.ylabel("最小政策裕度")
    _savefig(path)


def _fig_topsis(path, rows):
    labels = ["成本", "达标", "产量", "少储能", "电网价值"]
    best = rows[0] if rows else None
    values = [0.0] * len(labels)
    if best and rows:
        costs = np.array([float(r["unit_cost"]) for r in rows], dtype=float)
        pass_days = np.array([float(r["full_pass_days"]) for r in rows], dtype=float)
        nh3 = np.array([float(r["annual_NH3"]) for r in rows], dtype=float)
        storage = np.array([float(r["storage_investment_proxy"]) for r in rows], dtype=float)
        grid = np.array([max(float(r["grid_support_value"]), 0.0) for r in rows], dtype=float)

        def benefit(value, values_arr):
            lo, hi = float(np.min(values_arr)), float(np.max(values_arr))
            return 1.0 if hi - lo < 1e-12 else (float(value) - lo) / (hi - lo)

        def cost_benefit(value, values_arr):
            lo, hi = float(np.min(values_arr)), float(np.max(values_arr))
            return 1.0 if hi - lo < 1e-12 else (hi - float(value)) / (hi - lo)

        values = [
            cost_benefit(best["unit_cost"], costs),
            benefit(best["full_pass_days"], pass_days),
            benefit(best["annual_NH3"], nh3),
            cost_benefit(best["storage_investment_proxy"], storage),
            benefit(max(float(best["grid_support_value"]), 0.0), grid),
        ]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    plt.figure(figsize=(5, 5))
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("综合推荐方案归一化指标")
    _savefig(path)


def _fig_compare_bar(path, rows, key, title):
    vals = [r[key] for r in rows]
    plt.figure(figsize=(7, 4))
    if vals:
        plt.hist(vals, bins=20, color="#3B82F6")
    plt.xlabel(title)
    plt.ylabel("场景数")
    _savefig(path)


def _fig_q4_heatmap(path, rows, key):
    vals = np.array([r[key] for r in rows], dtype=float).reshape(6, 4)
    plt.figure(figsize=(6, 4))
    plt.imshow(vals, aspect="auto", cmap="YlGnBu")
    plt.xlabel("光伏场景")
    plt.ylabel("风电场景")
    plt.colorbar(label=_field_to_cn(key))
    _savefig(path)


def _fig_scan(path, rows):
    plt.figure(figsize=(6, 4))
    y_key = "storage_unit_cost_yuan_per_t"
    plt.plot([r["E_cap_MWh"] for r in rows], [r[y_key] for r in rows], marker="o")
    plt.xlabel("储能容量(MWh)")
    plt.ylabel("储能单位成本(元/吨)")
    _savefig(path)


def _fig_minimax_scan(path, rows):
    if not rows:
        _fig_placeholder(path, "无Minimax储能扫描数据")
        return
    e_caps = [float(r["E_cap_MWh"]) for r in rows]
    shortfall = [float(r.get("worst_shortfall_t", 0.0)) for r in rows]
    worst_nh3 = [float(r["daily_NH3_t"]) for r in rows]
    fig, ax1 = plt.subplots(figsize=(7.5, 4.6))
    ax1.plot(e_caps, shortfall, marker="o", color="#DC2626", label="最坏缺口")
    ax1.set_xlabel("储能容量(MWh)")
    ax1.set_ylabel("最坏场景缺口(吨/日)")
    ax2 = ax1.twinx()
    ax2.plot(e_caps, worst_nh3, marker="s", color="#2563EB", label="最坏日产氨量")
    ax2.axhline(72.0, color="#111827", linestyle="--", linewidth=0.9, label="72吨/日目标")
    ax2.set_ylabel("最坏场景日产氨量(吨)")
    lines = ax1.get_lines() + ax2.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="best")
    fig.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _fig_storage_soc(path, rows):
    if not rows:
        _fig_placeholder(path, "No storage dispatch rows")
        return
    scenario_ids = sorted(set(r["scenario_id"] for r in rows))
    scenario = max(
        scenario_ids,
        key=lambda sid: max(float(r["SOC_MWh"]) for r in rows if r["scenario_id"] == sid),
    )
    subset = sorted([r for r in rows if r["scenario_id"] == scenario], key=lambda r: int(r["hour"]))
    h = [int(r["hour"]) for r in subset]
    plt.figure(figsize=(9, 4.8))
    plt.plot(h, [float(r["SOC_MWh"]) for r in subset], marker="o", label="荷电量(MWh)")
    plt.bar(h, [float(r["P_charge_MW"]) for r in subset], alpha=0.35, label="充电功率(MW)")
    plt.bar(h, [-float(r["P_discharge_MW"]) for r in subset], alpha=0.35, label="放电功率(MW)")
    plt.plot(h, [float(r["P_curtail_MW"]) for r in subset], linestyle="--", label="弃电功率(MW)")
    plt.xlabel("时刻")
    plt.ylabel("功率/电量")
    plt.title(f"{scenario}场景储能调度")
    plt.legend()
    _savefig(path)


def _fig_storage_improvement(path, base_rows, storage_rows):
    base_by_id = {r["scenario_id"]: r for r in base_rows}
    rows = sorted(storage_rows, key=lambda r: float(r.get("delta_NH3_t", 0.0)), reverse=True)[:8]
    if not rows:
        _fig_placeholder(path, "No storage improvement rows")
        return
    labels = [r["scenario_id"] for r in rows]
    delta_nh3 = [float(r["daily_NH3_t"]) - float(base_by_id[r["scenario_id"]]["daily_NH3_t"]) for r in rows]
    curtail_drop = [float(base_by_id[r["scenario_id"]]["curtail_MWh"]) - float(r["curtail_MWh"]) for r in rows]
    x = np.arange(len(labels))
    plt.figure(figsize=(9, 4.8))
    plt.bar(x - 0.18, delta_nh3, width=0.36, label="产氨提升(吨/日)")
    plt.bar(x + 0.18, curtail_drop, width=0.36, label="弃电减少(MWh)")
    plt.xticks(x, labels)
    plt.ylabel("改善量")
    plt.legend()
    _savefig(path)


def _fig_grid_cost_scatter(path, rows):
    if not rows:
        _fig_placeholder(path, "No grid comparison rows")
        return
    plt.figure(figsize=(6.5, 5))
    x = [float(r["grid_connected_unit_cost"]) for r in rows]
    y = [float(r["offgrid_unit_cost"]) for r in rows]
    plt.scatter(x, y, s=35, alpha=0.8)
    lo = min(x + y)
    hi = max(x + y)
    plt.plot([lo, hi], [lo, hi], color="#64748B", linestyle="--", label="成本相等线")
    plt.xlabel("联网吨氨成本(元/吨)")
    plt.ylabel("离网吨氨成本(元/吨)")
    plt.legend()
    _savefig(path)


def _fig_grid_support_value(path, rows):
    if not rows:
        _fig_placeholder(path, "No grid support value rows")
        return
    ordered = sorted(rows, key=lambda r: float(r["grid_support_value"]), reverse=True)
    labels = [r["scenario_id"] for r in ordered]
    vals = [float(r["grid_support_value"]) for r in ordered]
    plt.figure(figsize=(9, 4.8))
    colors = ["#EF4444" if v > 0 else "#22C55E" for v in vals]
    plt.bar(labels, vals, color=colors)
    plt.axhline(0, color="#111827", linewidth=0.8)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("离网成本-联网成本(元/吨)")
    _savefig(path)


def _fig_min_capacity(path, rows):
    if not rows:
        _fig_placeholder(path, "No capacity rows")
        return
    labels = [_method_label_cn(r["method"]) for r in rows]
    wind = [float(r["wind_MW"]) for r in rows]
    pv = [float(r["pv_MW"]) for r in rows]
    x = np.arange(len(rows))
    plt.figure(figsize=(7, 4.8))
    plt.bar(x, wind, label="风电容量(MW)")
    plt.bar(x, pv, bottom=wind, label="光伏容量(MW)")
    plt.xticks(x, labels)
    plt.ylabel("所需装机容量(MW)")
    plt.legend()
    _savefig(path)


def _fig_stochastic(path, rows):
    if not rows:
        _fig_placeholder(path, "No stochastic scenario rows")
        return
    ordered = sorted(rows, key=lambda r: int(r["cluster_id"]))
    labels = [f"C{r['cluster_id']}" for r in ordered]
    probs = [float(r["probability"]) for r in ordered]
    costs = [float(r["unit_cost"]) for r in ordered]
    fig, ax1 = plt.subplots(figsize=(8, 4.8))
    ax1.bar(labels, probs, color="#3B82F6", alpha=0.65, label="概率")
    ax1.set_ylabel("概率")
    ax2 = ax1.twinx()
    ax2.plot(labels, costs, color="#EF4444", marker="o", label="吨氨成本")
    ax2.set_ylabel("吨氨成本(元/吨)")
    fig.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _fig_placeholder(path, title):
    plt.figure(figsize=(6, 3))
    plt.text(0.5, 0.5, title, ha="center", va="center", wrap=True)
    plt.axis("off")
    _savefig(path)


def _fig_grid_compare(path, rows):
    if not rows:
        _fig_placeholder(path, "无联网/离网对比数据")
        return
    grid_cost = float(np.nanmean([float(r["grid_connected_unit_cost"]) for r in rows]))
    offgrid_cost = float(np.nanmean([float(r["offgrid_unit_cost"]) for r in rows]))
    labels = ["联网方案", "离网+储能方案"]
    values = [grid_cost, offgrid_cost]
    plt.figure(figsize=(7, 4.6))
    bars = plt.bar(labels, values, color=["#2563EB", "#F97316"])
    plt.ylabel("平均吨氨成本(元/吨)")
    plt.title("联网与离网储能方案成本对比")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.0f}", ha="center", va="bottom")
    _savefig(path)


def _method_label_cn(method):
    labels = {
        "LP_min_total_wind_pv_capacity": "最小总装机\n线性规划",
        "fixed_wind_pv_ratio_scale": "固定风光比例\n等比例放大",
        "minimax_daily_energy_LP": "日能量Minimax\n线性规划",
        "minimax_daily_energy_fixed_ratio": "日能量Minimax\n固定比例",
        "minimax_daily_energy_fixed_ratio_storage_loss_margin": "日能量Minimax\n含损耗裕度",
        "minimax_hourly_LP_no_storage": "逐小时Minimax\n无储能",
        "minimax_hourly_fixed_ratio_no_storage": "逐小时Minimax\n固定比例",
    }
    return labels.get(method, str(method).replace("_", "\n"))


def _cvar90(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return np.nan
    threshold = np.quantile(values, 0.90)
    tail = values[values >= threshold]
    return float(np.mean(tail)) if tail.size else float(threshold)


def _topsis_rank(rows):
    if not rows:
        return []
    cols = ["unit_cost", "full_pass_days", "annual_NH3", "storage_investment_proxy", "grid_support_value"]
    X = np.array([[float(r[c]) for c in cols] for r in rows], dtype=float)
    denom = np.sqrt((X ** 2).sum(axis=0))
    denom[denom == 0] = 1.0
    V = X / denom
    weights = np.array([0.30, 0.25, 0.15, 0.15, 0.15])
    V = V * weights
    benefit = np.array([False, True, True, False, True])
    ideal_pos = np.where(benefit, V.max(axis=0), V.min(axis=0))
    ideal_neg = np.where(benefit, V.min(axis=0), V.max(axis=0))
    d_pos = np.sqrt(((V - ideal_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((V - ideal_neg) ** 2).sum(axis=1))
    scores = d_neg / (d_pos + d_neg + 1e-12)
    out = []
    for row, score in zip(rows, scores):
        nr = dict(row)
        nr["topsis_score"] = float(score)
        out.append(nr)
    out.sort(key=lambda r: r["topsis_score"], reverse=True)
    for i, row in enumerate(out, 1):
        row["rank"] = i
    return out
