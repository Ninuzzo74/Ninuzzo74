"""Lotti A fissi (0,70 / 0,35): deposito A ottimale col bonus 25% e lotti B per profitto in entrambi gli esiti."""
import numpy as np
from ciclo500 import ciclo, V, SL, TP
BON = 0.25
def run(LA, levA, soA, sp, levB=400, soB=.5):
    best = None
    for D in np.arange(100, 3001, 5.0):
        for LB in np.round(np.arange(0.01, LA + 1e-9, 0.01), 2):
            t, s, dA, ok, recA = ciclo(LA, LB, D, BON * D, 5000, levA, soA, levB, soB, sp)
            if not ok: continue
            m = min(t, s)
            if best is None or m > best[0]:
                best = (m, D, LB, t, s, dA, recA)
    return best
if __name__ == "__main__":
    print(f"V = {V:.2f} EUR/punto/lotto")
    for LA in (0.70, 0.35):
        print(f"\n=== Lotti A = {LA}: perdita a 25 punti = {25*V*LA:.0f} EUR")
        for levA, soA in ((1000, .5), (500, .5), (1000, .8), (1000, .2), (400, .5)):
            for sp in (0.12, 0.30):
                m, D, LB, t, s, dA, recA = run(LA, levA, soA, sp)
                bneed = 12.5 * V * LB
                print(f"lev 1:{levA} SO {soA:.0%} spread {sp}: deposito A {D:5.0f} (+bonus {BON*D:4.0f}) | LB {LB} | TP {t:6.1f} | stop {s:6.1f} | stop-out a {dA:5.2f} pt | EV/ciclo {(2*t+s)/3:5.1f} | perdita B se TP {bneed:4.0f}")
