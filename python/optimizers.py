from __future__ import annotations
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds, linprog
from scipy.sparse import lil_matrix
from config import CFG, TOU_PRICE
from costs import process_power_for_rate, process_om_cost_for_rate

def solve_discrete_on_grid(base_load_mw, renewable_mw, target_tpd, m_big=200.0):
    n = 24
    rate_full = 3.0
    p_full = process_power_for_rate(rate_full)
    on_hours = int(round(target_tpd / rate_full))
    nvars = 4 * n
    c = np.zeros(nvars)
    c[0:n] = process_om_cost_for_rate(rate_full)
    c[n:2*n] = TOU_PRICE * 1000
    c[2*n:3*n] = -CFG.feedin_yuan_per_kwh * 1000
    lb = np.zeros(nvars)
    ub = np.full(nvars, np.inf)
    ub[0:n] = 1
    ub[3*n:4*n] = 1
    integrality = np.zeros(nvars, dtype=int)
    integrality[0:n] = 1
    integrality[3*n:4*n] = 1

    cons = []
    row = np.zeros(nvars); row[0:n] = 1
    cons.append(LinearConstraint(row, on_hours, on_hours))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, n+t] = 1
        A[t, 2*n+t] = -1
        A[t, t] = -p_full
    cons.append(LinearConstraint(A.tocsr(), base_load_mw - renewable_mw, base_load_mw - renewable_mw))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, n+t] = 1
        A[t, 3*n+t] = -m_big
    cons.append(LinearConstraint(A.tocsr(), -np.inf*np.ones(n), np.zeros(n)))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, 2*n+t] = 1
        A[t, 3*n+t] = m_big
    cons.append(LinearConstraint(A.tocsr(), -np.inf*np.ones(n), m_big*np.ones(n)))

    res = milp(c=c, constraints=cons, bounds=Bounds(lb, ub), integrality=integrality)
    if not res.success:
        raise RuntimeError(res.message)
    x = res.x
    y = np.rint(x[0:n]).astype(int)
    buy = np.maximum(x[n:2*n], 0)
    sell = np.maximum(x[2*n:3*n], 0)
    return {'y': y, 'buy_mw': buy, 'sell_mw': sell, 'load_mw': base_load_mw + p_full * y}

def solve_continuous_on_grid(base_load_mw, renewable_mw, target_tpd, m_big=200.0):
    n = 24
    rate_max, rate_min = 3.0, 0.3
    p_per_rate = process_power_for_rate(1.0)
    om_per_rate = process_om_cost_for_rate(1.0)
    idx_r, idx_b, idx_s, idx_g = 0, n, 2*n, 3*n
    nvars = 4 * n
    c = np.zeros(nvars)
    c[idx_r:idx_b] = om_per_rate
    c[idx_b:idx_s] = TOU_PRICE * 1000
    c[idx_s:idx_g] = -CFG.feedin_yuan_per_kwh * 1000
    lb = np.zeros(nvars)
    ub = np.full(nvars, np.inf)
    lb[idx_r:idx_b] = rate_min
    ub[idx_r:idx_b] = rate_max
    ub[idx_g:idx_g+n] = 1
    integrality = np.zeros(nvars, dtype=int)
    integrality[idx_g:idx_g+n] = 1

    cons = []
    row = np.zeros(nvars); row[idx_r:idx_b] = 1
    cons.append(LinearConstraint(row, target_tpd, target_tpd))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, idx_b+t] = 1
        A[t, idx_s+t] = -1
        A[t, idx_r+t] = -p_per_rate
    cons.append(LinearConstraint(A.tocsr(), base_load_mw - renewable_mw, base_load_mw - renewable_mw))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, idx_b+t] = 1
        A[t, idx_g+t] = -m_big
    cons.append(LinearConstraint(A.tocsr(), -np.inf*np.ones(n), np.zeros(n)))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, idx_s+t] = 1
        A[t, idx_g+t] = m_big
    cons.append(LinearConstraint(A.tocsr(), -np.inf*np.ones(n), m_big*np.ones(n)))

    res = milp(c=c, constraints=cons, bounds=Bounds(lb, ub), integrality=integrality)
    if not res.success:
        raise RuntimeError(res.message)
    x = res.x
    r = x[idx_r:idx_b]
    buy = np.maximum(x[idx_b:idx_s], 0)
    sell = np.maximum(x[idx_s:idx_g], 0)
    return {'rate_tph': r, 'buy_mw': buy, 'sell_mw': sell, 'load_mw': base_load_mw + p_per_rate * r}

def offgrid_no_storage_dispatch(base_load_mw, renewable_mw):
    p_per_rate = process_power_for_rate(1.0)
    residual = renewable_mw - base_load_mw
    rate = np.clip(residual / p_per_rate, 0.3, 3.0)
    proc = p_per_rate * rate
    curtail = np.maximum(renewable_mw - base_load_mw - proc, 0)
    deficit = np.maximum(base_load_mw + proc - renewable_mw, 0)
    return {'rate_tph': rate, 'proc_power_mw': proc, 'curtail_mwh': curtail, 'deficit_mwh': deficit}

def solve_offgrid_storage_dispatch(base_load_mw, renewable_mw, e_cap_mwh, p_cap_mw=None, target_tpd=72.0, min_daily_tpd=0.0):
    n = 24
    e_cap_mwh = float(max(e_cap_mwh, 0.0))
    if p_cap_mw is None:
        p_cap_mw = e_cap_mwh / 4.0 if e_cap_mwh > 0 else 0.0
    p_cap_mw = float(max(p_cap_mw, 0.0))

    rate_max, rate_min = 3.0, 0.3
    p_per_rate = process_power_for_rate(1.0)
    idx_r, idx_ch, idx_dis = 0, n, 2*n
    idx_soc, idx_curt, idx_shed, idx_mode = 3*n, 4*n, 5*n, 6*n
    nvars = 7 * n

    c = np.zeros(nvars)
    c[idx_r:idx_ch] = -10000.0
    c[idx_ch:idx_dis] = 0.01
    c[idx_dis:idx_soc] = 0.01
    c[idx_curt:idx_shed] = 1.0
    c[idx_shed:idx_mode] = 1_000_000.0

    lb = np.zeros(nvars)
    ub = np.full(nvars, np.inf)
    lb[idx_r:idx_ch] = rate_min
    ub[idx_r:idx_ch] = rate_max
    ub[idx_ch:idx_dis] = p_cap_mw
    ub[idx_dis:idx_soc] = p_cap_mw
    ub[idx_soc:idx_curt] = e_cap_mwh
    ub[idx_mode:idx_mode+n] = 1.0

    integrality = np.zeros(nvars, dtype=int)
    integrality[idx_mode:idx_mode+n] = 1

    cons = []
    row = np.zeros(nvars)
    row[idx_r:idx_ch] = 1.0
    cons.append(LinearConstraint(row, float(min_daily_tpd), float(target_tpd)))

    A = lil_matrix((2*n, nvars))
    for t in range(n):
        A[t, idx_ch+t] = 1.0
        A[t, idx_mode+t] = -p_cap_mw
        A[n+t, idx_dis+t] = 1.0
        A[n+t, idx_mode+t] = p_cap_mw
    cons.append(LinearConstraint(A.tocsr(), -np.inf*np.ones(2*n), np.r_[np.zeros(n), np.full(n, p_cap_mw)]))

    A = lil_matrix((n, nvars))
    for t in range(n):
        A[t, idx_r+t] = p_per_rate
        A[t, idx_ch+t] = 1.0
        A[t, idx_curt+t] = 1.0
        A[t, idx_dis+t] = -1.0
        A[t, idx_shed+t] = -1.0
    cons.append(LinearConstraint(A.tocsr(), np.asarray(renewable_mw) - np.asarray(base_load_mw), np.asarray(renewable_mw) - np.asarray(base_load_mw)))

    A = lil_matrix((n, nvars))
    for t in range(n):
        prev = n - 1 if t == 0 else t - 1
        A[t, idx_soc+t] = 1.0
        A[t, idx_soc+prev] = -(1.0 - CFG.storage_self_loss_per_h)
        A[t, idx_ch+t] = -CFG.storage_eta_ch
        A[t, idx_dis+t] = 1.0 / CFG.storage_eta_dis
    cons.append(LinearConstraint(A.tocsr(), np.zeros(n), np.zeros(n)))

    res = milp(c=c, constraints=cons, bounds=Bounds(lb, ub), integrality=integrality)
    if not res.success:
        raise RuntimeError(res.message)

    x = res.x
    rate = np.maximum(x[idx_r:idx_ch], 0)
    charge = np.maximum(x[idx_ch:idx_dis], 0)
    discharge = np.maximum(x[idx_dis:idx_soc], 0)
    soc = np.maximum(x[idx_soc:idx_curt], 0)
    curtail = np.maximum(x[idx_curt:idx_shed], 0)
    shed = np.maximum(x[idx_shed:idx_mode], 0)
    return {
        'rate_tph': rate,
        'proc_power_mw': p_per_rate * rate,
        'charge_mw': charge,
        'discharge_mw': discharge,
        'soc_mwh': soc,
        'curtail_mwh': curtail,
        'deficit_mwh': shed,
        'daily_nh3_t': float(np.sum(rate)),
        'load_mw': np.asarray(base_load_mw) + p_per_rate * rate + charge - discharge,
    }

def estimate_min_capacity_hourly(base_load_mw, wind_pu, pv_pu, keep_ratio=False):
    req = base_load_mw + process_power_for_rate(3.0)
    if keep_ratio:
        scales = []
        worst = None
        for wi in range(6):
            for pi in range(4):
                current = CFG.wind_cap_mw * wind_pu[:, wi] + CFG.pv_cap_mw * pv_pu[:, pi]
                scale = float(np.max(req / current))
                scales.append(scale)
                if worst is None or scale > worst[0]:
                    worst = (scale, wi + 1, pi + 1)
        k = float(np.max(scales))
        return {
            'wind_mw': CFG.wind_cap_mw * k,
            'pv_mw': CFG.pv_cap_mw * k,
            'scale': k,
            'worst_case_scenario_id': f"W{worst[1]}P{worst[2]}" if worst else "",
        }
    A, b = [], []
    for wi in range(6):
        for pi in range(4):
            for t in range(24):
                A.append([-wind_pu[t, wi], -pv_pu[t, pi]])
                b.append(-req[t])
    res = linprog(c=[1, 1], A_ub=np.array(A), b_ub=np.array(b), bounds=[(0, None), (0, None)], method='highs')
    if not res.success:
        raise RuntimeError(res.message)
    return {'wind_mw': float(res.x[0]), 'pv_mw': float(res.x[1]), 'sum_mw': float(res.fun)}

def estimate_min_capacity_daily_energy(base_load_mw, wind_pu, pv_pu, keep_ratio=False):
    req_daily = float(np.sum(base_load_mw) + process_power_for_rate(3.0) * 24.0)
    wind_daily_pu = np.sum(wind_pu, axis=0)
    pv_daily_pu = np.sum(pv_pu, axis=0)
    if keep_ratio:
        scales = []
        worst = None
        for wi in range(6):
            for pi in range(4):
                current = CFG.wind_cap_mw * wind_daily_pu[wi] + CFG.pv_cap_mw * pv_daily_pu[pi]
                scale = float(req_daily / max(current, 1e-9))
                scales.append(scale)
                if worst is None or scale > worst[0]:
                    worst = (scale, wi + 1, pi + 1)
        k = float(np.max(scales))
        return {
            'wind_mw': CFG.wind_cap_mw * k,
            'pv_mw': CFG.pv_cap_mw * k,
            'scale': k,
            'sum_mw': (CFG.wind_cap_mw + CFG.pv_cap_mw) * k,
            'req_daily_mwh': req_daily,
            'worst_case_scenario_id': f"W{worst[1]}P{worst[2]}" if worst else "",
        }

    A, b = [], []
    for wi in range(6):
        for pi in range(4):
            A.append([-wind_daily_pu[wi], -pv_daily_pu[pi]])
            b.append(-req_daily)
    res = linprog(c=[1, 1], A_ub=np.array(A), b_ub=np.array(b), bounds=[(0, None), (0, None)], method='highs')
    if not res.success:
        raise RuntimeError(res.message)
    slacks = []
    for wi in range(6):
        for pi in range(4):
            supply = res.x[0] * wind_daily_pu[wi] + res.x[1] * pv_daily_pu[pi]
            slacks.append((float(supply - req_daily), wi + 1, pi + 1))
    worst = min(slacks, key=lambda x: x[0])
    return {
        'wind_mw': float(res.x[0]),
        'pv_mw': float(res.x[1]),
        'sum_mw': float(res.fun),
        'req_daily_mwh': req_daily,
        'worst_case_scenario_id': f"W{worst[1]}P{worst[2]}",
    }
