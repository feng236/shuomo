from __future__ import annotations
import numpy as np

def metering_energy(total_load_mw, renewable_mw, buy_mw, sell_mw, curtail_mw=None):
    """
    表计口径：对应老师提示图中的表1/表2。
    总用电量 = 下网电量 + 自备电量
    总发电量 = 自用电量 + 上网电量 + 弃电量（并网无弃电时为0）
    """
    e_load = float(np.sum(total_load_mw))
    e_re = float(np.sum(renewable_mw))
    e_buy = float(np.sum(buy_mw))
    e_sell = float(np.sum(sell_mw))
    e_curtail = 0.0 if curtail_mw is None else float(np.sum(curtail_mw))
    e_self_supply = e_load - e_buy
    e_self_use = e_re - e_sell - e_curtail
    return {
        "E_load_MWh": e_load,
        "E_RE_MWh": e_re,
        "E_buy_MWh": e_buy,
        "E_sell_MWh": e_sell,
        "E_curtail_MWh": e_curtail,
        "E_self_supply_MWh": e_self_supply,
        "E_self_use_MWh": e_self_use,
        "balance_gap_MWh": e_self_supply - e_self_use,
    }

def green_direct_metrics_metering(total_load_mw, renewable_mw, buy_mw, sell_mw, curtail_mw=None):
    """
    主口径：表计口径/政策口径。
    1) 新能源自发自用比例 = 自用电量 / 总可用发电量 >= 60%
    2) 总用电量绿电比例 = 自备电量 / 总用电量 >= 30%
    3) 上网电量比例 = 上网电量 / 总可用发电量 <= 20%
    """
    e = metering_energy(total_load_mw, renewable_mw, buy_mw, sell_mw, curtail_mw)
    e_load, e_re = e["E_load_MWh"], e["E_RE_MWh"]
    out = dict(e)
    out["self_use_gen_ratio"] = e["E_self_use_MWh"] / e_re if e_re > 0 else float("nan")
    out["green_load_ratio"] = e["E_self_supply_MWh"] / e_load if e_load > 0 else float("nan")
    out["sell_ratio"] = e["E_sell_MWh"] / e_re if e_re > 0 else float("nan")
    out["is_all_qualified"] = (
        out["self_use_gen_ratio"] >= 0.60
        and out["green_load_ratio"] >= 0.30
        and out["sell_ratio"] <= 0.20
    )
    return out

def green_direct_metrics_statement(total_load_mw, renewable_mw, buy_mw, sell_mw):
    """
    题面公式复核口径：保留用于对照题面原公式。
    注意：它和表计口径在“同一日既购电又上网”时可能给出不同的自发自用比例。
    """
    e_load = float(np.sum(total_load_mw))
    e_re = float(np.sum(renewable_mw))
    e_buy = float(np.sum(buy_mw))
    e_sell = float(np.sum(sell_mw))
    return {
        "E_load_MWh": e_load,
        "E_RE_MWh": e_re,
        "E_buy_MWh": e_buy,
        "E_sell_MWh": e_sell,
        "statement_self_use_ratio": (e_load - e_sell - e_buy) / e_re if e_re > 0 else float("nan"),
        "statement_green_load_ratio": (e_re - e_sell) / e_load if e_load > 0 else float("nan"),
        "statement_sell_ratio": e_sell / e_re if e_re > 0 else float("nan"),
    }

def classify_metering(metrics: dict) -> str:
    flags = [
        metrics["self_use_gen_ratio"] >= 0.60,
        metrics["green_load_ratio"] >= 0.30,
        metrics["sell_ratio"] <= 0.20,
    ]
    if all(flags):
        return "全满足"
    if not any(flags):
        return "全不满足"
    return "部分满足"
