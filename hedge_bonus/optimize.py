"""Ottimizzazione vettorizzata (forma chiusa, margine statico) + verifica col modello completo."""
import numpy as np
from model import Acct, Setup, analyse, sigma_hourly_usd

P0, CS = 3620.0, 100.0
LEV_A, LEV_B, SO_A, SO_B = 400, 1000, 0.50, 0.80
mA, mB = CS * P0 / LEV_A, CS * P0 / LEV_B        # margine per lotto
SIG_H = sigma_hourly_usd(0.20, P0)               # $/h, sigma annuo 20% (IPOTESI)
LOT_STEP, LOT_MAX = 0.01, 100.0


def closed_form(DA, DB, LA, LB, bonus=1.0, spread=0.12):
    """Payoff in forma chiusa (margine statico, NBP, credito non prelevabile). Broadcast su array."""
    C = bonus * DB
    LA = np.asarray(LA, float); LB = np.asarray(LB, float)
    dA = (DA - spread * LA * CS - SO_A * LA * mA) / (LA * CS)
    dB = (DB + C - spread * LB * CS - SO_B * LB * mB) / (LB * CS)
    resA = SO_A * LA * mA
    resB = SO_B * LB * mB
    piA = resA + DB - spread * LB * CS + LB * CS * dA - DA - DB
    piB = DA - spread * LA * CS + LA * CS * dB + np.maximum(resB - C, 0) - DA - DB
    return piA, piB, dA, dB


def best_for_alloc(K, xB, tau_max_h=None, objective="pmin", spread=0.12, bonus=1.0, lb_max=None):
    """Per allocazione xB (quota B), cerca (LA, LB) su griglia lot-step.
    objective: 'pmin' (max min profitto, con vincolo E[tau]<=tau_max_h) | 'rate' (pmin/E[tau])."""
    DA, DB = (1 - xB) * K, xB * K
    C = bonus * DB
    lbmax = min(LOT_MAX, (DB + C) / (CS * (SO_B * mB / CS + spread)) * 0.999)
    lamax = min(LOT_MAX, DA / (CS * (SO_A * mA / CS + spread)) * 0.999)
    if lb_max: lbmax = min(lbmax, lb_max)
    LB = np.round(np.arange(LOT_STEP, lbmax, LOT_STEP), 2)
    LA = np.round(np.arange(LOT_STEP, lamax, LOT_STEP), 2)
    if len(LA) == 0 or len(LB) == 0:
        return None
    # Per LB fisso: piB cresce e piA decresce in LA -> max(min) all'incrocio.
    # Bisezione vettorizzata sul continuo, poi verifica floor/ceil al lot step.
    lo = np.full(LB.shape, LOT_STEP); hi = np.full(LB.shape, LA[-1])
    for _ in range(50):
        mid = (lo + hi) / 2
        pa, pb, _, _ = closed_form(DA, DB, mid, LB, bonus, spread)
        up = pb < pa
        lo = np.where(up, mid, lo); hi = np.where(up, hi, mid)
    cands = []
    for LAc in (np.floor(lo / LOT_STEP) * LOT_STEP, np.ceil(lo / LOT_STEP) * LOT_STEP):
        LAc = np.clip(np.round(LAc, 2), LOT_STEP, LA[-1])
        cands.append(LAc)
    best = None
    for LAg in cands:
        LBg = LB
        piA, piB, dA, dB = closed_form(DA, DB, LAg, LBg, bonus, spread)
        pmin = np.minimum(piA, piB)
        tau = dA * dB / SIG_H ** 2
        ok = (dA > 0) & (dB > 0)
        if tau_max_h is not None:
            ok &= tau <= tau_max_h
        score = np.where(ok, pmin if objective == "pmin" else pmin / tau, -np.inf)
        i = int(np.argmax(score))
        if np.isfinite(score[i]) and (best is None or score[i] > best[0]):
            best = (score[i], LAg[i], LBg[i], piA[i], piB[i], dA[i], dB[i], tau[i])
    if best is None:
        return None
    s, la, lb, pa, pb, da, db, tau = best
    return dict(K=K, xB=xB, DA=DA, DB=DB, LA=la, LB=lb, piA=pa, piB=pb, pmin=min(pa, pb),
                dA_pct=da / P0 * 100, dB_pct=db / P0 * 100, tau_h=tau,
                rate_h=min(pa, pb) / tau, roi_min=min(pa, pb) / K * 100)


def optimize(K, tau_max_h=None, objective="pmin", spread=0.12, coarse=0.01, fine=0.001):
    res = [best_for_alloc(K, x, tau_max_h, objective, spread) for x in np.arange(0.10, 0.9001, coarse)]
    res = [r for r in res if r]
    key = (lambda r: r["pmin"]) if objective == "pmin" else (lambda r: r["rate_h"])
    b = max(res, key=key)
    fine_res = [best_for_alloc(K, x, tau_max_h, objective, spread)
                for x in np.arange(b["xB"] - coarse, b["xB"] + coarse + 1e-9, fine)]
    fine_res = [r for r in fine_res if r]
    return max(fine_res + [b], key=key), res


def verify_full(r, spread=0.12):
    """Verifica indipendente col modello completo (margine dinamico)."""
    A = Acct(r["DA"], 0.0, LEV_A, SO_A, r["LA"], +1, spread=spread)
    B = Acct(r["DB"], 1.0, LEV_B, SO_B, r["LB"], -1, spread=spread)
    return analyse(Setup(A, B, P0=P0, dynamic_margin=True))
