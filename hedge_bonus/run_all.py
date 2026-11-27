"""Esegue REPLICA, CAPITAL, OPTIMIZE, STRATEGY, MONTECARLO, STRESS e salva risultati in results/."""
import json, math, os
from dataclasses import replace
import numpy as np
from model import Acct, Setup, analyse, scenario, acct_table, benchmark, sigma_hourly_usd
from optimize import optimize, verify_full, closed_form, best_for_alloc, P0, CS, SIG_H

OUT = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT, exist_ok=True)
R = {}

def mk(DA, DB, LA, LB, spread=0.12, regime="absorb", levA=400, levB=1000, bonus=1.0, **kw):
    A = Acct(DA, 0.0, levA, 0.50, LA, +1, spread=spread)
    B = Acct(DB, bonus, levB, 0.80, LB, -1, spread=spread, bonus_regime=regime)
    s = Setup(A, B, P0=P0, dynamic_margin=True)
    for k, v in kw.items():
        setattr(s, k, v)
    return s

def summ(s):
    r = analyse(s)
    tau = r["dAdB"] / SIG_H ** 2
    return dict(piA=r["A"]["profit"], piB=r["B"]["profit"], pmin=r["pmin"], ev=r["ev"], pA=r["pA"],
                dA=r["A"]["dist_pct"], dB=r["B"]["dist_pct"], tau=tau,
                PA=r["A"]["P_stop"], PB=r["B"]["P_stop"], recA_A=r["A"]["recA"], recB_A=r["A"]["recB"],
                recA_B=r["B"]["recA"], recB_B=r["B"]["recB"], resA=r["A"]["residual_equity"],
                resB=r["B"]["residual_equity"])

# ---------------- REPLICA ----------------
rep = {}
for dyn in (False, True):
    for sp in (0.0, 0.12):
        s = mk(2000, 2000, 0.38, 0.53, spread=sp, dynamic_margin=dyn)
        rep[f"dyn={dyn},spread={sp}"] = summ(s)
R["replica"] = rep
R["acct_table"] = acct_table(mk(2000, 2000, 0.38, 0.53))
# margin level 980%: ricerca di combinazioni coerenti
ml = {}
ml["A_lots_for_980"] = 2000 / (9.8 * CS * P0 / 400)
ml["B_lots_for_980"] = 4000 / (9.8 * CS * P0 / 1000)
ml["aggregate_ML"] = 6000 / (0.38 * CS * P0 / 400 + 0.53 * CS * P0 / 1000) * 100
ml["B_ML_if_lev400"] = 4000 / (0.53 * CS * P0 / 400) * 100
R["ml980"] = ml

# Upper bound teorico (lotti -> 0, no costi): r* e profitto
def sup_profit(xB, K=4000):
    DA, DB = (1 - xB) * K, xB * K
    # piB = 2 r DB - DB ; piA = DA (1/r - 1) -> uguaglia
    a, b, c = 2 * DB, DA - DB, -DA     # 2DB r^2 + (DA-DB) r - DA = 0  (moltiplicando per r)
    r = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
    return r, 2 * r * DB - DB
xs = np.arange(0.10, 0.9001, 0.001)
sp = [sup_profit(x) for x in xs]
i = int(np.argmax([p for _, p in sp]))
R["sup"] = dict(x50=sup_profit(0.5), xbest=float(xs[i]), r=sp[i][0], p=sp[i][1])

# ---------------- FRONTIERA (K=4000) ----------------
caps = [1, 2, 4, 8, 12, 24, 38.5, 48, 96, 240]
front = []
for cap in caps:
    b, _ = optimize(4000, tau_max_h=cap)
    v = verify_full(b)
    b.update(full_piA=v["A"]["profit"], full_piB=v["B"]["profit"])
    front.append(b)
R["frontier"] = front

# ---------------- CAPITAL grid ----------------
caps_K = [500, 1000, 2000, 4000, 5000, 10000, 15000, 20000, 30000, 50000, 100000]
cap_rows = []
for K in caps_K:
    # vincolo di durata pari al benchmark (stesse distanze %, E[tau] ~ 38.5h a sigma 20%)
    b, allx = optimize(K, tau_max_h=38.5)
    v = verify_full(b)
    # benchmark scalato: 50/50, lotti proporzionali arrotondati
    sc = K / 4000
    LA0, LB0 = max(0.01, round(0.38 * sc, 2)), max(0.01, round(0.53 * sc, 2))
    s0 = summ(mk(K / 2, K / 2, LA0, LB0))
    cap_rows.append(dict(K=K, xB=b["xB"], DA=b["DA"], DB=b["DB"], LA=b["LA"], LB=b["LB"],
                         dA=b["dA_pct"], dB=b["dB_pct"], piA=v["A"]["profit"], piB=v["B"]["profit"],
                         pmin=min(v["A"]["profit"], v["B"]["profit"]), tau=b["tau_h"],
                         mlA=b["DA"] / (b["LA"] * CS * P0 / 400) * 100,
                         mlB=2 * b["DB"] / (b["LB"] * CS * P0 / 1000) * 100,
                         bench_LA=LA0, bench_LB=LB0, bench_pmin=s0["pmin"], bench_dA=s0["dA"], bench_dB=s0["dB"]))
R["capital"] = cap_rows

# heatmap allocazione x rapporto (K=4000, LB fisso 0.53)
hm = []
for xB in np.arange(0.30, 0.701, 0.02):
    row = []
    for LA in np.arange(0.20, 0.601, 0.02):
        a, b_, dA, dB = closed_form((1 - xB) * 4000, xB * 4000, LA, 0.53)
        row.append(float(min(a, b_)))
    hm.append(row)
R["heatmap"] = dict(xB=list(np.round(np.arange(0.30, 0.701, 0.02), 2)),
                    LA=list(np.round(np.arange(0.20, 0.601, 0.02), 2)), z=hm)

# ---------------- STRATEGIE (K=4000) ----------------
S = {}
S["S01"] = dict(mk=(2000, 2000, 0.38, 0.53))
# S02: size fisse, allocazione ottimizzata
best = None
for x in np.arange(0.10, 0.9001, 0.001):
    a, b_, dA, dB = closed_form((1 - x) * 4000, x * 4000, 0.38, 0.53)
    if dA > 0 and dB > 0 and (best is None or min(a, b_) > best[0]):
        best = (min(a, b_), x)
S["S02"] = dict(mk=((1 - best[1]) * 4000, best[1] * 4000, 0.38, 0.53))
# S03: 50/50, size ottimizzate a parità di durata attesa
r3 = best_for_alloc(4000, 0.5, tau_max_h=38.5)
S["S03"] = dict(mk=(2000, 2000, r3["LA"], r3["LB"]))
r4, _ = optimize(4000, tau_max_h=38.5)
S["S04"] = dict(mk=(r4["DA"], r4["DB"], r4["LA"], r4["LB"]))
# S05: stop equidistanti (|dA-dB| minimo), max pmin a parità di prodotto dA*dB
best5 = None
for x in np.arange(0.30, 0.7001, 0.005):
    for LA in np.arange(0.20, 0.80, 0.01):
        for LB in np.arange(0.20, 0.80, 0.01):
            a, b_, dA, dB = closed_form((1 - x) * 4000, x * 4000, LA, LB)
            if dA <= 0 or dB <= 0 or abs(dA - dB) / P0 > 0.0005: continue
            if dA * dB / SIG_H ** 2 > 38.5: continue
            if best5 is None or min(a, b_) > best5[0]:
                best5 = (min(a, b_), x, round(LA, 2), round(LB, 2))
S["S05"] = dict(mk=((1 - best5[1]) * 4000, best5[1] * 4000, best5[2], best5[3]))
strat_rows = {}
for k, v in S.items():
    DA, DB, LA, LB = v["mk"]
    strat_rows[k] = dict(DA=DA, DB=DB, LA=LA, LB=LB, **summ(mk(DA, DB, LA, LB)))
# S09: inversione direzioni (A short / B long) - payoff simmetrico, differenza = swap
def swap_cost(LA, LB, nights, inv=False, sl=-30, ss=+20):
    # swap dichiarati (unità ipotizzate USD/lotto/notte), stessi valori su entrambi i broker (IPOTESI)
    if not inv:
        return nights * (LA * sl + LB * ss)
    return nights * (LA * ss + LB * sl)
strat_rows["S09_swap_per_night"] = dict(base=swap_cost(0.38, 0.53, 1), inverted=swap_cost(0.38, 0.53, 1, True))
R["strategies"] = strat_rows

# ---------------- MONTE CARLO ----------------
rng = np.random.default_rng(20261127)

def mc(LA, LB, DA, DB, sig_ann=0.20, nu=4, n=20000, horizon_h=72, dt_min=1, vol_unc=0.35,
       early_target=None, drift_ann=0.0):
    """Percorsi di prezzo a 1 minuto: innovazioni Student-t(nu), vol per-path lognormale (incertezza
    di regime). Restituisce tempi di uscita e payoff. Margine statico (forma chiusa)."""
    a, b_, dA, dB = closed_form(DA, DB, LA, LB)
    piA, piB = float(a), float(b_)
    steps = int(horizon_h * 60 / dt_min)
    sig_path = sig_ann * np.exp(vol_unc * rng.standard_normal(n) - 0.5 * vol_unc ** 2)
    sd_step = sig_path * P0 / math.sqrt(252 * 23 * 60 / dt_min)
    scale = math.sqrt((nu - 2) / nu)
    mu_step = drift_ann * P0 / (252 * 23 * 60 / dt_min)
    x = np.zeros(n); alive = np.ones(n, bool); t_exit = np.full(n, np.inf); who = np.zeros(n, int)
    down = dA if early_target is None else min(dA, early_target / ((LB - LA) * CS))
    mdd = np.zeros(n)
    for k in range(steps):
        inc = rng.standard_t(nu, n) * scale * sd_step + mu_step
        x = np.where(alive, x + inc, x)
        hitA = alive & (x <= -down); hitB = alive & (x >= dB)
        t_exit[hitA] = (k + 1) * dt_min / 60; who[hitA] = 1
        t_exit[hitB] = (k + 1) * dt_min / 60; who[hitB] = 2
        alive &= ~(hitA | hitB)
        if not alive.any(): break
    pay_down = piA if early_target is None else ((LB - LA) * CS * down - 0.12 * (LA + LB) * CS)
    return dict(t=t_exit, who=who, piA=piA, piB=piB, pay_down=pay_down, dA=dA, dB=dB, down=down,
                x_end=x, LA=LA, LB=LB)

mc_rows = {}
cfgs = {"S01 benchmark": (0.38, 0.53, 2000, 2000),
        "S04 (tau<=38.5h)": (r4["LA"], r4["LB"], r4["DA"], r4["DB"]),
        "Frontiera tau<=8h": (front[3]["LA"], front[3]["LB"], front[3]["DA"], front[3]["DB"])}
for name, (LA, LB, DA, DB) in cfgs.items():
    for sig in (0.15, 0.20, 0.30):
        m = mc(LA, LB, DA, DB, sig_ann=sig, n=4000, horizon_h=72, dt_min=2)
        t = m["t"]
        probs = {h: float(np.mean(t <= h)) for h in (1, 4, 8, 12, 24, 48, 72)}
        done = np.isfinite(t)
        shareA = float(np.mean(m["who"][done] == 1)) if done.any() else float("nan")
        mc_rows[f"{name} | sigma={sig}"] = dict(probs=probs, median_h=float(np.median(t)) if np.mean(done) > 0.5 else None,
                                                shareA=shareA, pA_theory=m["dB"] / (m["dA"] + m["dB"]))
R["montecarlo"] = mc_rows

# S07 time stop sul benchmark (sigma 20%): esito alla scadenza = P&L direzionale netto - costi, bonus non consumato
ts = {}
m = mc(0.38, 0.53, 2000, 2000, sig_ann=0.20, n=2000, horizon_h=48, dt_min=2)
for T in (1, 4, 8, 12, 24, 48):
    # ricostruisci: chi è uscito entro T prende il payoff terminale, gli altri chiudono a x(T) ~ approssimato con x_end
    # (ri-simulazione esplicita per ciascun T per evitare look-ahead)
    mm = mc(0.38, 0.53, 2000, 2000, sig_ann=0.20, n=4000, horizon_h=T, dt_min=2)
    done = np.isfinite(mm["t"])
    pay = np.where(mm["who"] == 1, mm["piA"], np.where(mm["who"] == 2, mm["piB"], 0.0))
    open_pnl = -(0.53 - 0.38) * CS * mm["x_end"] - 0.12 * (0.38 + 0.53) * CS
    nights = math.floor(T / 24)
    open_pnl = open_pnl + swap_cost(0.38, 0.53, nights)
    pay = np.where(done, pay, open_pnl)
    ts[T] = dict(p_complete=float(done.mean()), mean=float(pay.mean()), p5=float(np.percentile(pay, 5)),
                 p_loss=float((pay < 0).mean()), mean_per_h=float(pay.mean() / np.mean(np.minimum(mm["t"], T))))
R["timestop"] = ts

# S06 chiusura anticipata: target di profitto sul lato ribassista (A in profitto netto short)
es = {}
for tgt in (200, 300, 400, 500, 600):
    mm = mc(0.38, 0.53, 2000, 2000, sig_ann=0.20, n=3000, horizon_h=240, dt_min=2, early_target=tgt)
    done = np.isfinite(mm["t"])
    pay = np.where(mm["who"] == 1, mm["pay_down"], mm["piB"])
    pB = mm["dA"] and (mm["down"] / (mm["down"] + mm["dB"]))
    es[tgt] = dict(down_pct=mm["down"] / P0 * 100, p_up=float(np.mean(mm["who"][done] == 2)),
                   ev=float(pay[done].mean()), pmin=float(min(mm["pay_down"], mm["piB"])),
                   tau_theory=mm["down"] * mm["dB"] / SIG_H ** 2, ev_theory=(mm["dB"] / (mm["down"] + mm["dB"])) * mm["pay_down"] + (mm["down"] / (mm["down"] + mm["dB"])) * mm["piB"])
R["early"] = es

# ---------------- STRESS ----------------
def stress_cfg(DA, DB, LA, LB):
    out = {}
    for mult in (1, 2, 3, 5):
        out[f"spread x{mult} (${0.12*mult:.2f}/oz)"] = summ(mk(DA, DB, LA, LB, spread=0.12 * mult))["pmin"]
    out["spread $1.20/oz (interpretazione '12 pips'=120$/lotto)"] = summ(mk(DA, DB, LA, LB, spread=1.20))["pmin"]
    for sl in (0.5, 1, 2, 5, 10):
        s = mk(DA, DB, LA, LB, slip_stop=sl, slip_close=sl)
        out[f"slippage {sl}$ (stop + chiusura superstite avversi)"] = summ(s)["pmin"]
    for sl in (0.5, 1, 2, 5, 10):
        s = mk(DA, DB, LA, LB, slip_stop=0.0, slip_close=sl)
        out[f"solo latenza superstite {sl}$"] = summ(s)["pmin"]
    for lat in (0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 30):
        # slippage atteso avverso al 95° pct da latenza con vol 3x in fase di stop-out
        sig_s = 3 * SIG_H / 3600 ** 0.5
        sl = 1.645 * sig_s * lat ** 0.5
        out[f"latenza {lat}s (q95, vol x3) -> {sl:.2f}$"] = summ(mk(DA, DB, LA, LB, slip_close=sl))["pmin"]
    for dv in (-5, -2, -1, 1, 2, 5):
        out[f"divergenza quotazioni B {dv:+}$"] = summ(mk(DA, DB, LA, LB, quote_div=dv))["pmin"]
    out["bonus regime 'remove' (credito rimosso a equity<=credito)"] = summ(mk(DA, DB, LA, LB, regime="remove"))["pmin"]
    out["bonus 50%"] = summ(mk(DA, DB, LA, LB, bonus=0.5))["pmin"]
    out["bonus 0% (non rinnovato)"] = summ(mk(DA, DB, LA, LB, bonus=0.0))["pmin"]
    out["leva B 1:500"] = summ(mk(DA, DB, LA, LB, levB=500))["pmin"]
    out["leva B 1:100"] = summ(mk(DA, DB, LA, LB, levB=100))["pmin"]
    out["leva A 1:100"] = summ(mk(DA, DB, LA, LB, levA=100))["pmin"]
    for n_ in (1, 3, 5):
        out[f"swap {n_} notti (USD/lotto/notte, ipotesi)"] = summ(mk(DA, DB, LA, LB, nights=0))["pmin"] + swap_cost(LA, LB, n_)
    # profitti scenario A annullati (clausola abuso): B restituisce solo il deposito
    sa = summ(mk(DA, DB, LA, LB))
    out["profitti B annullati (scenario A)"] = sa["recA_A"] + DB - DA - DB
    # mancata chiusura del superstite per 1h: sd P&L
    out["superstite non chiuso 1h: dev.std P&L ($)"] = -max(LA, LB) * CS * SIG_H
    return out

def breakeven(DA, DB, LA, LB):
    def bisect(f, lo, hi):
        for _ in range(60):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if f(mid) > 0 else (lo, mid)
        return lo
    return dict(spread=bisect(lambda s: summ(mk(DA, DB, LA, LB, spread=s))["pmin"], 0, 50),
                slip=bisect(lambda s: summ(mk(DA, DB, LA, LB, slip_stop=s, slip_close=s))["pmin"], 0, 200),
                div=bisect(lambda s: summ(mk(DA, DB, LA, LB, quote_div=s))["pmin"], 0, 200),
                div_neg=-bisect(lambda s: summ(mk(DA, DB, LA, LB, quote_div=-s))["pmin"], 0, 200))

stress = {}
for name, (LA, LB, DA, DB) in {**cfgs, "Frontiera tau<=1h": (front[0]["LA"], front[0]["LB"], front[0]["DA"], front[0]["DB"])}.items():
    stress[name] = dict(table=stress_cfg(DA, DB, LA, LB), be=breakeven(DA, DB, LA, LB),
                        cfg=dict(DA=DA, DB=DB, LA=LA, LB=LB))
R["stress"] = stress

# ---------------- REBALANCE (S12) ----------------
b = summ(mk(2000, 2000, 0.38, 0.53))
R["rebalance"] = dict(
    after_A=dict(cash_A=b["recA_A"], cash_B=b["recB_A"], to_move_B_to_A=2000 - b["recA_A"],
                 withdraw_profit=b["recA_A"] + b["recB_A"] - 4000),
    after_B=dict(cash_A=b["recA_B"], cash_B=b["recB_B"], to_move_A_to_B=2000,
                 withdraw_profit=b["recA_B"] - 2000),
    reserve_needed=2000 - b["recA_A"],
    roi_on_immobilized=b["pmin"] / (4000 + 2000) * 100)

# Bridge EV / RoboForex EV (trasferimento economico)
pA = b["pA"]
R["transfer"] = dict(pA=pA, EV_user=b["ev"],
                     EV_bonus_broker=pA * -(b["recB_A"] - 2000) + (1 - pA) * 2000,
                     EV_A_broker=pA * (2000 - b["recA_A"]) + (1 - pA) * -(b["recA_B"] - 2000))

json.dump(R, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=float)
print("ok")
