"""Assistente AI personale basato su Claude.

Le risposte seguono le impostazioni in impostazioni.json (modificabili dalla
barra laterale) e ogni conversazione viene salvata in ordine cronologico
nella cartella conversazioni/.

Avvio:  streamlit run app.py
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st

CARTELLA = Path(__file__).parent
FILE_IMPOSTAZIONI = CARTELLA / "impostazioni.json"
CARTELLA_CONVERSAZIONI = CARTELLA / "conversazioni"
CARTELLA_CONVERSAZIONI.mkdir(exist_ok=True)

MODELLI = {
    "claude-opus-5-5": "Claude Opus 5.5 (il più capace)",
    "claude-sonnet-5-5": "Claude Sonnet 5.5 (veloce ed economico)",
    "claude-haiku-5-5": "Claude Haiku 5.5 (rapidissimo, costa pochissimo)",
}
IMPEGNI = {
    "low": "Basso (risposte rapide)",
    "medium": "Medio",
    "high": "Alto (ragiona di più)",
    "xhigh": "Molto alto",
    "max": "Massimo",
}
LUNGHEZZE = ["breve", "media", "dettagliata"]

BETAS = [
    # Se il modello rifiuta una richiesta, l'API la riprova da sola su un altro modello.
    "server-side-fallback-2026-07-01",
    # Controllo sui blocchi di ragionamento quando la cronologia cambia.
    "thinking-binding-controls-2026-08-01",
]


# ---------------------------------------------------------------- impostazioni

def carica_impostazioni() -> dict:
    return json.loads(FILE_IMPOSTAZIONI.read_text(encoding="utf-8"))


def salva_impostazioni(imp: dict) -> None:
    FILE_IMPOSTAZIONI.write_text(
        json.dumps(imp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def istruzioni_da_impostazioni(imp: dict) -> str:
    """Trasforma le impostazioni nelle istruzioni (system prompt) per Claude."""
    righe = [
        f"Sei {imp['nome_assistente']}, l'assistente personale dell'utente.",
        f"Rispondi sempre in {imp['lingua']}, con un tono {imp['tono']}.",
        f"Lunghezza delle risposte: {imp['lunghezza_risposte']}.",
    ]
    if imp.get("chi_sono", "").strip():
        righe.append(f"Informazioni sull'utente: {imp['chi_sono'].strip()}")
    if imp.get("istruzioni", "").strip():
        righe.append(f"Istruzioni dell'utente: {imp['istruzioni'].strip()}")
    regole = [r.strip() for r in imp.get("regole", []) if r.strip()]
    if regole:
        righe.append("Regole da rispettare sempre:")
        righe += [f"- {r}" for r in regole]
    return "\n".join(righe)


# -------------------------------------------------------------- conversazioni

def adesso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def nuova_conversazione(imp: dict) -> dict:
    return {
        "id": datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6],
        "titolo": "Nuova conversazione",
        "creata": adesso(),
        "aggiornata": adesso(),
        # Le istruzioni restano fisse per tutta la conversazione; se le
        # impostazioni cambiano, la modifica viene aggiunta in coda (vedi invia()).
        "istruzioni": istruzioni_da_impostazioni(imp),
        "istruzioni_attuali": istruzioni_da_impostazioni(imp),
        "messaggi": [],
    }


def salva_conversazione(conv: dict) -> None:
    conv["aggiornata"] = adesso()
    percorso = CARTELLA_CONVERSAZIONI / f"{conv['id']}.json"
    percorso.write_text(json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8")


def elenco_conversazioni() -> list[dict]:
    """Tutte le conversazioni, dalla più recente alla più vecchia."""
    conv = []
    for f in CARTELLA_CONVERSAZIONI.glob("*.json"):
        try:
            conv.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(conv, key=lambda c: c["aggiornata"], reverse=True)


def testo_di(msg: dict) -> str:
    """Il testo leggibile di un messaggio salvato."""
    if isinstance(msg["content"], str):
        return msg["content"]
    return "".join(b.get("text", "") for b in msg["content"] if b.get("type") == "text")


# ------------------------------------------------------------------- Claude

def invia(conv: dict, imp: dict, testo: str, area_risposta) -> None:
    conv["messaggi"].append(
        {"role": "user", "content": testo, "ora": adesso(), "modello": imp["modello"]}
    )

    # Impostazioni cambiate a metà conversazione: invece di riscrivere le
    # istruzioni iniziali, si aggiunge un messaggio di sistema dopo la domanda.
    nuove = istruzioni_da_impostazioni(imp)
    if nuove != conv["istruzioni_attuali"]:
        conv["messaggi"].append({
            "role": "system",
            "content": "Da questo punto valgono le nuove impostazioni dell'utente, "
                       "che sostituiscono le precedenti:\n\n" + nuove,
            "ora": adesso(),
        })
        conv["istruzioni_attuali"] = nuove

    # Si inviano i messaggi esattamente come salvati (senza i campi locali).
    messaggi_api = [{"role": m["role"], "content": m["content"]} for m in conv["messaggi"]]

    # La chiave incollata nell'app ha la precedenza; altrimenti si usa ANTHROPIC_API_KEY.
    chiave = st.session_state.get("chiave_api", "").strip()
    client = anthropic.Anthropic(api_key=chiave) if chiave else anthropic.Anthropic()
    testo_parziale = ""
    with client.beta.messages.stream(
        model=imp["modello"],
        max_tokens=64000,
        system=conv["istruzioni"],
        messages=messaggi_api,
        thinking={
            "type": "adaptive",
            "block_binding": {"prefix_mismatch_behavior": "drop_block"},
        },
        output_config={"effort": imp["impegno"]},
        betas=BETAS,
        fallbacks="default",
    ) as stream:
        for pezzo in stream.text_stream:
            testo_parziale += pezzo
            area_risposta.markdown(testo_parziale + "▌")
        risposta = stream.get_final_message()

    if risposta.stop_reason == "refusal":
        area_risposta.warning("Il modello non ha risposto a questa richiesta. Prova a riformularla.")
    else:
        area_risposta.markdown(testo_parziale)

    # La risposta viene salvata per intero (compresi i blocchi di ragionamento),
    # così può essere rimandata identica ai turni successivi.
    conv["messaggi"].append({
        "role": "assistant",
        "content": [b.model_dump(mode="json", exclude_none=True, by_alias=True)
                    for b in risposta.content],
        "ora": adesso(),
        "modello": risposta.model,
    })
    if conv["titolo"] == "Nuova conversazione":
        conv["titolo"] = testo[:60] + ("…" if len(testo) > 60 else "")
    salva_conversazione(conv)


# ------------------------------------------------------------- interfaccia

st.set_page_config(page_title="Assistente AI", page_icon="💬", layout="wide")

if "imp" not in st.session_state:
    st.session_state.imp = carica_impostazioni()
imp = st.session_state.imp

if "conv" not in st.session_state:
    st.session_state.conv = nuova_conversazione(imp)
conv = st.session_state.conv

with st.sidebar:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.text_input(
            "🔑 Chiave API di Anthropic", type="password", key="chiave_api",
            placeholder="sk-ant-...",
            help="Incollala qui. Resta solo in memoria finché l'app è aperta: non viene salvata.",
        )
        if not st.session_state.get("chiave_api"):
            st.info("Incolla la tua chiave API qui sopra per iniziare.")
    if st.button("➕ Nuova conversazione", use_container_width=True):
        st.session_state.conv = nuova_conversazione(imp)
        st.rerun()

    with st.expander("⚙️ Impostazioni", expanded=False):
        with st.form("impostazioni"):
            nome = st.text_input("Nome dell'assistente", imp["nome_assistente"])
            modello = st.selectbox("Modello", list(MODELLI), format_func=MODELLI.get,
                                   index=list(MODELLI).index(imp["modello"]))
            impegno = st.selectbox("Impegno nel ragionamento", list(IMPEGNI),
                                   format_func=IMPEGNI.get,
                                   index=list(IMPEGNI).index(imp["impegno"]))
            lingua = st.text_input("Lingua delle risposte", imp["lingua"])
            tono = st.text_input("Tono", imp["tono"])
            lunghezza = st.selectbox("Lunghezza risposte", LUNGHEZZE,
                                     index=LUNGHEZZE.index(imp["lunghezza_risposte"]))
            chi_sono = st.text_area("Chi sono (cosa deve sapere di te)", imp["chi_sono"])
            istruzioni = st.text_area("Istruzioni", imp["istruzioni"], height=120)
            regole = st.text_area("Regole (una per riga)", "\n".join(imp["regole"]))
            if st.form_submit_button("Salva impostazioni", use_container_width=True):
                imp.update(
                    nome_assistente=nome, modello=modello, impegno=impegno,
                    lingua=lingua, tono=tono, lunghezza_risposte=lunghezza,
                    chi_sono=chi_sono, istruzioni=istruzioni,
                    regole=[r for r in regole.splitlines() if r.strip()],
                )
                salva_impostazioni(imp)
                st.success("Impostazioni salvate: valgono dal prossimo messaggio.")

    st.subheader("🕑 Cronologia")
    for c in elenco_conversazioni():
        data = datetime.fromisoformat(c["aggiornata"]).strftime("%d/%m/%Y %H:%M")
        if st.button(f"{c['titolo']}\n\n{data}", key=c["id"], use_container_width=True):
            st.session_state.conv = c
            st.rerun()

st.title(f"💬 {imp['nome_assistente']}")
st.caption(f"Modello: {MODELLI[imp['modello']]} · Impegno: {IMPEGNI[imp['impegno']]}")

for m in conv["messaggi"]:
    ora = datetime.fromisoformat(m["ora"]).strftime("%d/%m/%Y %H:%M")
    if m["role"] == "system":
        st.caption(f"⚙️ {ora} · impostazioni aggiornate")
        continue
    with st.chat_message(m["role"]):
        st.caption(ora)
        st.markdown(testo_di(m))

if domanda := st.chat_input("Scrivi qui il tuo messaggio…"):
    with st.chat_message("user"):
        st.caption(datetime.now().strftime("%d/%m/%Y %H:%M"))
        st.markdown(domanda)
    with st.chat_message("assistant"):
        area = st.empty()
        # In caso di errore si torna allo stato di prima, senza messaggi a metà.
        n_prima, istr_prima = len(conv["messaggi"]), conv["istruzioni_attuali"]

        def annulla():
            del conv["messaggi"][n_prima:]
            conv["istruzioni_attuali"] = istr_prima

        try:
            invia(conv, imp, domanda, area)
        except anthropic.AuthenticationError:
            area.error("Chiave API mancante o non valida: controlla ANTHROPIC_API_KEY (vedi LEGGIMI.md).")
            annulla()
        except anthropic.RateLimitError:
            area.error("Troppe richieste in poco tempo: aspetta qualche secondo e riprova.")
            annulla()
        except anthropic.APIStatusError as e:
            area.error(f"Errore dal servizio ({e.status_code}): {e.message}")
            annulla()
        except anthropic.APIConnectionError:
            area.error("Connessione non riuscita: controlla la rete e riprova.")
            annulla()
