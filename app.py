import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PyPDF2 import PdfReader

st.set_page_config(layout="wide")

# Mappature colonne
MAPPATURE_COLONNE = {
    "arbitri": {
        1: "Cod.Mecc.",
        2: "Cognome",
        3: "Nome",
        4: "Sezione",
        7: "Età"
    },
    "cra01": {
        1: "NumGara",
        2: "Categoria",
        3: "Girone",
        6: "DataGara",
        16: "Ruolo",
        17: "Cod.Mecc.",
        18: "Cognome"
    },
    "voti": {
        0: "NumGara",
        8: "Voto OA",
        9: "Voto OT"
    },
    "indisponibili": {
        1: "Cod.Mecc.",
        8: "Inizio",
        9: "Fine",
        10: "Motivo"
    }
}

def rinomina_colonne(df, tipo):
    mappatura = MAPPATURE_COLONNE[tipo]
    if len(df.columns) < max(mappatura.keys()) + 1:
        st.error(f"❌ Il file {tipo} ha meno colonne del previsto.")
        st.stop()
    df = df.rename(columns={df.columns[k]: v for k, v in mappatura.items()})
    return df

@st.cache_data
def carica_anagrafica(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "arbitri")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str[-7:]  # Usa solo le ultime 7 cifre
    return df

@st.cache_data
def carica_gare(file):
    df = pd.read_excel(file, header=0)
    df = rinomina_colonne(df, "cra01")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str.strip()
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False)
    df["DataGara"] = pd.to_datetime(df["DataGara"], errors='coerce')
    df = df[~df["DataGara"].isna()]
    return df

@st.cache_data
def carica_voti(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    righe = text.strip().split("\n")
    dati = [riga.split() for riga in righe if len(riga.split()) >= 10]
    df = pd.DataFrame(dati)
    df = rinomina_colonne(df, "voti")
    df["NumGara"] = df["NumGara"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Voto OA"] = pd.to_numeric(df["Voto OA"], errors="coerce")
    df["Voto OT"] = pd.to_numeric(df["Voto OT"], errors="coerce")
    return df

@st.cache_data
def carica_indisponibili(file):
    df = pd.read_excel(file)
    df = rinomina_colonne(df, "indisponibili")
    df["Cod.Mecc."] = df["Cod.Mecc."].astype(str).str[-7:]
    df["Inizio"] = pd.to_datetime(df["Inizio"], errors="coerce")
    df["Fine"] = pd.to_datetime(df["Fine"], errors="coerce")
    return df

# Selezione file
st.title("📊 Visualizzazione Gare Arbitri")
arbitri_file = st.file_uploader("Carica il file Arbitri (.xlsx)", type=["xlsx"])
gare_file = st.file_uploader("Carica il file CRA01 (.xlsx)", type=["xlsx"])
voti_file = st.file_uploader("Carica il file Voti (.pdf)", type=["pdf"])
indisponibili_file = st.file_uploader("Carica il file Indisponibili (.xlsx)", type=["xlsx"])

if arbitri_file:
    df_arbitri = carica_anagrafica(arbitri_file)
    df_gare = carica_gare(gare_file) if gare_file else pd.DataFrame()
    df_voti = carica_voti(voti_file) if voti_file else pd.DataFrame()
    df_indisp = carica_indisponibili(indisponibili_file) if indisponibili_file else pd.DataFrame()

    # Merge voti con gare tramite NumGara
    if not df_voti.empty and not df_gare.empty:
        if "NumGara" not in df_voti.columns or "NumGara" not in df_gare.columns:
            st.error("❌ Colonna 'NumGara' mancante per il merge.")
            st.stop()
        df_merged = pd.merge(df_gare, df_voti, on="NumGara", how="left")
    else:
        df_merged = df_gare.copy()

    # Settimane da 01/05/2025 a 31/05/2025
    start_date = datetime(2025, 5, 1)
    end_date = datetime(2025, 5, 31)
    settimane = []
    while start_date <= end_date:
        week_start = start_date
        week_end = week_start + timedelta(days=6)
        settimane.append((week_start, week_end))
        start_date = week_end + timedelta(days=1)

    for _, arbitro in df_arbitri.iterrows():
        st.markdown(f"### {arbitro['Cognome']} {arbitro['Nome']}")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Sezione:** {arbitro['Sezione']}")
        col2.markdown(f"**Età:** {arbitro['Età']}")
        col3.markdown(f"**Cod.Mecc.:** {arbitro['Cod.Mecc.']}")

        cod_mecc = str(arbitro["Cod.Mecc."]).zfill(7)
        cognome_arbitro = arbitro["Cognome"].strip().upper()

        for week_start, week_end in settimane:
            st.markdown(f"#### Settimana {week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}")
            eventi_settimanali = []

            # Gare assegnate
            gare_sett = df_merged[
                (df_merged["DataGara"] >= week_start) &
                (df_merged["DataGara"] <= week_end) &
                ((df_merged["Cod.Mecc."].astype(str).str[-7:] == cod_mecc) |
                 (df_merged["Cognome"].str.upper() == cognome_arbitro))
            ]
            for _, gara in gare_sett.iterrows():
                descrizione = f"{gara['Categoria']} – {gara['Girone']} – {gara['Ruolo']}"
                if not pd.isna(gara.get("Voto OA")) or not pd.isna(gara.get("Voto OT")):
                    voto_oa = f"OA: {gara['Voto OA']:.2f}" if not pd.isna(gara.get("Voto OA")) else ""
                    voto_ot = f"OT: {gara['Voto OT']:.2f}" if not pd.isna(gara.get("Voto OT")) else ""
                    descrizione += f" – {voto_oa} {voto_ot}".strip()
                eventi_settimanali.append(descrizione)

            # Indisponibilità
            indisp_sett = df_indisp[
                (df_indisp["Cod.Mecc."] == cod_mecc) &
                (df_indisp["Inizio"] <= week_end) &
                (df_indisp["Fine"] >= week_start)
            ]
            for _, ind in indisp_sett.iterrows():
                eventi_settimanali.append(f"🚫 Indisponibile ({ind['Motivo']})")

            if eventi_settimanali:
                for evento in eventi_settimanali:
                    st.markdown(f"- {evento}")
            else:
                st.markdown("—")
