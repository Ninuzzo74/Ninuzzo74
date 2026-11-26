"""Genera la dashboard del Conto Unificato.

Legge da una cartella di dati:
  - operazioni.csv        operazioni chiuse (tutti i conti, già uniti)
  - posizioni_aperte.csv  posizioni aperte
  - conto.json            capitale iniziale e data dell'ultimo aggiornamento
toglie i dati sensibili scelti in PRIVACY e scrive la pagina HTML.

I dati nascosti vengono eliminati dal file generato, non solo coperti a
video: chi apre il codice della pagina non li trova.

Uso:
    python3 genera_dashboard.py                      # dati di esempio
    python3 genera_dashboard.py CARTELLA_DATI USCITA # es. dati_mt5 pubblica/index.html
"""

import csv
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Privacy: True = il dato NON viene pubblicato, False = viene mostrato.
# ---------------------------------------------------------------------------
PRIVACY = {
    # Simboli (XAUUSD, EURUSD, ...). Nasconde anche il grafico per strumento
    # e i prezzi delle posizioni aperte, che rivelerebbero lo strumento.
    "simboli": True,
    # Data e ora di apertura delle operazioni. Nasconde anche la durata.
    "apertura": True,
}

BASE = Path(__file__).resolve().parent
TEMPLATE = BASE / "template.html"


def leggi_operazioni(cartella):
    righe = []
    with (cartella / "operazioni.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            righe.append([
                int(r["ticket"]),
                None if PRIVACY["simboli"] else r["simbolo"],
                r["tipo"],
                float(r["lotti"]),
                None if PRIVACY["apertura"] else r["apertura"],
                r["chiusura"],
                round(float(r["profitto"]), 2),
            ])
    righe.sort(key=lambda r: r[5])
    return righe


def leggi_posizioni(cartella):
    file = cartella / "posizioni_aperte.csv"
    if not file.exists():
        return []
    out = []
    with file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({
                "t": int(r["ticket"]),
                "o": None if PRIVACY["apertura"] else r["apertura"],
                "s": None if PRIVACY["simboli"] else r["simbolo"],
                "ty": r["tipo"],
                "l": float(r["lotti"]),
                "po": None if PRIVACY["simboli"] else float(r["prezzo_apertura"]),
                "pc": None if PRIVACY["simboli"] else float(r["prezzo_attuale"]),
                "p": round(float(r["profitto"]), 2),
            })
    return out


def genera(cartella_dati, uscita):
    cartella_dati, uscita = Path(cartella_dati), Path(uscita)
    conto = json.loads((cartella_dati / "conto.json").read_text(encoding="utf-8"))
    operazioni = leggi_operazioni(cartella_dati)
    if not operazioni:
        raise SystemExit("Nessuna operazione chiusa trovata: la dashboard non può essere generata.")
    js = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8")
    html = (html.replace("__TRADES__", js(operazioni))
                .replace("__OPEN__", js(leggi_posizioni(cartella_dati)))
                .replace("__PRIVACY__", js(PRIVACY))
                .replace("__START__", js(round(float(conto["capitale_iniziale"]), 2)))
                .replace("__UPDATED__", js(conto["aggiornato"])))
    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_text(html, encoding="utf-8")
    print(f"Creato {uscita} (privacy: {PRIVACY})")
    return uscita


if __name__ == "__main__":
    if len(sys.argv) == 3:
        genera(sys.argv[1], sys.argv[2])
    else:
        genera(BASE / "dati", BASE / "conto-unificato.html")
