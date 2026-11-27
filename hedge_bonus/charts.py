import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["text.parse_math"] = False
from model import Acct, Setup, analyse

D = os.path.dirname(__file__)
R = json.load(open(os.path.join(D, "results", "results.json")))
BLUE, ORANGE, AQUA, INK, INK2, GRID = "#257de0", "#f47230", "#00b894", "#191919", "#666666", "#e7e7e7"
plt.rcParams.update({"text.usetex": False, "axes.formatter.use_mathtext": False,"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white"})

# 1) Valore economico prelevabile (chiusura simultanea al prezzo P) vs prezzo - benchmark
P0, CS = 3620, 100
LA, LB, DA, DB, C, sp = 0.38, 0.53, 2000, 2000, 2000, 0.12
r = analyse(Setup(Acct(DA, 0, 400, .5, LA, 1, spread=sp), Acct(DB, 1, 1000, .8, LB, -1, spread=sp)))
PA, PB = r["A"]["P_stop"], r["B"]["P_stop"]
P = np.linspace(PA, PB, 400)
balA = DA - sp * LA * CS + LA * CS * (P - P0)
balB = DB - sp * LB * CS - LB * CS * (P - P0)          # balance proprio (credito escluso)
own = np.maximum(balA, 0) + np.maximum(balB, 0) - (DA + DB)
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
ax.plot(P, own, color=BLUE, lw=2, label="Chiusura simultanea a P (bonus non incassato)")
ax.scatter([PA, PB], [r["A"]["profit"], r["B"]["profit"]], s=60, color=ORANGE, zorder=5,
           edgecolor="white", linewidth=2, label="Esito terminale (stop-out + chiusura superstite)")
for x, y, t in ((PA, r["A"]["profit"], f"Stop-out A\n{PA:,.1f}  (+${r['A']['profit']:,.0f})"),
                (PB, r["B"]["profit"], f"Stop-out B\n{PB:,.1f}  (+${r['B']['profit']:,.0f})")):
    ax.annotate(t, (x, y), xytext=(0, 14), textcoords="offset points", ha="center", color=INK, fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.axvline(P0, color=INK2, lw=0.8, ls=":")
ax.set_xlabel("Prezzo XAUUSD (mid)"); ax.set_ylabel("Profitto economico prelevabile ($)")
ax.set_title("S01 benchmark: payoff prelevabile vs prezzo", color=INK, loc="left", fontsize=11)
ax.legend(frameon=False, loc="upper center", fontsize=8.5)
ax.set_ylim(-800, 1050); ax.legend(frameon=False, loc="lower left", fontsize=8.5)
fig.tight_layout(); fig.savefig(os.path.join(D, "results", "payoff_vs_price.png")); plt.close(fig)

# 2) Frontiera di Pareto profitto minimo vs durata attesa
F = R["frontier"]
tau = [f["tau_h"] for f in F]; pm = [min(f["full_piA"], f["full_piB"]) for f in F]
fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
ax.plot(tau, pm, color=BLUE, lw=2, marker="o", ms=6, mec="white", mew=1.5, label="Frontiera (K=$4.000, spread $0,12/oz)")
ax.axhline(828.43, color=INK2, lw=1, ls="--")
ax.text(250, 840, "Limite teorico (lotti→0, costi 0): $828", color=INK2, ha="right", fontsize=8.5)
b = R["strategies"]["S01"]
ax.scatter([b["tau"]], [b["pmin"]], s=70, color=ORANGE, zorder=5, edgecolor="white", linewidth=2, label="S01 benchmark")
for f, t, p in zip(F, tau, pm):
    if abs(t - 46.5) < 1: continue
    ax.annotate(f"{f['LA']:.2f}/{f['LB']:.2f}", (t, p), xytext=(4, -12), textcoords="offset points", fontsize=7.5, color=INK2)
ax.set_xscale("log"); ax.set_xlabel("Durata attesa E[τ] (ore, σ=20% annuo, moto browniano)")
ax.set_ylabel("Profitto minimo ($)")
ax.set_title("Frontiera: profitto minimo vs durata (etichette = lotti A/B)", color=INK, loc="left", fontsize=11)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
fig.tight_layout(); fig.savefig(os.path.join(D, "results", "frontier.png")); plt.close(fig)

# 3) Heatmap profitto minimo (allocazione B x lotti A, LB=0.53)
H = R["heatmap"]; z = np.array(H["z"])
fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
lim = np.nanmax(np.abs(z))
im = ax.imshow(z, origin="lower", aspect="auto", cmap="RdBu", vmin=-lim, vmax=lim,
               extent=[H["LA"][0] - .01, H["LA"][-1] + .01, H["xB"][0] * 100 - 1, H["xB"][-1] * 100 + 1])
cs = ax.contour(H["LA"], np.array(H["xB"]) * 100, z, levels=[0, 400, 600, 700], colors=INK, linewidths=0.8)
ax.clabel(cs, fmt="$%d", fontsize=7.5)
ax.scatter([0.38], [50], color=ORANGE, s=50, edgecolor="white", linewidth=1.5, zorder=5)
ax.set_xlabel("Lotti A (Lotti B = 0,53)"); ax.set_ylabel("Quota capitale su B (%)"); ax.grid(False)
ax.set_title("Profitto minimo ($) – K=$4.000; punto = benchmark", color=INK, loc="left", fontsize=11)
fig.colorbar(im, ax=ax, label="Profitto minimo ($)")
fig.tight_layout(); fig.savefig(os.path.join(D, "results", "heatmap.png")); plt.close(fig)
print("charts ok")
