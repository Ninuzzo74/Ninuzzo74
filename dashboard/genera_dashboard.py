"""Genera la dashboard del Conto Unificato.

Legge le operazioni da dati/operazioni.csv e le posizioni aperte da
dati/posizioni_aperte.csv, toglie i dati sensibili scelti in PRIVACY e
scrive conto-unificato.html, pronto da pubblicare.

I dati nascosti vengono eliminati dal file generato, non solo coperti a
video: chi apre il codice della pagina non li trova.

Uso:
    python3 genera_dashboard.py
"""

import csv
import json
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
OPERAZIONI = BASE / "dati" / "operazioni.csv"
POSIZIONI = BASE / "dati" / "posizioni_aperte.csv"
USCITA = BASE / "conto-unificato.html"


def leggi_operazioni():
    righe = []
    with OPERAZIONI.open(newline="", encoding="utf-8") as f:
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


def leggi_posizioni():
    if not POSIZIONI.exists():
        return []
    out = []
    with POSIZIONI.open(newline="", encoding="utf-8") as f:
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


def main():
    js = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8")
    html = (html.replace("__TRADES__", js(leggi_operazioni()))
                .replace("__OPEN__", js(leggi_posizioni()))
                .replace("__PRIVACY__", js(PRIVACY)))
    USCITA.write_text(html, encoding="utf-8")
    print(f"Creato {USCITA.name} (privacy: {PRIVACY})")


if __name__ == "__main__":
    main()
