"""Aggiorna la dashboard del Conto Unificato dai conti MetaTrader 5.

Si collega a ogni conto indicato in config_conti.json con la password
investor (sola lettura), scarica operazioni chiuse e posizioni aperte,
unisce tutto in un unico conto e genera la pagina HTML in pubblica/.
Se nel file di configurazione l'FTP è attivo, carica anche la pagina sul sito.

Requisiti (solo Windows, con MetaTrader 5 installato):
    py -m pip install MetaTrader5

Uso:
    py aggiorna_da_mt5.py
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config_conti.json"
DATI = BASE / "dati_mt5"            # esclusa da GitHub
PAGINA = BASE / "pubblica" / "index.html"  # esclusa da GitHub

# Costanti di MetaTrader 5 (uguali a quelle del modulo MetaTrader5)
DEAL_TYPE_BUY, DEAL_TYPE_SELL, DEAL_TYPE_BALANCE = 0, 1, 2
DEAL_ENTRY_IN, DEAL_ENTRY_OUT, DEAL_ENTRY_INOUT, DEAL_ENTRY_OUT_BY = 0, 1, 2, 3
POSITION_TYPE_BUY = 0


def ora_server(secondi):
    """MT5 restituisce l'ora del server come secondi 'UTC': la lasciamo così."""
    return datetime.fromtimestamp(secondi, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")


def leggi_config():
    if not CONFIG.exists():
        sys.exit(f"Manca {CONFIG.name}. Copia config_conti.esempio.json in {CONFIG.name} e inserisci i dati dei conti.")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not cfg.get("conti"):
        sys.exit(f"In {CONFIG.name} non c'è nessun conto.")
    return cfg


def connetti(mt5, cfg, conto):
    kw = dict(login=int(conto["login"]), password=conto["password_investor"], server=conto["server"], timeout=60000)
    if cfg.get("terminale"):
        kw["path"] = cfg["terminale"]
    if not mt5.initialize(**kw):
        errore = mt5.last_error()
        mt5.shutdown()
        sys.exit(f"Conto {conto['nome']}: connessione non riuscita {errore}. Controlla login, password investor e server.")


def operazioni_chiuse(deals):
    """Una riga per ogni chiusura (anche parziale) di una posizione.

    Il profitto è netto: profitto + swap + commissioni + fee della chiusura,
    più la quota delle commissioni d'ingresso proporzionale ai lotti chiusi.
    """
    per_posizione = defaultdict(list)
    for d in deals:
        if d.type in (DEAL_TYPE_BUY, DEAL_TYPE_SELL):
            per_posizione[d.position_id].append(d)

    righe, costi_residui = [], {}
    for pos_id, lista in per_posizione.items():
        lista.sort(key=lambda d: d.time_msc)
        ingressi = [d for d in lista if d.entry in (DEAL_ENTRY_IN, DEAL_ENTRY_INOUT)]
        uscite = [d for d in lista if d.entry in (DEAL_ENTRY_OUT, DEAL_ENTRY_INOUT, DEAL_ENTRY_OUT_BY)]
        if not ingressi:
            continue
        lotti_in = sum(d.volume for d in ingressi) or 1.0
        costi_in = sum(d.commission + d.fee for d in ingressi)
        costi_residui[pos_id] = costi_in - costi_in * min(1.0, sum(u.volume for u in uscite) / lotti_in)
        primo = ingressi[0]
        tipo = "buy" if primo.type == DEAL_TYPE_BUY else "sell"
        for u in uscite:
            quota = costi_in * (u.volume / lotti_in)
            righe.append({
                "ticket": pos_id,
                "simbolo": u.symbol,
                "tipo": tipo,
                "lotti": round(u.volume, 2),
                "apertura": ora_server(primo.time),
                "chiusura": ora_server(u.time),
                "profitto": round(u.profit + u.swap + u.commission + u.fee + quota, 2),
            })
    return righe, costi_residui


def leggi_conto(mt5, cfg, conto):
    connetti(mt5, cfg, conto)
    try:
        info = mt5.account_info()
        dal = datetime.strptime(cfg.get("storico_dal", "2015-01-01"), "%Y-%m-%d")
        al = datetime.now() + timedelta(days=2)
        deals = mt5.history_deals_get(dal, al)
        if deals is None:
            sys.exit(f"Conto {conto['nome']}: impossibile leggere lo storico {mt5.last_error()}.")
        posizioni = mt5.positions_get() or ()

        depositi = round(sum(d.profit for d in deals if d.type == DEAL_TYPE_BALANCE), 2)
        chiuse, costi_residui = operazioni_chiuse(deals)
        # Commissioni d'ingresso della parte ancora aperta: il broker le ha già scalate dal saldo
        costi_aperte = sum(costi_residui.get(p.ticket, 0.0) for p in posizioni)
        aperte = [{
            "ticket": p.ticket,
            "apertura": ora_server(p.time),
            "simbolo": p.symbol,
            "tipo": "buy" if p.type == POSITION_TYPE_BUY else "sell",
            "lotti": round(p.volume, 2),
            "prezzo_apertura": p.price_open,
            "prezzo_attuale": p.price_current,
            "profitto": round(p.profit + p.swap, 2),
        } for p in posizioni]

        saldo_calcolato = depositi + sum(r["profitto"] for r in chiuse) + costi_aperte
        if abs(saldo_calcolato - info.balance) > 1:
            print(f"  Attenzione: conto {conto['nome']}, saldo MT5 {info.balance:.2f} ma ricalcolato {saldo_calcolato:.2f}. "
                  f"Controlla che 'storico_dal' sia prima della prima operazione o se ci sono crediti/bonus.")
        print(f"  Conto {conto['nome']} ({info.login}, {info.currency}): saldo {info.balance:.2f}, "
              f"equity {info.equity:.2f}, {len(chiuse)} chiusure, {len(aperte)} posizioni aperte")
        return {"valuta": info.currency, "depositi": depositi, "costi_aperte": costi_aperte,
                "chiuse": chiuse, "aperte": aperte}
    finally:
        mt5.shutdown()


def scrivi_csv(file, campi, righe):
    with file.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campi)
        w.writeheader()
        w.writerows(righe)


def carica_ftp(cfg_ftp, pagina):
    from ftplib import FTP_TLS
    with FTP_TLS(cfg_ftp["host"], timeout=60) as ftp:
        ftp.login(cfg_ftp["utente"], cfg_ftp["password"])
        ftp.prot_p()
        if cfg_ftp.get("cartella"):
            ftp.cwd(cfg_ftp["cartella"])
        with pagina.open("rb") as f:
            ftp.storbinary(f"STOR {cfg_ftp.get('nome_file', 'index.html')}", f)
    print(f"Pagina caricata su {cfg_ftp['host']}")


def main():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.exit("Manca la libreria MetaTrader5. Installala con:  py -m pip install MetaTrader5")

    cfg = leggi_config()
    print("Lettura dei conti...")
    conti = [leggi_conto(mt5, cfg, c) for c in cfg["conti"]]

    valute = {c["valuta"] for c in conti}
    if len(valute) > 1:
        sys.exit(f"I conti hanno valute diverse ({', '.join(sorted(valute))}): per unirli serve una conversione.")
    if valute != {"EUR"}:
        print(f"  Attenzione: i conti sono in {valute.pop()}, ma la pagina mostra gli importi in €.")

    chiuse = sorted((r for c in conti for r in c["chiuse"]), key=lambda r: r["chiusura"])
    aperte = [r for c in conti for r in c["aperte"]]
    # Capitale iniziale = depositi - prelievi; le commissioni delle posizioni
    # aperte sono già nel saldo, quindi le togliamo qui per farlo tornare.
    capitale = sum(c["depositi"] + c["costi_aperte"] for c in conti)

    DATI.mkdir(exist_ok=True)
    scrivi_csv(DATI / "operazioni.csv", ["ticket", "simbolo", "tipo", "lotti", "apertura", "chiusura", "profitto"], chiuse)
    scrivi_csv(DATI / "posizioni_aperte.csv",
               ["ticket", "apertura", "simbolo", "tipo", "lotti", "prezzo_apertura", "prezzo_attuale", "profitto"], aperte)
    (DATI / "conto.json").write_text(json.dumps({
        "capitale_iniziale": round(capitale, 2),
        "aggiornato": datetime.now().strftime("%Y-%m-%dT%H:%M"),
    }, indent=2), encoding="utf-8")
    print(f"Conto unificato: capitale iniziale {capitale:.2f}, {len(chiuse)} operazioni chiuse, {len(aperte)} posizioni aperte")

    sys.path.insert(0, str(BASE))
    from genera_dashboard import genera
    pagina = genera(DATI, PAGINA)

    ftp = cfg.get("ftp") or {}
    if ftp.get("attivo"):
        carica_ftp(ftp, pagina)


if __name__ == "__main__":
    main()
