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
    idx_r, idx_y, idx_b, idx_s, idx_g = 0, n, 2*n, 3*n, 4*n
    nvars = 5 * n
    c = np.zeros(nvars)
    c[idx_r:idx_y] = om_per_rate
    c[idx_b:idx_s] = TOU_PRICE * 1000
    c[idx_s:idx_g] = -CFG.feedin_yuan_per_kwh * 1000
    lb = np.zeros(nvars)
    ub = np.full(nvars, np.inf)
    ub[idx_r:idx_y] = rate_max
    ub[idx_y:idx_b] = 1
    ub[idx_g:idx_g+n] = 1
    integrality = np.zeros(nvars, dtype=int)
    integrality[idx_y:idx_b] = 1
    integrality[idx_g:idx_g+n] = 1

    cons = []
    row = np.zeros(nvars); row[idx_r:idx_y] = 1
    cons.append(LinearConstraint(row, target_tpd, target_tpd))

    A = lil_matrix((2*n, nvars))
    for t in range(n):
        A[t, idx_r+t] = 1; A[t, idx_y+t] = -rate_max
        A[n+t, idx_r+t] = -1; A[n+t, idx_y+t] = rate_min
    cons.append(LinearConstraint(A.tocsr(), -np.inf*np.ones(2*n), np.zeros(2*n)))

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
    r = x[idx_r:idx_y]
    buy = np.maximum(x[idx_b:idx_s], 0)
    sell = np.maximum(x[idx_s:idx_g], 0)
    return {'rate_tph': r, 'buy_mw': buy, 'sell_mw': sell, 'load_mw': base_load_mw + p_per_rate * r}

def offgrid_no_storage_dispatch(base_load_mw, renewable_mw):
    p_per_rate = process_power_for_rate(1.0)
    p_full = process_power_for_rate(3.0)
    p_min = process_power_for_rate(0.3)
    residual = renewable_mw - base_load_mw
    rate = np.zeros(24)
    proc = np.zeros(24)
    for t in range(24):
        if residual[t] >= p_min:
            proc[t] = min(p_full, residual[t])
            rate[t] = proc[t] / p_per_rate
    curtail = np.maximum(renewable_mw - base_load_mw - proc, 0)
    deficit = np.maximum(base_load_mw - renewable_mw, 0)
    return {'rate_tph': rate, 'proc_power_mw': proc, 'curtail_mwh': curtail, 'deficit_mwh': deficit}

def estimate_min_capacity_hourly(base_load_mw, wind_pu, pv_pu, keep_ratio=False):
    req = base_load_mw + process_power_for_rate(3.0)
    if keep_ratio:
        scales = []
        for wi in range(6):
            for pi in range(4):
                current = CFG.wind_cap_mw * wind_pu[:, wi] + CFG.pv_cap_mw * pv_pu[:, pi]
                scales.append(np.max(req / current))
        k = float(np.max(scales))
        return {'wind_mw': CFG.wind_cap_mw * k, 'pv_mw': CFG.pv_cap_mw * k, 'scale': k}
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
