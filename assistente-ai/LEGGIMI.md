# Assistente AI personale

Un assistente basato su **Claude** che risponde seguendo **le tue impostazioni** (nome, tono, lingua, istruzioni, regole) e salva ogni conversazione **in ordine cronologico**.

## Cosa serve

1. **Python 3.10 o più recente**: scaricalo da https://www.python.org/downloads/
2. **Una chiave API di Anthropic**: creala su https://console.anthropic.com/ (sezione *API Keys*). L'uso si paga a consumo, in base a quanto scrivi.

## Installazione (una volta sola)

Apri il terminale nella cartella `assistente-ai` e scrivi:

```bash
pip install -r requirements.txt
```

## Avvio

Imposta la chiave e avvia l'app.

**Mac / Linux**
```bash
export ANTHROPIC_API_KEY="la-tua-chiave"
streamlit run app.py
```

**Windows (PowerShell)**
```powershell
$env:ANTHROPIC_API_KEY="la-tua-chiave"
streamlit run app.py
```

Si apre il browser con la chat. Non condividere mai la chiave e non salvarla nei file del progetto.

## Come si usa

- **⚙️ Impostazioni** (barra a sinistra): scegli il modello, il tono, la lingua, la lunghezza delle risposte, cosa deve sapere di te, le istruzioni e le regole. Premi *Salva impostazioni*: valgono dal messaggio successivo, anche a conversazione già iniziata. Le impostazioni sono salvate in `impostazioni.json`, che puoi anche modificare a mano.
- **🕑 Cronologia**: tutte le conversazioni, dalla più recente, con data e ora. Cliccane una per riaprirla e continuarla.
- **➕ Nuova conversazione**: ricomincia da capo con le impostazioni attuali.

Le conversazioni sono salvate come file nella cartella `conversazioni/` (una per file, con l'ora di ogni messaggio). Questa cartella **non** viene caricata su GitHub.

## Modelli disponibili

| Modello | Quando usarlo |
|---|---|
| Claude Opus 5.5 | Il più capace: testi importanti, strategie, analisi |
| Claude Sonnet 5.5 | Veloce ed economico, ottimo per l'uso quotidiano |
| Claude Haiku 5.5 | Rapidissimo e costa pochissimo, per richieste semplici |

L'**impegno** stabilisce quanto il modello ragiona prima di rispondere: più alto vuol dire risposte più accurate, ma più lente e più costose.
