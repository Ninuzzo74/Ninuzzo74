# Dashboard Conto Unificato

Unisce più conti MetaTrader 5 in un unico conto e genera una pagina HTML da pubblicare sul sito.
I conti vengono letti con la **password investor**, quindi in sola lettura: lo script non può aprire né chiudere operazioni.

## File

| File | A cosa serve |
|---|---|
| `aggiorna_da_mt5.py` | Legge i conti da MT5, li unisce e genera la pagina |
| `genera_dashboard.py` | Crea la pagina HTML dai dati e applica la privacy |
| `template.html` | Grafica e funzioni della pagina |
| `config_conti.esempio.json` | Modello per la configurazione dei conti |
| `aggiorna.bat` | Avvio con doppio clic o dall'Utilità di pianificazione di Windows |
| `dati/` | Dati simulati per la pagina di esempio `conto-unificato.html` |

Non vanno su GitHub (sono in `.gitignore`): `config_conti.json` con le password, `dati_mt5/` con i dati veri, `pubblica/` con la pagina vera, `aggiorna.log`.

## Prima installazione (PC Windows con MetaTrader 5)

1. Installa Python da https://www.python.org (spunta "Add python.exe to PATH").
2. Installa la libreria di MetaTrader 5:
   ```
   py -m pip install MetaTrader5
   ```
3. Copia `config_conti.esempio.json` in `config_conti.json` e inserisci per ogni conto: numero di conto (`login`), password investor e nome esatto del server, come appare nella finestra di login di MT5.
   Se MetaTrader 5 non è nella cartella standard, correggi `terminale` con il percorso di `terminal64.exe`.
4. Lancia `aggiorna.bat` con un doppio clic, oppure:
   ```
   py aggiorna_da_mt5.py
   ```
5. Apri `pubblica\index.html` nel browser e controlla che il saldo sia la somma dei saldi dei conti in MT5.

## Aggiornamento automatico

Utilità di pianificazione di Windows → Crea attività di base → per esempio ogni ora → Avvia programma → `aggiorna.bat`.
Il PC deve essere acceso e connesso; l'esito di ogni aggiornamento finisce in `aggiorna.log`.

## Pubblicazione sul sito

Carica `pubblica\index.html` sul tuo hosting. Per farlo in automatico, in `config_conti.json` imposta `"attivo": true` nella sezione `ftp` e inserisci i dati FTP del sito (connessione cifrata FTPS).

## Privacy

In cima a `genera_dashboard.py`:

```python
PRIVACY = {
    "simboli": True,    # True = nascosto
    "apertura": True,
}
```

I dati nascosti vengono tolti dal file pubblicato, non solo coperti a video.

## Come vengono calcolati i numeri

- Ogni chiusura, anche parziale, è un'operazione. Il profitto è netto: profitto, swap, commissioni e fee.
- Capitale iniziale = depositi meno prelievi di tutti i conti.
- Saldo = capitale iniziale + operazioni chiuse; equity = saldo + flottante delle posizioni aperte.
- Gli orari sono quelli del server del broker.
- I conti devono avere la stessa valuta. La pagina mostra gli importi in euro.
