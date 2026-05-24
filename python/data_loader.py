from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd

from config import CFG, TOU_PRICE, update_config, update_tou_price


@dataclass
class ParkData:
    times: list[str]
    load_pu: np.ndarray
    base_load_mw: np.ndarray
    typical_wind_pu: np.ndarray
    typical_pv_pu: np.ndarray
    wind_scen_pu: np.ndarray
    pv_scen_pu: np.ndarray
    price: np.ndarray
    parameter_sources: dict[str, str] | None = None


def _read(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, engine="openpyxl")


def _find_attachment(data_dir: Path, attachment_no: int, keywords=(), required=True) -> Path | None:
    candidates = [
        path
        for path in sorted(data_dir.glob("*.xlsx")) + sorted(data_dir.glob("*.xls"))
        if not path.name.startswith("~$")
    ]
    by_no = [
        path for path in candidates
        if f"附件{attachment_no}" in path.name
        or f"attachment{attachment_no}" in path.name.lower()
        or f"a{attachment_no}" in path.stem.lower()
    ]
    if keywords:
        matched = [path for path in by_no if any(keyword in path.name for keyword in keywords)]
        if matched:
            return matched[0]
    if by_no:
        return by_no[0]

    if len(candidates) == 4 and 1 <= attachment_no <= 4:
        return candidates[attachment_no - 1]
    if not required:
        return None
    names = ", ".join(path.name for path in candidates) or "none"
    raise FileNotFoundError(f"Cannot find attachment {attachment_no} in {data_dir}. Found: {names}")


def load_parameter_attachments(data_dir: str | Path) -> dict[str, str]:
    p = Path(data_dir)
    sources: dict[str, str] = {}

    tech_path = _find_attachment(p, 5, ("参数", "技术", "tech"), required=False)
    if tech_path:
        _apply_tech_parameters(tech_path)
        sources["attachment5"] = str(tech_path)

    storage_path = _find_attachment(p, 6, ("储能", "合成氨", "storage", "nh3"), required=False)
    if storage_path:
        _apply_storage_nh3_parameters(storage_path)
        sources["attachment6"] = str(storage_path)

    tou_path = _find_attachment(p, 7, ("分时", "电价", "tou"), required=False)
    if tou_path:
        update_tou_price(_parse_tou_price(tou_path))
        sources["attachment7"] = str(tou_path)

    feedin_path = _find_attachment(p, 8, ("上网", "电价", "feedin"), required=False)
    if feedin_path:
        _apply_feed_in_price(feedin_path)
        sources["attachment8"] = str(feedin_path)

    return sources


def load_all_attachments(data_dir: str | Path) -> ParkData:
    p = Path(data_dir)
    parameter_sources = load_parameter_attachments(p)
    load_df = _read(_find_attachment(p, 1, ("负荷", "load")))
    typical_df = _read(_find_attachment(p, 2, ("风电", "光伏", "wind", "pv")))
    wind_df = _read(_find_attachment(p, 3, ("风电", "wind")))
    pv_df = _read(_find_attachment(p, 4, ("光伏", "pv")))

    times = load_df.iloc[:, 0].astype(str).tolist()
    load_pu = load_df.iloc[:, 1].astype(float).to_numpy()
    return ParkData(
        times=times,
        load_pu=load_pu,
        base_load_mw=CFG.conv_peak_mw * load_pu,
        typical_wind_pu=typical_df.iloc[:, 1].astype(float).to_numpy(),
        typical_pv_pu=typical_df.iloc[:, 2].astype(float).to_numpy(),
        wind_scen_pu=wind_df.iloc[:, 1:7].astype(float).to_numpy(),
        pv_scen_pu=pv_df.iloc[:, 1:5].astype(float).to_numpy(),
        price=TOU_PRICE.copy(),
        parameter_sources=parameter_sources,
    )


def _apply_tech_parameters(path: Path) -> None:
    df = _parameter_table(path)
    update_config(
        wind_lcoe_yuan_per_kwh=_numeric_at(df, "度电成本", "风机"),
        pv_lcoe_yuan_per_kwh=_numeric_at(df, "度电成本", "光伏"),
        alk_om_yuan_per_kwh=_numeric_at(df, "运维", "碱性"),
        pem_om_yuan_per_kwh=_numeric_at(df, "运维", "质子"),
    )


def _apply_storage_nh3_parameters(path: Path) -> None:
    df = _parameter_table(path)
    eta_ch, eta_dis = _parse_storage_efficiency(_text_at(df, "效率", "电储能"))
    update_config(
        storage_capex_yuan_per_kwh=_numeric_at(df, "投资成本", "电储能"),
        nh3_capex_yuan_per_kgH2_per_h=_numeric_at(df, "投资成本", "合成氨"),
        storage_om_yuan_per_kwh=_numeric_at(df, "运维", "电储能"),
        nh3_om_yuan_per_kwh=_numeric_at(df, "运维", "合成氨"),
        storage_life_year=_numeric_at(df, "使用寿命", "电储能"),
        nh3_life_year=_numeric_at(df, "使用寿命", "合成氨"),
        storage_eta_ch=eta_ch,
        storage_eta_dis=eta_dis,
        storage_self_loss_per_h=_percent_row_value(_numeric_at(df, "自损耗", "电储能")),
    )


def _parse_tou_price(path: Path) -> np.ndarray:
    df = pd.read_excel(path, engine="openpyxl")
    prices = {row.iloc[0]: float(row.iloc[1]) for _, row in df.iterrows()}
    peak = _find_price(prices, "高峰")
    flat = _find_price(prices, "平")
    valley = _find_price(prices, "低谷")
    out = np.empty(24, dtype=float)
    for hour in range(24):
        if 10 <= hour < 15 or 18 <= hour < 21:
            out[hour] = peak
        elif 7 <= hour < 10 or 15 <= hour < 18 or 21 <= hour < 23:
            out[hour] = flat
        else:
            out[hour] = valley
    return out


def _apply_feed_in_price(path: Path) -> None:
    df = pd.read_excel(path, engine="openpyxl")
    price_col = df.columns[1]
    price = pd.to_numeric(df[price_col], errors="coerce").dropna().mean()
    update_config(feedin_yuan_per_kwh=float(price))


def _parameter_table(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, header=0, engine="openpyxl")
    return df.set_index(df.columns[0])


def _numeric_at(df: pd.DataFrame, row_keyword: str, col_keyword: str) -> float | None:
    row = _match_label(df.index, row_keyword)
    col = _match_label(df.columns, col_keyword)
    if row is None or col is None:
        return None
    return _extract_number(df.loc[row, col])


def _text_at(df: pd.DataFrame, row_keyword: str, col_keyword: str) -> str | None:
    row = _match_label(df.index, row_keyword)
    col = _match_label(df.columns, col_keyword)
    if row is None or col is None:
        return None
    value = df.loc[row, col]
    return None if pd.isna(value) else str(value)


def _match_label(labels, keyword: str):
    for label in labels:
        if keyword in str(label):
            return label
    return None


def _extract_number(value) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _rate_from_percent_like(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 100.0 if value > 1 else value


def _percent_row_value(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 100.0 if value > 0.05 else value


def _parse_storage_efficiency(text: str | None) -> tuple[float | None, float | None]:
    if not text:
        return None, None
    values = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if len(values) >= 2:
        return _rate_from_percent_like(values[0]), _rate_from_percent_like(values[1])
    if len(values) == 1:
        eta = _rate_from_percent_like(values[0])
        return eta, eta
    return None, None


def _find_price(prices: dict, keyword: str) -> float:
    for label, value in prices.items():
        if keyword in str(label):
            return value
    raise ValueError(f"Cannot find TOU price row containing {keyword!r}")


def typical_scenario(data: ParkData):
    wind = CFG.wind_cap_mw * data.typical_wind_pu
    pv = CFG.pv_cap_mw * data.typical_pv_pu
    return {"id": "typical", "wind_mw": wind, "pv_mw": pv, "renew_mw": wind + pv}


def build_scenarios(data: ParkData):
    out = []
    for wi in range(6):
        for pi in range(4):
            wind = CFG.wind_cap_mw * data.wind_scen_pu[:, wi]
            pv = CFG.pv_cap_mw * data.pv_scen_pu[:, pi]
            out.append({
                "id": f"W{wi + 1}P{pi + 1}",
                "wind_id": wi + 1,
                "pv_id": pi + 1,
                "wind_mw": wind,
                "pv_mw": pv,
                "renew_mw": wind + pv,
            })
    return out
