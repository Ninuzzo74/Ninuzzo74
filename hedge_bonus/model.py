"""
Modello quantitativo per hedge cross-broker con bonus (Conto A senza bonus, Conto B con bonus).

Convenzioni
-----------
- Prezzi in USD/oz, mid price. Lo spread completo s ($/oz) è addebitato una sola volta
  all'apertura come mark-to-market (long apre ad ask, valutato a bid; short simmetrico).
  Nessun ulteriore addebito in chiusura -> nessun doppio conteggio.
- Commissione: USD per lotto round-turn, addebitata all'apertura.
- Swap: USD per lotto per notte (unità DICHIARATA ma non verificata), segno broker.
- Margine statico: L*CS*P0/lev. Dinamico: L*CS*P/lev.
- Stop-out: Equity/Margin <= so (frazione, es. 0.5 = 50%).
- Bonus regime:
    'absorb'  : il credito assorbe le perdite (dichiarato). Prelevabile = max(balance, 0);
                il credito non è mai prelevabile. NBP: balance negativo azzerato.
    'remove'  : il credito viene rimosso quando Equity <= Credito (clausola frequente):
                lo stop-out effettivo avviene a perdita = capitale proprio.
- Conto senza bonus: NBP (balance negativo azzerato) - IPOTESI.
"""
from __future__ import annotations
from dataclasses import dataclass, replace, field
import math
import numpy as np

CS_GOLD = 100.0


@dataclass
class Acct:
    deposit: float
    bonus_pct: float
    lev: float
    so: float            # stop-out margin level (fraction)
    lots: float
    direction: int       # +1 long, -1 short
    spread: float = 0.12        # $/oz full spread (12 punti = $12/lotto) - DICHIARATO/ipotesi unità
    comm_per_lot: float = 0.0   # USD round-turn per lotto
    swap_per_lot: float = 0.0   # USD per lotto per notte (segno incluso)
    bonus_regime: str = "absorb"

    @property
    def credit(self):
        return self.deposit * self.bonus_pct

    def cost_open(self, cs=CS_GOLD):
        return self.spread * self.lots * cs + self.comm_per_lot * self.lots

    def margin(self, price, cs=CS_GOLD):
        return self.lots * cs * price / self.lev


@dataclass
class Setup:
    A: Acct
    B: Acct
    P0: float = 3620.0
    cs: float = CS_GOLD
    dynamic_margin: bool = True
    nights: int = 0              # notti di swap
    slip_stop: float = 0.0       # $/oz slippage avverso sull'esecuzione dello stop-out
    slip_close: float = 0.0      # $/oz slippage avverso sulla chiusura del superstite (latenza)
    quote_div: float = 0.0       # $/oz divergenza quotazioni: B quota P + div (rischio basis)


def stop_price(acc: Acct, P0, cs, dynamic, extra_cost=0.0):
    """Prezzo mid di stop-out del conto. Ritorna (prezzo, distanza $ avversa, equity residua)."""
    L = acc.lots * cs
    if L <= 0:
        return (math.nan, math.inf, acc.deposit + acc.credit)
    E0 = acc.deposit + acc.credit - acc.cost_open(cs) - extra_cost
    if dynamic:
        k = acc.so / acc.lev
        if acc.direction > 0:
            P = (L * P0 - E0) / (L * (1 - k))
        else:
            P = (L * P0 + E0) / (L * (1 + k))
        M = acc.margin(P, cs)
    else:
        M = acc.margin(P0, cs)
        d = (E0 - acc.so * M) / L
        P = P0 - d if acc.direction > 0 else P0 + d
    res = acc.so * M
    if acc.bonus_regime == "remove" and acc.credit > 0 and acc.credit > res:
        # trigger: equity = credito
        d = (E0 - acc.credit) / L
        P = P0 - d if acc.direction > 0 else P0 + d
        res = acc.credit
    d = abs(P - P0)
    return P, d, res


def withdrawable(acc: Acct, equity_closed: float):
    """Liquidità prelevabile dopo la chiusura di tutte le posizioni."""
    balance = equity_closed - acc.credit
    return max(balance, 0.0)


def scenario(setup: Setup, which: str):
    """which = 'A' (stop-out conto A) o 'B'. Ritorna dict con risultati del ciclo."""
    A, B, P0, cs = setup.A, setup.B, setup.P0, setup.cs
    swapA = A.swap_per_lot * A.lots * setup.nights
    swapB = B.swap_per_lot * B.lots * setup.nights
    stopped, other = (A, B) if which == "A" else (B, A)
    sw_st, sw_ot = (swapA, swapB) if which == "A" else (swapB, swapA)
    Pst, d, res = stop_price(stopped, P0, cs, setup.dynamic_margin, extra_cost=-sw_st)
    # esecuzione stop-out con slippage avverso al conto fermato
    Pexec = Pst - stopped.direction * setup.slip_stop
    eq_st = (stopped.deposit + stopped.credit - stopped.cost_open(cs) + sw_st
             + stopped.direction * stopped.lots * cs * (Pexec - P0))
    # NBP: equity negativa azzerata (il credito resta perso)
    eq_st_c = max(eq_st, 0.0)
    rec_st = withdrawable(stopped, eq_st_c)
    # superstite chiuso con latenza: slippage avverso al superstite
    Pc = Pexec - other.direction * setup.slip_close
    if other is B:
        Pc = Pc + setup.quote_div
    eq_ot = (other.deposit + other.credit - other.cost_open(cs) + sw_ot
             + other.direction * other.lots * cs * (Pc - P0))
    rec_ot = withdrawable(other, max(eq_ot, 0.0))
    recA, recB = (rec_st, rec_ot) if which == "A" else (rec_ot, rec_st)
    own = A.deposit + B.deposit
    profit = recA + recB - own
    return dict(which=which, P_stop=Pst, dist=d, dist_pct=d / P0 * 100, residual_equity=res,
                eq_stopped=eq_st, recA=recA, recB=recB, profit=profit, roi=profit / own * 100,
                bonus_lost=(B.credit if (which == "B") else 0.0))


def analyse(setup: Setup):
    sa, sb = scenario(setup, "A"), scenario(setup, "B")
    dA, dB = sa["dist"], sb["dist"]
    # driftless BM: P(stop A prima) = dB/(dA+dB) ; E[tau] = dA*dB/sigma^2
    pA = dB / (dA + dB)
    ev = pA * sa["profit"] + (1 - pA) * sb["profit"]
    return dict(A=sa, B=sb, pA=pA, pB=1 - pA, ev=ev,
                pmin=min(sa["profit"], sb["profit"]), dAdB=dA * dB)


def acct_table(setup: Setup):
    rows = []
    for name, a in (("A", setup.A), ("B", setup.B)):
        M = a.margin(setup.P0, setup.cs)
        eq = a.deposit + a.credit - a.cost_open(setup.cs)
        rows.append(dict(conto=name, deposit=a.deposit, credit=a.credit, equity0=eq,
                         lots=a.lots, dir="Long" if a.direction > 0 else "Short",
                         notional=a.lots * setup.cs * setup.P0, margin=M,
                         ml0=eq / M * 100, lev_eff=a.lots * setup.cs * setup.P0 / eq))
    return rows


def benchmark(**kw):
    A = Acct(2000, 0.0, 400, 0.50, 0.38, +1)
    B = Acct(2000, 1.0, 1000, 0.80, 0.53, -1)
    s = Setup(A, B)
    for k, v in kw.items():
        if hasattr(s, k):
            setattr(s, k, v)
    return s


def sigma_hourly_usd(sig_ann, P0, hours_per_year=252 * 23):
    return sig_ann * P0 / math.sqrt(hours_per_year)
