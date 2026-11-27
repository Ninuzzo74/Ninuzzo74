# Hedge cross-broker con bonus: REPLICA · OPTIMIZE · CAPITAL · STRATEGY · MONTECARLO · STRESS

Data analisi: 27/11/2026. Codice: `model.py` (modello completo, margine dinamico), `optimize.py` (forma chiusa vettorizzata, margine statico), `run_all.py` (pipeline), `charts.py`. Risultati grezzi: `results/results.json`.

**Avvertenza di perimetro.** Nel repository non ci sono storici reali (CSV, report MT4/5, estratti conto), quindi **AUDIT e BACKTEST su dati reali non sono stati eseguiti**. Tutto ciò che segue è **teorico** (payoff deterministico) o **simulato** (Monte Carlo parametrico). Non ci sono risultati "reali".

---

## A. Sintesi

1. **Il benchmark è replicato.** Le distanze di stop-out sono 1,33% (A) e 2,00% (B), contro 1,33% e 2% dichiarati. Il profitto minimo vale **$709,8** con spread $0,12/oz, oppure $722,5 a costi nulli; il software dichiara $700. Lo scarto è del +1,4%, ed è compatibile con un costo implicito di circa $10 o con un arrotondamento.
2. **L'unica fonte di valore atteso è il bonus.** Con prezzo martingala, il P&L direzionale netto (short netto di 0,15 lotti) ha valore atteso nullo (optional stopping). Il valore atteso del ciclo è quindi E[π] ≈ P(stop-out B) × (perdita assorbita dal credito) − costi = 0,40 × ~$1.840 ≈ **$724**. Gli stessi numeri si leggono come un trasferimento: **il valore atteso del broker B è −$729 per ciclo, quello del broker A è ≈ $0**. Il "profitto in entrambi gli scenari" ha senso solo se il credito assorbe davvero le perdite e se i profitti generati su B sono effettivamente pagati.
3. **Il profitto minimo massimo è un ottimo degenere.** Riducendo i lotti, π_min → $828,4 = K·(√2−1)/2 (con 50/50 e r* = L_A/L_B = 1/√2), ma la durata attesa → ∞. L'obiettivo ben posto è una **frontiera profitto minimo / durata** (§D, §F). A parità di durata del benchmark (E[τ] ≈ 38,5 h con σ = 20%), l'ottimo congiunto lascia invariati i lotti (0,38/0,53) e sposta solo il capitale: **A $2.048 / B $1.952**. Il profitto minimo passa da $709,8 a **$725,8** (+2,3%). Il benchmark è quindi già quasi efficiente.
4. **Il ROI minimo teorico per ciclo è 17,7–18,2%** sul capitale versato. Sul capitale immobilizzato, compresa la riserva di ribilanciamento, scende a **≈11,8%**.
5. **La strategia non sopravvive ai rischi contrattuali.**
   - Se il credito viene rimosso quando equity ≤ credito (clausola diffusa), π_min = **−$575**.
   - Se i profitti su B vengono annullati per bonus abuse, la perdita è **−$1.830**.
   - Con bonus al 50% il profitto minimo è ≈ $30; con bonus a 0% è −$531.
   - Il rischio dominante è **contrattuale e di controparte**, non di mercato.
6. **I termini di Bridge Markets non sono verificati.** Non sono riuscito a reperire online i termini ufficiali. I termini 100% bonus di altri broker classificano esplicitamente come abuso il *hedging esterno / tra conti*. Finché non ci sono T&C scritti di Bridge Markets che consentono questa operatività, la strategia va classificata come **contrattualmente non verificata e probabilmente non eseguibile** (§G).

## B. Input

| Parametro | Valore usato | Stato | Nota |
|---|---|---|---|
| Capitale A / B | $2.000 / $2.000 | dichiarato | |
| Bonus B | 100% del deposito, credito non prelevabile | dichiarato | trattamento del saldo negativo **ipotizzato** (NBP: azzerato) |
| Assorbimento perdite dal credito | sì (regime `absorb`) | dichiarato, **non verificato** | alternativa `remove` testata in stress |
| Leva A / B | 1:400 / 1:1.000, fissa | dichiarato | leva applicata allo specifico CFD da verificare |
| Stop-out A / B | 50% / 80% | dichiarato | |
| Lotti A / B | 0,38 long / 0,53 short | dichiarato | coerenti con conti da $2.000 (ML0 580% / 2.082%) |
| Contract size | 100 oz | dichiarato | |
| P0 | 3.620 $/oz | dichiarato | |
| Spread | **$0,12/oz = $12/lotto**, addebitato una volta | unità **ipotizzata** | stress anche a $1,20/oz ("12 pips") |
| Commissioni | 0 | ipotizzato | |
| Swap | −30 long / +20 short in **USD/lotto/notte**, stessi valori sui due broker | unità **ipotizzata** | impatto trascurabile a 1 notte |
| Margine | dinamico (modello completo), statico (forma chiusa) | derivato | differenza < $3 |
| Margin level 980% | **non riconciliato** | dichiarato | nessuna combinazione coerente: A = 580%, B = 2.082%, aggregato = 1.120%, B a 1:400 = 834%. Il 980% richiederebbe 0,226 lotti su A o 1,128 su B |
| Volatilità oro | σ = 20% annuo (scenari 15/30%), t-Student ν=4, vol per-path lognormale (±35%) | **ipotizzato** | sostituire con stima da tick reali |
| Lot step / min / max | 0,01 / 0,01 / 100 | ipotizzato | |

## C. Risultati per conto: S01 benchmark (margine dinamico, spread $0,12/oz)

| | Conto A | Conto B |
|---|---|---|
| Capitale proprio / credito | 2.000 / 0 | 2.000 / 2.000 |
| Equity iniziale (dopo spread) | 1.995,4 | 3.993,6 |
| Direzione · lotti | Long · 0,38 | Short · 0,53 |
| Controvalore | 137.560 | 191.860 |
| Margine | 343,9 | 191,9 |
| Margin level iniziale | 580% | 2.082% |
| Leva effettiva (nozionale/equity) | 68,9× | 48,0× |
| Prezzo di stop-out | **3.571,95** (−1,327%) | **3.692,40** (+1,995%) |
| Equity residua allo stop-out | 169,7 (prelevabile) | 156,6 (= credito, persa) |
| P&L del superstite allo stop dell'altro | B: +2.540,1 | A: +2.746,6 |

**Drawdown intermedio.** Se si chiudesse tutto a mercato prima di uno stop-out, il valore prelevabile minimo è **−$573** (−14,3% di K). Si raggiunge a P ≈ 3.657,7, cioè nel punto in cui il balance proprio di B si azzera (2.000/53 = $37,7 sopra P0). Da lì in su le perdite ricadono solo sul credito (vedi `results/payoff_vs_price.png`).

## D. Scenari (K = $4.000)

| Scenario | Valore recuperato A | Valore recuperato B | Profitto netto | ROI |
|---|---|---|---|---|
| Stop-out A (prezzo ↓ 1,33%) | 169,7 | 4.540,1 (credito escluso) | **+709,8** | 17,7% |
| Stop-out B (prezzo ↑ 2,00%) | 4.746,6 | 0 | **+746,6** | 18,7% |
| Valore atteso (moto browniano senza drift, P(A) = 0,601) | | | +724,5 | 18,1% |
| Time stop 24 h (MC, σ 20%) | | | media +215; 5° percentile −699; P(perdita) 35% | |
| Avverso: credito rimosso a equity ≤ credito | | | −575 | −14,4% |
| Avverso: profitti B annullati (scenario A) | | | −1.830 | −45,8% |

## E. Confronto strategie (K = $4.000, spread $0,12/oz, durata a σ = 20%)

| Strategia | Cap. A | Cap. B | Lotti A | Lotti B | Stop A % | Stop B % | Profitto stop A | Profitto stop B | Profitto min | ROI min | Drawdown interm. | E[τ] h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 benchmark | 2.000 | 2.000 | 0,38 | 0,53 | 1,33 | 2,00 | 709,8 | 746,6 | 709,8 | 17,7% | −573 | 38,5 |
| S02 allocazione ottimizzata, lotti fissi | 2.048 | 1.952 | 0,38 | 0,53 | 1,36 | 1,95 | 728,8 | 725,8 | **725,8** | 18,1% | ≈ −570 | 38,5 |
| S03 50/50, lotti ottimizzati (E[τ] ≤ 38,5 h) | 2.000 | 2.000 | 0,42 | 0,59 | 1,19 | 1,79 | 719,4 | 713,6 | 713,6 | 17,8% | — | 30,8 |
| S04 ottimizzazione congiunta (E[τ] ≤ 38,5 h) | 2.048 | 1.952 | 0,38 | 0,53 | 1,36 | 1,95 | 728,8 | 725,8 | **725,8** | 18,1% | — | 38,5 |
| S05 stop equidistanti | 2.420 | 1.580 | 0,41 | 0,54 | 1,50 | 1,53 | 696,4 | 688,9 | 688,9 | 17,2% | — | 33,4 |
| S06 take-profit $400 sul lato ↓ | 2.000 | 2.000 | 0,38 | 0,53 | 0,74* | 2,00 | 389 | 746,6 | 389 | 9,7% | −573 | 21,4 |
| S06 take-profit $600 sul lato ↓ | 2.000 | 2.000 | 0,38 | 0,53 | 1,11* | 2,00 | 589 | 746,6 | 589 | 14,7% | −573 | 32,0 |
| Frontiera, E[τ] ≤ 8 h | 2.044 | 1.956 | 0,78 | 1,08 | 0,60 | 0,92 | 625 | 623 | 622,7 | 15,6% | — | 7,9 |
| Frontiera, E[τ] ≤ 1 h | 2.036 | 1.964 | 1,78 | 2,41 | 0,19 | 0,37 | 378 | 377 | 377,1 | 9,4% | — | 1,0 |

\* distanza della chiusura anticipata, non dello stop-out.

- **S06:** il valore atteso per ora migliora (EV $281 su 10,7 h con target $200), perché si accorcia una barriera. Però riduce il profitto minimo e la probabilità di incassare il bonus. Non è dominante.
- **S07 (time stop):** con chiusura a T ore senza stop-out, il bonus non viene consumato e l'esito è puro P&L direzionale meno costi. A 1/4/8/12/24/48 h la media è −12 / −5 / +14 / +63 / +215 / +399 $, con P(perdita) di 54 / 51 / 50 / 47 / 35 / 23%. **Il time stop introduce perdite reali**: la protezione dipende interamente dal raggiungere uno stop-out.
- **S09 (inversione):** il payoff è simmetrico. Con gli swap dichiarati (unità ipotizzate) costa −$0,8/notte nella configurazione base e −$8,3/notte invertita. La differenza è irrilevante sotto le 24 h; conta solo se gli swap reali dei due broker sono diversi.
- **S10 (multi-strumento):** in forma chiusa il profitto dipende solo da D_A, D_B, credito, r e residui di margine, **non dallo strumento**. Lo strumento incide solo su durata (σ/distanza), costi (spread/σ), gap, swap e orari. Il confronto numerico richiede le specifiche dei due broker per ciascun CFD, che non sono disponibili: **non eseguito**, per non inventare dati.
- **S11 (size dinamiche):** con prezzo martingala, ogni aggiustamento intermedio ha valore atteso nullo prima dei costi. Può solo riallocare il payoff tra gli stati, ma aggiunge spread e rischio di stop-out anticipato. **Nessun vantaggio atteso**: non simulato oltre questa argomentazione.

### CAPITAL: griglia capitali (vincolo E[τ] ≤ 38,5 h, ottimo congiunto, verificato col modello dinamico)

| K | Cap. A | Cap. B | Lotti A | Lotti B | Stop A % | Stop B % | ML0 A | ML0 B | Profitto min | ROI min | Benchmark scalato π_min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | 252,5 | 247,5 | 0,05 | 0,07 | 1,27 | 1,87 | 558% | 1.953% | 90,1 | 18,0% | 89,4 |
| 1.000 | 505 | 495 | 0,10 | 0,14 | 1,27 | 1,87 | 558% | 1.953% | 180,2 | 18,0% | 133,5 (0,10/0,13) |
| 2.000 | 964 | 1.036 | 0,19 | 0,27 | 1,27 | 2,04 | 561% | 2.120% | 361,4 | 18,1% | 346,7 |
| 4.000 | 2.048 | 1.952 | 0,38 | 0,53 | 1,36 | 1,95 | 596% | 2.035% | 725,8 | 18,1% | 709,8 |
| 5.000 | 2.555 | 2.445 | 0,48 | 0,67 | 1,34 | 1,93 | 588% | 2.016% | 905,1 | 18,1% | 910,0 |
| 10.000 | 5.060 | 4.940 | 0,95 | 1,33 | 1,34 | 1,97 | 589% | 2.052% | 1.813,8 | 18,1% | 1.798,4 |
| 15.000 | 7.440 | 7.560 | 1,42 | 2,00 | 1,32 | 2,01 | 579% | 2.088% | 2.721,6 | 18,1% | 2.639,3 |
| 20.000 | 10.120 | 9.880 | 1,90 | 2,66 | 1,34 | 1,97 | 589% | 2.052% | 3.627,6 | 18,1% | 3.548,9 |
| 30.000 | 15.300 | 14.700 | 2,85 | 3,98 | 1,36 | 1,96 | 593% | 2.041% | 5.442,9 | 18,1% | 5.347,3 |
| 50.000 | 25.250 | 24.750 | 4,74 | 6,64 | 1,34 | 1,98 | 589% | 2.059% | 9.072,3 | 18,1% | 8.848,3 |
| 100.000 | 50.200 | 49.800 | 9,47 | 13,29 | 1,34 | 1,99 | 586% | 2.070% | 18.147,3 | 18,1% | 17.744,5 |

- **Scalabilità teorica: lineare.** Il ROI è circa 18,1% a ogni livello, a meno della granularità del lot step: sotto i $1.000 l'arrotondamento a 0,01 lotti pesa, e a K = 1.000 il benchmark scalato perde il 26%.
- **Scalabilità reale: non lineare.** Il limite non è il mercato (13 lotti di oro sono liquidi) ma la controparte del bonus. A $100k il broker B paga in media circa $18k per ciclo (valore atteso negativo per lui). Ci si devono quindi aspettare limiti massimi al bonus, verifiche, revisione dei prelievi e annullamenti. **Non estrapolare.**

## F. Grafici

- `results/payoff_vs_price.png`: profitto prelevabile in funzione del prezzo e punti terminali.
- `results/frontier.png`: frontiera di Pareto profitto minimo / durata attesa.
- `results/heatmap.png`: profitto minimo per allocazione B (%) e lotti A, con L_B = 0,53.

### MONTECARLO: probabilità di stop-out entro h ore

Modello: passi da 2 minuti, innovazioni t(4), volatilità per percorso lognormale, nessun drift, nessun gap, mercato continuo 23 h/giorno.

| Config | σ | 1 h | 4 h | 8 h | 12 h | 24 h | 48 h | 72 h | Mediana |
|---|---|---|---|---|---|---|---|---|---|
| S01 | 15% | 0% | 0,6% | 3,7% | 7,9% | 21% | 43% | 58% | 57 h |
| S01 | 20% | 0,1% | 4,0% | 10,9% | 19,0% | 40% | 64% | 77% | 32 h |
| S01 | 30% | 0,9% | 11,7% | 28,2% | 41,3% | 66% | 86% | 93% | 15 h |
| Frontiera 8 h | 20% | 4,3% | 31% | 53% | 67% | 87% | 97% | 99% | 7,4 h |

- **Incongruenza con la durata dichiarata.** Una durata di 1–24 h per il benchmark richiede σ di almeno ~30% o code molto più spesse. Con σ al 20% il 36% dei cicli dura oltre 48 h e paga swap.
- **Controllo indipendente.** La quota di stop-out su A coincide con la teoria (dB/(dA+dB) = 0,60): 0,616 con σ 30%. Il valore atteso MC della chiusura anticipata coincide con la formula analitica entro l'1–2%.

## STRESS: profitto minimo ($)

| Shock | S01 (0,38/0,53) | S04 | Frontiera 8 h (0,78/1,08) | Frontiera 1 h (1,78/2,41) |
|---|---|---|---|---|
| Base | 709,8 | 725,8 | 622,7 | 377,1 |
| Spread ×2 / ×3 / ×5 | 697 / 684 / 659 | 716 / 703 / 678 | 599 / 573 / 522 | 320 / 263 / 147 |
| Spread $1,20/oz | 595 | 614 | 392 | **−142** |
| Latenza superstite: slippage avverso $1 / $2 / $5 / $10 | 657 / 604 / 445 / 180 | 676 / 623 / 464 / 199 | 517 / 409 / 85 / **−455** | 137 / **−104 / −827 / −2.032** |
| Latenza 5 ms / 100 ms / 1 s / 5 s / 30 s (q95, vol ×3) | 707 / 697 / 668 / 617 / 483 | 724 / 716 / 687 / 636 / 502 | 618 / 599 / 541 / 436 / 163 | 365 / 319 / 190 / **−43 / −654** |
| Divergenza quotazioni B +$2 / +$5 alla chiusura | 604 / 445 | 623 / 464 | 409 / 85 | **−104 / −827** |
| Leva B 1:500 / leva A 1:100 | 635 / 508 | 614 / 527 | 395 / 218 | −140 / non apribile |
| Swap 3 notti | 707 | 723 | 617 | 362 |
| Bonus 50% / 0% | 30 / **−531** | 27 / −518 | −83 / −475 | −348 / −373 |
| Credito rimosso a equity ≤ credito | **−575** | **−562** | −562 | −556 |
| Profitti B annullati | **−1.830** | −1.878 | −1.693 | −1.232 |
| Superstite non chiuso per 1 h: dev. std del P&L | ±504 | ±504 | ±1.027 | ±2.292 |

**Break-even** (profitto minimo = 0), per S01 / S04 / frontiera 8 h / frontiera 1 h:

| Variabile | S01 | S04 | Frontiera 8 h | Frontiera 1 h |
|---|---|---|---|---|
| Spread ($/oz) | 6,8 | 7,0 | 3,0 | 0,9 |
| Slippage della chiusura del superstite (= divergenza di prezzo) ($) | 13,4 | 13,8 | 5,8 | 1,6 |

Uno slippage di gap sullo stop-out è assorbito dall'NBP e **favorisce** il superstite. Questo vale finché il broker non contesta il saldo negativo.

**Lettura.** Accorciare i cicli migliora il valore per ora solo in un mondo senza attriti. La robustezza a costi ed esecuzione crolla con la size, perché il break-even scala con 1/L. **La configurazione più robusta è vicina al benchmark o leggermente più piccola** (E[τ] 24–40 h). Le frontiere sotto le 8 h sono fragili.

### REBALANCE (S12)

- **Dopo lo stop-out di A:** A ha $170, B ha $4.540 di balance più $2.000 di credito.
  - Per riavviare 2.000/2.000 bisogna spostare $1.830 da B ad A.
  - Un prelievo da B di solito cancella il credito (da verificare): si perde l'opzione bonus residua e serve un nuovo deposito con un nuovo bonus.
  - In alternativa si finanzia A con una **riserva esterna di ≈ $1.830**, senza toccare B.
- **Dopo lo stop-out di B:** A ha $4.747 e B è a $0. Si prelevano $2.747 da A e si ridepositano $2.000 su B per un nuovo bonus.
- **Capitale immobilizzato** con una riserva che copre i tempi di prelievo: ≈ $6.000. Il ROI minimo per ciclo scende quindi all'**11,8%**.
- **Ritmo dei cicli.** Il ritmo effettivo è vincolato dai tempi di prelievo e deposito. Con un overhead di 24 h tra cicli, il miglior valore per ora sulla frontiera scende da $18,9/h (benchmark, senza overhead) a circa $11,6/h. Con 72 h scende a circa $6,6/h. L'ottimo si sposta su E[τ] di 8–12 h, cioè proprio dove la robustezza peggiora.
- **Rendimento annuo: non calcolato di proposito.** Dipende dal numero di bonus effettivamente concessi e pagati, che non è modellabile senza i T&C.

## G. Valutazione

| Voce | Esito |
|---|---|
| Migliore sul profitto minimo, a parità di durata del benchmark | **S04: A $2.048 / B $1.952, 0,38 / 0,53.** π_min $725,8 (18,1%). Validità: credito che assorbe perdite, NBP, profitti B pagati, spread ≤ $7/oz, slippage del superstite ≤ $13 |
| Più robusta | S04 o S01 con lotti a −10/20%: break-even di spread e slippage più ampi, a costo di durata maggiore |
| Migliore sul valore per ora, senza attriti | Frontiera 1–2 h: dominata dagli stress, **sconsigliata** |
| Scostamento dal benchmark | +1,4% su π_min. L'ottimo non cambia i lotti, ma il 50/50 non è ottimo (2,3% di miglioramento spostando $48) |
| Parametri che cambiano gli esiti | (1) regola di rimozione o assorbimento del credito; (2) regole di prelievo dei profitti con credito attivo (requisiti di volume, cancellazione); (3) clausole di bonus abuse e di hedging esterno; (4) unità di spread e swap; (5) origine del margin level 980%; (6) tick bid/ask reali dei due broker al momento degli stop-out (latenza e divergenza effettive) |

**Rischi per tipologia**

- **Contrattuale e di controparte (dominante).** Annullamento dei profitti, rimozione del credito, chiusura dei conti, mancato pagamento. Il broker B ha valore atteso −$729 per ciclo verso questa operatività: l'incentivo a contestarla è strutturale.
- **Operativo e tecnologico.** Mancata chiusura del superstite (±$504/h di deviazione standard), disconnessioni, requote sullo stop-out.
- **Mercato.** Limitato finché i due stop-out sono raggiungibili e l'NBP vale; diventa rilevante con time stop o chiusure anticipate.

**Verifica contrattuale: non completata.**

- Non sono riuscito a reperire online i T&C ufficiali di Bridge Markets (entità, regolatore, regole del bonus). Le specifiche XAUUSD di RoboForex non sono state verificate.
- I T&C del 100% bonus di altri broker (es. [IC Markets](https://cdn.icmarkets.com/uploads/clientarea/Deposit_Bonus_T%26C.pdf), [HF Markets](https://static.hotforex.com/assets/common/documents/cysec/100_SuperCharged_Bonus_CY.pdf)) qualificano espressamente come abuso l'hedging interno o esterno e i conti multipli, con rimozione del bonus e dei profitti.
- Diversi programmi di credito prevedono la rimozione del credito quando equity ≤ credito, che è esattamente il regime `remove` che rende negativo π_min ([daytrading.com](https://www.daytrading.com/safety/understanding-bonus-terms)).
- **Finché i T&C scritti di Bridge Markets non autorizzano esplicitamente questa operatività, la strategia è classificata come non eseguibile sul piano contrattuale.** Non vengono proposti accorgimenti per renderla non rilevabile.

**Prossimi passi per l'AUDIT.** Servono gli storici dei due conti in CSV o HTML MT4/MT5, con ticket, apertura e chiusura, prezzi, swap, commissioni, depositi, prelievi e movimenti di credito. Servono anche i T&C del bonus e i tick bid/ask XAUUSD dei due broker (o almeno M1) sul periodo operativo. Con questi dati la pipeline può riconciliare ciclo per ciclo teorico e reale, e ricalibrare σ e la distribuzione delle durate out-of-sample.
