"""Ciclo singolo: A long con bonus (SL 25 / TP 12,5), B short senza bonus, lotti non speculari.
Valuta del conto EUR. Ipotesi dichiarate in testa."""
import numpy as np
EURUSD = 1.16                  # IPOTESI
V = 100 / EURUSD               # EUR per punto per lotto (XAUUSD, 1 punto = 1 $)
P0 = 3620.0                    # IPOTESI (solo margine)
SL, TP = 25.0, 12.5
p_TP = SL / (SL + TP)          # driftless: P(TP prima di SL) = 2/3

def ciclo(LA, LB, D, C, DB, levA, soA, levB, soB, spread):
    mA = LA * 100 * P0 / levA / EURUSD; mB = LB * 100 * P0 / levB / EURUSD
    costA, costB = spread * V * LA, spread * V * LB
    EA = D + C - costA
    # distanza dello stop-out di A (se prima dello SL)
    dA = min(SL, (EA - soA * mA) / (V * LA))
    # esito SL / stop-out
    balA = D - costA - V * LA * dA
    recA = max(balA, 0.0)                     # credito non prelevabile, NBP
    net_SL = recA + (DB - costB + V * LB * dA) - D - DB
    # esito TP: B non deve andare in stop-out prima di +12,5
    ok = (DB - costB - V * LB * TP) > soB * mB and dA > 0
    net_TP = (D - costA + V * LA * TP) + (DB - costB - V * LB * TP) - D - DB
    return net_TP, net_SL, dA, ok, recA

def best(D, C, DB, levA, soA, levB, soB, spread, mode="maxmin"):
    out = None
    for LA in np.round(np.arange(0.01, 3.0, 0.01), 2):
        for LB in np.round(np.arange(0.01, LA + 0.001, 0.01), 2):
            t, s, dA, ok, recA = ciclo(LA, LB, D, C, DB, levA, soA, levB, soB, spread)
            if not ok: continue
            score = min(t, s) if mode == "maxmin" else (s if t >= 0 else -1e9)
            if out is None or score > out[0]:
                out = (score, LA, LB, t, s, dA)
    return out

if __name__ == "__main__":
    for C in (125, 500):
        for (levA, soA) in ((1000, .8), (1000, .5), (500, .5), (1000, .2)):
            for sp in (0.12, 0.30):
                r = best(500, C, 500, levA, soA, 400, .5, sp)
                if r is None: print(C, levA, soA, sp, "nessuna"); continue
                sc, LA, LB, t, s, dA = r
                ev_cycle = p_TP * t + (1 - p_TP) * s
                tot = 2 * t + s   # 2 TP attesi prima dello stop-out
                print(f"bonus {C} lev 1:{levA} SO {soA:.0%} spread {sp}: LA {LA} LB {LB} | TP {t:6.1f} | stop {s:6.1f} | dist stop {dA:5.2f} | EV/ciclo {ev_cycle:5.1f} | atteso fino al bruciamento {tot:6.1f}")
        r = best(500, C, 500, 1000, .8, 400, .5, 0.30, mode="tp0")
        sc, LA, LB, t, s, dA = r
        print(f"  [TP>=0, max stop] bonus {C}: LA {LA} LB {LB} TP {t:.1f} stop {s:.1f}")
