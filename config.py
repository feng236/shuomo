from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ParkConfig:
    dt_h: float = 1.0
    conv_peak_mw: float = 6.0
    wind_cap_mw: float = 40.0
    pv_cap_mw: float = 64.0
    alk_mw_36: float = 10.0
    pem_mw_36: float = 10.0
    nh3_mw_36: float = 0.75
    nh3_rate_tph_36: float = 1.5
    wind_lcoe_yuan_per_kwh: float = 0.15
    pv_lcoe_yuan_per_kwh: float = 0.12
    alk_om_yuan_per_kwh: float = 0.10
    pem_om_yuan_per_kwh: float = 0.15
    nh3_om_yuan_per_kwh: float = 0.002
    feedin_yuan_per_kwh: float = 0.3779
    nh3_capex_yuan_per_kgH2_per_h: float = 60000.0
    nh3_life_year: float = 30.0
    storage_capex_yuan_per_kwh: float = 1000.0
    storage_om_yuan_per_kwh: float = 0.01
    storage_life_year: float = 15.0
    storage_eta_ch: float = 0.90
    storage_eta_dis: float = 0.90
    storage_self_loss_per_h: float = 0.002


CFG = ParkConfig()


def tou_price(hour: int) -> float:
    if 10 <= hour < 15 or 18 <= hour < 21:
        return 0.8024
    if 7 <= hour < 10 or 15 <= hour < 18 or 21 <= hour < 23:
        return 0.6074
    return 0.3424


TOU_PRICE = np.array([tou_price(h) for h in range(24)], dtype=float)


def update_config(**kwargs) -> ParkConfig:
    updates = {k: v for k, v in kwargs.items() if v is not None}
    for key, value in updates.items():
        setattr(CFG, key, value)
    return CFG


def update_tou_price(price_by_hour) -> np.ndarray:
    arr = np.asarray(price_by_hour, dtype=float)
    if arr.shape != (24,):
        raise ValueError("TOU price must contain 24 hourly values")
    TOU_PRICE[:] = arr
    return TOU_PRICE
