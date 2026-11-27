# Handoff: strategia hedge oro con bonus

Repository `Ninuzzo74/Ninuzzo74`, branch `claude/eager-wozniak-tvsuwj`. Lingua dell'utente: **italiano**. Ha esperienza di trading ma non di programmazione: preferisce numeri, tabelle e risposte operative. A volte scrive a voce (ha scritto "Masamiya" per Masaniello) e a volte cambia ipotesi a metà discorso: conferma i parametri prima di calcolare.

## 1. La strategia attuale

Sono due conti presso **due broker diversi**, operativi **solo su oro (XAUUSD)**: contratto da 100 oz, quindi $100 di P&L per ogni $1 di movimento per lotto.

| | Conto A | Conto B |
|---|---|---|
| Bonus | **25% del deposito**, solo qui | nessuno |
| Direzione | sempre **long** | sempre **short** |
| Leva / stop-out | **1:500 / 30%** | **1:1000 / 50%** |
| Lotti massimi | **0,70** (alternativa 0,35) | ≤ lotti A |
| Uscite | TP **+$12,50**, SL **−$25** (dollari sul prezzo, confermato: non pip) | chiusura allo stesso prezzo di A |

- **Obiettivo dell'utente:** un colpo solo. A destra A chiude in TP e B perde meno di quanto guadagna A. A sinistra A va in stop-out, il bonus assorbe la perdita e B guadagna. In entrambi i casi il ciclo deve chiudere **in pari o in piccolo utile**.
- **Lotti di B:** non speculari, circa il 92% di quelli di A.
- **Deposito di A:** libero, purché A si bruci in un colpo con i lotti disponibili.

## 2. Risultati principali

Conto in EUR, EUR/USD 1,16, prezzo dell'oro 3.620 (usato solo per il margine), spread $0,20 per conto.

- **Formula chiave.** Con lotti ottimizzati il profitto per ciclo è al massimo **bonus ÷ 3** in entrambi gli esiti, e non dipende dal deposito. Stop-out residuo (credito perso) e spread lo riducono di circa la metà.
- **Configurazione di riferimento.** Deposito A €1.285 (bonus €321), **A long 0,69, B short 0,63**, B con almeno €790 (consigliati €1.000).
  - Lo stop-out di A scatta a **−$24,63**, prima dello SL: il TP di B va messo lì.
  - Il ciclo chiude a **+€42 sia al TP sia allo stop-out**.
  - P(TP) è circa 66% con prezzo senza tendenza, quindi in media A si brucia ogni 3 cicli: circa **+€124 per bonus consumato**.
- **Deposito massimo bruciabile in un colpo con 0,70 lotti:** circa **€1.320**, oppure circa $1.530 se il conto è in USD. Oltre, il ciclo perde.
- **Regola pratica:** lotti A ≈ deposito ÷ 1.870 (in EUR), lotti B ≈ 92% di A, capitale B ≈ 61% del deposito A.
- **Con SL di 25 pip ($2,50) la strategia non funziona mai.** Il residuo allo stop-out supera il bonus. L'utente ha confermato che si tratta di dollari.
- **Masaniello e progressioni non creano valore atteso.** P(riuscita) = 1/moltiplicatore esatto; più trade significa più spread. La soluzione migliore resta il colpo singolo.

## 3. Rischi già comunicati all'utente

Il rischio principale è contrattuale.

- **Bonus rimosso quando l'equity arriva al suo livello.** Se il bonus funziona così, invece di assorbire le perdite, ogni stop-out costa circa −€320: perdita certa.
- **Bonus cancellato al prelievo.** Dopo ogni TP, A sale a circa €2.017 e B scende a circa €310. Per ripetere il colpo va riportato A a €1.285 (prelievo di circa €732) e ricaricato B (circa €690). Se il prelievo cancella il bonus, la strategia si rompe.
- **Divieto di hedging verso altri broker.** Spesso è considerato abuso del bonus, con annullamento dei profitti.
- **Termini e condizioni del broker di A mai verificati.** Non conosciamo nemmeno il nome del broker. I T&C di Bridge Markets, il broker con bonus di una versione precedente della strategia, non si trovano online.
- **Rischi tecnici:** slippage e latenza nella chiusura di B, gap, swap oltre le 24 ore.

Regola da mantenere: non proporre modi per aggirare controlli o T&C dei broker. Una strategia incompatibile con il contratto va segnalata come "non eseguibile".

## 4. File nel repository

| Percorso | Contenuto |
|---|---|
| `simulatore/simulatore-bonus.html` | Sorgente dell'artifact. È HTML senza `<html>`/`<head>`, perché lo scheletro lo aggiunge la piattaforma. Due schede: **#oro** (ciclo one-shot, predefinita) e **#sequenze** (simulatore di sequenze di 3–5 trade con Bonus A/B, payout e obiettivo) |
| `simulatore/index.html` | Stesso contenuto, versione autonoma con doctype, da aprire con doppio clic. **Va rigenerata a ogni modifica** del file sopra (comando in §6) |
| `masaniello/ciclo500.py` | Funzione `ciclo()`: modello del singolo colpo, base di tutti i calcoli successivi |
| `masaniello/lotti_fissi.py` | Lotti A fissi (0,70 / 0,35), deposito ottimale |
| `masaniello/deposito_libero.py` | Deposito A libero, lotti ottimali con le condizioni attuali (1:500/30% e 1:1000/50%) |
| `masaniello/analisi.py` | Tabelle Masaniello con hedge speculare (versione con bonus da 5.000 e 25%) |
| `hedge_bonus/` | Prima analisi, ormai superata: RoboForex + Bridge Markets, bonus 100%, $2.000 + $2.000, 0,38/0,53 lotti. Contiene `REPORT.md`, modello Python, Monte Carlo, stress test e grafici. Utile come riferimento metodologico |

**Artifact pubblicato (privato):** https://claude.ai/artifact/72YuoucTT15DFhUiyToFS2. Si aggiorna ripubblicando `simulatore/simulatore-bonus.html`; un'altra conversazione deve passare `url` e prima fare una read.

## 5. Modello di calcolo (`ciclo()`, ripreso identico in JS nella scheda #oro)

```
V  = 100 / EURUSD                 # valuta del conto per $1 di oro per lotto (V = 100 se il conto è in USD)
mA = LA*100*P0/levA/EURUSD        # margine A
EA = D + 0.25*D - spread*V*LA     # equity A dopo lo spread
dA = min(SL, (EA - soA*mA)/(V*LA))   # distanza dello stop-out (o dello SL) di A
recA = max(D - spread*V*LA - V*LA*dA, 0)      # prelevabile di A (il credito non si preleva mai)
net_SO = recA - D - spread*V*LB + V*LB*dA
net_TP = V*TP*(LA-LB) - spread*V*(LA+LB)
vincoli: A si brucia in un colpo (recA ≈ 0); B regge la perdita al TP sopra lo stop-out
ottimo: max min(net_TP, net_SO) su griglia di lotti con passo 0,01
```

## 6. Comandi utili

Rigenerare la versione autonoma, dalla root del repository:

```bash
cd simulatore && { printf '<!doctype html>\n<html lang="it">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'; sed -n '1,/^<\/style>/p' simulatore-bonus.html; printf '</head>\n<body>\n'; sed -n '/^<\/style>/,$p' simulatore-bonus.html | tail -n +2; printf '</body>\n</html>\n'; } > index.html
```

Tabella dei depositi:

```bash
python3 masaniello/deposito_libero.py
```

Playwright e Chromium sono preinstallati e servono per gli screenshot di verifica.

## 7. Domande aperte (chiederle all'utente)

1. Nome dei due broker e **regolamento del bonus del 25%**: assorbe le perdite? Viene tolto al prelievo? L'hedging è vietato?
2. **Spread** reale sull'oro di entrambi i broker. Sposta il risultato tra circa +€30 e +€51 per ciclo con €1.285.
3. Valuta effettiva del conto A (EUR o USD).
4. I limiti sui lotti (0,70) valgono per singolo ordine o per esposizione totale?
5. Il bonus si ottiene di nuovo a ogni deposito, dopo lo stop-out?

## 8. Possibili passi successivi

- Simulare in sequenza più cicli con il ribilanciamento: capitale immobilizzato, riserva per B, rendimento per settimana.
- Monte Carlo sulla durata del ciclo con la volatilità dell'oro, se l'utente fornisce dati M1 o tick. Stima attuale: circa 1,5–6 ore per ciclo.
- Audit degli storici reali, se l'utente fornisce report MT4/MT5.
- Pubblicazione su GitHub Pages: l'utente non ha ancora risposto alla proposta di aprire una PR verso `main`. **Non creare PR senza richiesta esplicita.**
