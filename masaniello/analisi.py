"""Masaniello + hedge speculare con bonus. Ipotesi dichiarate nel report."""
from functools import lru_cache
from math import comb
SL, TP = 25.0, 12.0          # punti conto A (B speculare: SL 12 / TP 25)
PT = 100.0                   # $ per punto per lotto (XAUUSD, 1 punto = 1 $ di prezzo) - IPOTESI
DEP, BONUS = 5000.0, 0.25
P0 = 3620.0                  # solo per il margine - IPOTESI
LEV_B, SO_B = 1000, 0.80     # conto con bonus - IPOTESI (dalle condizioni precedenti)
LEV_N, SO_N = 400, 0.50      # conto senza bonus - IPOTESI
SPREAD = 0.30                # punti per trade per conto - IPOTESI

def masaniello(N, K, q):
    @lru_cache(None)
    def C(n, k):
        if k <= 0: return 1.0
        if k > n: return 0.0
        return (C(n-1, k-1) + (q-1)*C(n-1, k)) / q
    return C

def p_at_least(N, K, p):
    return sum(comb(N, i) * p**i * (1-p)**(N-i) for i in range(K, N+1))

def analizza(side):
    # side 'A': conto bonus fa SL25/TP12 ; 'B': conto bonus fa SL12/TP25
    sl, tp = (SL, TP) if side == 'A' else (TP, SL)
    q = 1 + tp/sl; p = sl/(sl+tp)     # prob. driftless di toccare TP prima di SL
    E = DEP*(1+BONUS); cap_mirror = DEP
    rows = []
    for N in range(1, 9):
        for K in range(1, N+1):
            C = masaniello(N, K, q)
            M = 1/C(N, K); G = E*(M-1)
            # stake max e lotti max lungo l'albero (per vincolo margine/specchio)
            maxlots = 0; exp_trades = 0
            def walk(n, k, cap, prob, played):
                nonlocal maxlots, exp_trades
                if k <= 0 or k > n or cap <= 1e-9:
                    exp_trades += prob*played; return
                stake = cap - C(n-1, k)/C(n, k)*cap
                lots = stake/(sl*PT); maxlots = max(maxlots, lots)
                walk(n-1, k-1, cap + stake*(q-1), prob*p, played+1)
                walk(n-1, k, cap - stake, prob*(1-p), played+1)
            walk(N, K, E, 1.0, 0)
            # residuo allo stop-out del conto bonus nel trade di azzeramento (lotti ~ ultimo stake = intero capitale)
            lots_wipe = E/(sl*PT)  # upper bound; nell'ultimo trade lo stake residuo e' minore
            res_b = SO_B*lots_wipe*PT*P0/LEV_B
            p_wipe = 1 - p_at_least(N, K, p)
            cost = exp_trades*2*SPREAD*PT*maxlots   # bound superiore
            feasible = G <= cap_mirror - SO_N*maxlots*PT*P0/LEV_N
            bonus_net = max(DEP*BONUS - res_b, 0)
            rows.append(dict(N=N, K=K, q=q, M=M, G=G, p_succ=1/M, p_succ_binom=p_at_least(N, K, p),
                             p_wipe=p_wipe, maxlots=maxlots, exp_trades=exp_trades, feasible=feasible,
                             ev_gross=p_wipe*DEP*BONUS, ev_net=p_wipe*bonus_net - cost, res=res_b, cost=cost))
    return q, p, rows

if __name__ == "__main__":
    for side in ('A', 'B'):
        q, p, rows = analizza(side)
        print(f"\n=== bonus sul lato {side}: quota {q:.4f}, p(vincita) {p:.4f}")
        for r in rows:
            if r['feasible'] and r['N'] <= 6:
                print(f"N={r['N']} K={r['K']} M={r['M']:.3f} G={r['G']:7.0f} Psucc={r['p_succ']:.3f}/{r['p_succ_binom']:.3f} "
                      f"Pazz={r['p_wipe']:.3f} lotmax={r['maxlots']:.2f} E[trade]={r['exp_trades']:.2f} "
                      f"EVlordo={r['ev_gross']:.0f} res={r['res']:.0f} costi<= {r['cost']:.0f} EVnetto={r['ev_net']:.0f}")
