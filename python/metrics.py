from __future__ import annotations

import numpy as np


CLASS_ALL = "\u5168\u6ee1\u8db3"
CLASS_PARTIAL = "\u90e8\u5206\u6ee1\u8db3"
CLASS_NONE = "\u5168\u4e0d\u6ee1\u8db3"


def metering_energy(total_load_mw, renewable_mw, buy_mw, sell_mw, curtail_mw=None):
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
    e = metering_energy(total_load_mw, renewable_mw, buy_mw, sell_mw, curtail_mw)
    e_load, e_re = e["E_load_MWh"], e["E_RE_MWh"]
    out = dict(e)
    out["self_use_gen_ratio"] = e["E_self_use_MWh"] / e_re if e_re > 0 else float("nan")
    out["green_load_ratio"] = e["E_self_use_MWh"] / e_load if e_load > 0 else float("nan")
    out["sell_ratio"] = e["E_sell_MWh"] / e_re if e_re > 0 else float("nan")
    out["pass_self"] = out["self_use_gen_ratio"] >= 0.60
    out["pass_green"] = out["green_load_ratio"] >= 0.30
    out["pass_green_2030"] = out["green_load_ratio"] >= 0.35
    out["pass_sell"] = out["sell_ratio"] <= 0.20
    out["is_all_qualified"] = out["pass_self"] and out["pass_green"] and out["pass_sell"]
    return out


def green_direct_metrics_statement(total_load_mw, renewable_mw, buy_mw, sell_mw):
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
        return CLASS_ALL
    if not any(flags):
        return CLASS_NONE
    return CLASS_PARTIAL
