from __future__ import annotations
import numpy as np
from config import CFG

def process_power_for_rate(rate_tph: float) -> float:
    return (CFG.alk_mw_36 + CFG.pem_mw_36 + CFG.nh3_mw_36) / CFG.nh3_rate_tph_36 * rate_tph

def process_om_cost_for_rate(rate_tph: float) -> float:
    factor = rate_tph / CFG.nh3_rate_tph_36
    return (
        CFG.alk_mw_36 * factor * 1000 * CFG.alk_om_yuan_per_kwh
        + CFG.pem_mw_36 * factor * 1000 * CFG.pem_om_yuan_per_kwh
        + CFG.nh3_mw_36 * factor * 1000 * CFG.nh3_om_yuan_per_kwh
    )

def annualized_nh3_capex_daily(capacity_tpd: float) -> float:
    kgH2_per_h = 0.2 * capacity_tpd * 1000 / 24
    capex = CFG.nh3_capex_yuan_per_kgH2_per_h * kgH2_per_h
    return capex / (CFG.nh3_life_year * 365)

def renewable_generation_cost(wind_mw: np.ndarray, pv_mw: np.ndarray) -> float:
    return float((wind_mw.sum() * CFG.wind_lcoe_yuan_per_kwh + pv_mw.sum() * CFG.pv_lcoe_yuan_per_kwh) * 1000)

def storage_capex_daily(e_cap_mwh: float) -> float:
    return e_cap_mwh * 1000 * CFG.storage_capex_yuan_per_kwh / (CFG.storage_life_year * 365)
