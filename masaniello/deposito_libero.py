"""Deposito A libero (bonus 25%), lotti A max 0,70: lotti ottimali per bruciare A in un colpo e chiudere in utile in entrambi gli esiti.
A: leva 1:500 stop-out 30%; B: leva 1:1000 stop-out 50%. Solo XAUUSD, SL $25 / TP $12,5."""
import numpy as np
from ciclo500 import ciclo, V, P0, EURUSD
LEVA, SOA, LEVB, SOB = 500, .30, 1000, .50
def best(D, sp, lamax=0.70):
    out = None
    for LA in np.round(np.arange(0.01, lamax + 1e-9, 0.01), 2):
        for LB in np.round(np.arange(0.01, LA + 1e-9, 0.01), 2):
            t, s, dA, ok, recA = ciclo(LA, LB, D, .25 * D, 1e6, LEVA, SOA, LEVB, SOB, sp)
            if not ok or dA > 25 - 1e-9 and recA > 0.5: continue   # deve bruciare in un colpo
            m = min(t, s)
            if out is None or m > out[0]: out = (m, LA, LB, t, s, dA)
    return out
if __name__ == "__main__":
    mB = 100 * P0 / LEVB / EURUSD
    for D in (200, 300, 400, 500, 645, 750, 1000, 1285, 1500):
        row = [f"{D:5d}"]
        for sp in (0.12, 0.30):
            r = best(D, sp)
            if r is None: row.append("non bruciabile"); continue
            m, LA, LB, t, s, dA = r
            Bmin = 12.5 * V * LB + SOB * mB * LB + sp * V * LB
            row.append(f"LA {LA:.2f} LB {LB:.2f} TP {t:6.1f} SO {s:6.1f} d {dA:5.2f} Bmin {Bmin:5.0f}")
        print(" | ".join(row))
